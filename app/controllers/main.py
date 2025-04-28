# -*- coding: utf-8 -*-
# Importações básicas e de bibliotecas padrão
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import calendar
import logging
import os
import tempfile
import pandas as pd
from datetime import datetime, date, timedelta, time

# --- CORREÇÃO: Definir o Blueprint 'main' PRIMEIRO ---
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# --- FIM DA CORREÇÃO ---

# Importações de módulos da aplicação (Modelos, Formulários, db)
# Estas importações ocorrem DEPOIS que 'main' já foi definido.
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app import db # Importa db do pacote app (__init__.py)

# Função auxiliar para calcular horas trabalhadas (sem alterações)
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    """Calcula as horas trabalhadas em um dia, considerando o almoço."""
    if not entrada or not saida:
        return None
    try:
        entrada_dt = datetime.combine(data_ref, entrada)
        saida_dt = datetime.combine(data_ref, saida)
        if saida_dt < entrada_dt:
            saida_dt += timedelta(days=1)
        diff_total = saida_dt - entrada_dt
        horas_trabalhadas = diff_total.total_seconds() / 3600
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco)
            retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)
            if retorno_almoco_dt < saida_almoco_dt:
                retorno_almoco_dt += timedelta(days=1)
            diff_almoco = retorno_almoco_dt - saida_almoco_dt
            horas_trabalhadas -= diff_almoco.total_seconds() / 3600
        return max(0, horas_trabalhadas)
    except Exception as e:
        logger.error(f"Erro ao calcular horas para {data_ref}: {e}", exc_info=True)
        return None

# Função auxiliar para obter o contexto do usuário (sem alterações)
def get_usuario_contexto():
    """Obtém o usuário cujo contexto (dashboard, calendário, etc.) está sendo visualizado."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_selecionado = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_selecionado = usuario_req
        else:
            flash(f"Usuário com ID {user_id_req} não encontrado.", "warning")
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

# Rota principal (sem alterações)
@main.route('/')
@login_required
def index():
    """Redireciona para o dashboard."""
    return redirect(url_for('main.dashboard'))

# Rota do Dashboard (lógica de cálculo de dias úteis já atualizada)
@main.route('/dashboard')
@login_required
def dashboard():
    """Exibe o dashboard com o resumo mensal e registros recentes."""
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data.desc()).all()

        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # --- Bloco de Cálculo Revisado ---
        dias_uteis_potenciais = 0
        dias_afastamento = 0
        dias_trabalhados = 0 # Dias com registro de trabalho (não afastamento)
        horas_trabalhadas = 0.0
        registros_dict = {r.data: r for r in registros} # Mapeia data para registro

        # 1. Calcular dias úteis potenciais e dias de afastamento
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro_dia = registros_dict.get(data_atual)
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1

        # 2. Calcular dias trabalhados e horas trabalhadas (apenas em dias não afastados)
        for r_data, r_obj in registros_dict.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                if r_data.weekday() < 5 and r_data not in feriados_datas:
                    dias_trabalhados += 1
                    horas_trabalhadas += r_obj.horas_trabalhadas

        # 3. Calcular carga horária devida e saldo
        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # --- Fim do Bloco Revisado ---

        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        return render_template(
            'main/dashboard.html',
            registros=registros,
            mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            dias_uteis=dias_uteis_potenciais,
            dias_trabalhados=dias_trabalhados,
            dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas,
            carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas,
            media_diaria=media_diaria,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano
        )
    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
        flash('Erro ao carregar o dashboard. Tente novamente.', 'danger')
        hoje = date.today()
        return render_template(
            'main/dashboard.html',
            registros=[], mes_atual=hoje.month, ano_atual=hoje.year, nome_mes="Mês Atual",
            dias_uteis=0, dias_trabalhados=0, dias_afastamento=0, horas_trabalhadas=0,
            carga_horaria_devida=0, saldo_horas=0, media_diaria=0,
            usuario=current_user, usuarios=None
        )

# Rota para registrar um novo ponto (validação de almoço no form)
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Registra um novo ponto para um dia específico."""
    form = RegistroPontoForm()
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash('Data na URL inválida.', 'warning')

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            horas_calculadas = calcular_horas(
                data_selecionada, form.entrada.data, form.saida.data,
                form.saida_almoco.data, form.retorno_almoco.data
            )
            novo_registro = Ponto(
                user_id=current_user.id, data=data_selecionada, entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data, retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data, horas_trabalhadas=horas_calculadas,
                observacoes=form.observacoes.data,
                resultados_produtos=form.resultados_produtos.data,
                afastamento=False, tipo_afastamento=None
            )
            db.session.add(novo_registro)
            db.session.flush()
            if form.atividades.data and form.atividades.data.strip():
                atividade = Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip())
                db.session.add(atividade)
            db.session.commit()
            flash('Registro de ponto criado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar ponto: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o ponto. Tente novamente.', 'danger')
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")

# Rota para editar um ponto existente (validação de almoço no form)
@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Edita um registro de ponto existente."""
    registro = Ponto.query.get_or_404(ponto_id)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = EditarPontoForm(obj=registro)
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if request.method == 'GET':
        if atividade_existente and not form.atividades.data:
            form.atividades.data = atividade_existente.descricao

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            registro.resultados_produtos = form.resultados_produtos.data

            if is_afastamento:
                registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else:
                registro.entrada=form.entrada.data
                registro.saida_almoco=form.saida_almoco.data
                registro.retorno_almoco=form.retorno_almoco.data
                registro.saida=form.saida.data
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada, form.entrada.data, form.saida.data,
                    form.saida_almoco.data, form.retorno_almoco.data
                )

            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                if atividade_existente: atividade_existente.descricao = descricao_atividade
                else: db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade))
            elif atividade_existente:
                 db.session.delete(atividade_existente)

            db.session.commit()
            flash('Registro atualizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao atualizar o registro. Tente novamente.', 'danger')
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

# Rota para registrar um afastamento (sem alterações)
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    """Registra um afastamento (férias, licença, etc.) para um dia."""
    form = RegistroAfastamentoForm()
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try: form.data.data = date.fromisoformat(data_query)
            except ValueError: flash('Data na URL inválida.', 'warning')
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            tipo_afastamento = form.tipo_afastamento.data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
            novo_afastamento = Ponto(
                user_id=current_user.id, data=data_selecionada, afastamento=True, tipo_afastamento=tipo_afastamento,
                entrada=None, saida_almoco=None, retorno_almoco=None, saida=None, horas_trabalhadas=None,
                observacoes=None, resultados_produtos=None
            )
            db.session.add(novo_afastamento)
            db.session.commit()
            flash('Afastamento registrado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar afastamento: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o afastamento. Tente novamente.', 'danger')
    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")

# Rota para registrar férias (sem alterações)
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
    """Redireciona para a rota de registrar afastamento."""
    flash('Use a opção "Registrar Afastamento" para registrar férias.', 'info')
    return redirect(url_for('main.registrar_afastamento', **request.args))

# Rota do Calendário (lógica de cálculo de dias úteis já atualizada)
@main.route('/calendario')
@login_required
def calendario():
    """Exibe o calendário mensal com os registros de ponto."""
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).all()
        registros_dict = {r.data: r for r in registros}

        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # --- Bloco de Cálculo Revisado ---
        dias_uteis_potenciais = 0
        dias_afastamento = 0
        dias_trabalhados = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro_dia = registros_dict.get(data_atual)
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1

        for r_data, r_obj in registros_dict.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                if r_data.weekday() < 5 and r_data not in feriados_datas:
                     dias_trabalhados += 1
                     horas_trabalhadas += r_obj.horas_trabalhadas

        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # --- Fim do Bloco Revisado ---

        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        cal = calendar.Calendar(firstweekday=6)
        semanas_mes = cal.monthdayscalendar(ano_req, mes_req)
        calendario_data = []
        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                dia_info = {'dia': dia, 'data': None, 'is_mes_atual': False, 'registro': None, 'feriado': None, 'is_hoje': False, 'is_fim_semana': False}
                if dia != 0:
                    data_atual = date(ano_req, mes_req, dia)
                    dia_info.update({
                        'data': data_atual, 'is_mes_atual': True,
                        'registro': registros_dict.get(data_atual),
                        'feriado': feriados_dict.get(data_atual),
                        'is_hoje': (data_atual == hoje),
                        'is_fim_semana': (data_atual.weekday() >= 5)
                    })
                semana_data.append(dia_info)
            calendario_data.append(semana_data)

        return render_template(
            'main/calendario.html',
            calendario_data=calendario_data,
            mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            dias_uteis=dias_uteis_potenciais,
            dias_trabalhados=dias_trabalhados,
            dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas,
            carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas,
            media_diaria=media_diaria,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano
        )
    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao carregar calendário: {e}", exc_info=True)
        flash('Erro ao carregar o calendário. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para o Relatório Mensal detalhado (lógica de cálculo de dias úteis já atualizada)
@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Exibe o relatório mensal detalhado com todos os registros."""
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all()

        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        registros_por_data = {registro.data: registro for registro in registros}
        ponto_ids = [r.id for r in registros]
        atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
        atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto:
                atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)

        # --- Bloco de Cálculo Revisado ---
        dias_uteis_potenciais = 0
        dias_afastamento = 0
        dias_trabalhados = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro_dia = registros_por_data.get(data_atual)
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1

        for r_data, r_obj in registros_por_data.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                 if r_data.weekday() < 5 and r_data not in feriados_datas:
                    dias_trabalhados += 1
                    horas_trabalhadas += r_obj.horas_trabalhadas

        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # --- Fim do Bloco Revisado ---

        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        return render_template(
            'main/relatorio_mensal.html',
            registros=registros,
            mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano,
            dias_uteis=dias_uteis_potenciais,
            dias_trabalhados=dias_trabalhados,
            dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas,
            carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas,
            media_diaria=media_diaria,
            feriados_dict=feriados_dict, feriados_datas=feriados_datas,
            registros_por_data=registros_por_data,
            atividades_por_ponto=atividades_por_ponto,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            date=date, ultimo_dia=ultimo_dia, ano=ano_req, mes=mes_req
        )
    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True)
        flash('Erro ao gerar o relatório mensal. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para exportar o relatório mensal em PDF (sem alterações)
@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    """Gera e envia o relatório mensal em formato PDF."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_pdf
        pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano)
        if pdf_rel_path:
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else:
                logger.error(f"Arquivo PDF não encontrado: {pdf_abs_path}")
                flash('Erro interno: Arquivo PDF gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em PDF.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao gerar/enviar PDF: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para exportar o relatório mensal em Excel (sem alterações)
@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    """Gera e envia o relatório mensal em formato Excel."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_excel
        excel_rel_path = generate_excel(usuario_alvo.id, mes, ano)
        if excel_rel_path:
            excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path)
            if os.path.exists(excel_abs_path):
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"
                return send_file(excel_abs_path, as_attachment=True, download_name=download_name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                logger.error(f"Arquivo Excel não encontrado: {excel_abs_path}")
                flash('Erro interno: Arquivo Excel gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em Excel.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao gerar/enviar Excel: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o Excel.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para visualizar detalhes de um ponto específico (sem alterações)
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    """Exibe os detalhes de um registro de ponto específico."""
    registro = Ponto.query.get_or_404(ponto_id)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono:
        flash('Usuário associado a este registro não encontrado.', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('main/visualizar_ponto.html', registro=registro, atividades=atividades, usuario=usuario_dono, title="Visualizar Registro")

# Rota para excluir um ponto (via POST) (sem alterações)
@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """Exclui um registro de ponto."""
    registro = Ponto.query.get_or_404(ponto_id)
    data_registro = registro.data
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    try:
        db.session.delete(registro)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
        flash('Ocorreu um erro ao excluir o registro.', 'danger')
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

# Rota para visualizar o perfil do usuário logado (sem alterações)
@main.route('/perfil')
@login_required
def perfil():
    """Exibe a página de perfil do usuário logado."""
    usuario_atualizado = User.query.get(current_user.id)
    if not usuario_atualizado:
        flash('Erro ao carregar informações do perfil.', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")

# Rota para registrar múltiplos pontos de uma vez (com validação de almoço)
@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Permite registrar múltiplos pontos de uma vez."""
    form = MultiploPontoForm()
    if form.validate_on_submit():
        try:
            datas_str = request.form.getlist('datas[]')
            entradas_str = request.form.getlist('entradas[]')
            saidas_almoco_str = request.form.getlist('saidas_almoco[]')
            retornos_almoco_str = request.form.getlist('retornos_almoco[]')
            saidas_str = request.form.getlist('saidas[]')
            atividades_desc = request.form.getlist('atividades[]')
            resultados_produtos_desc = request.form.getlist('resultados_produtos[]')
            observacoes_desc = request.form.getlist('observacoes[]')

            registros_criados, registros_ignorados, registros_erro_almoco = 0, 0, 0
            datas_processadas = set()

            for i in range(len(datas_str)):
                data_str = datas_str[i]
                if not data_str: continue
                try: data = date.fromisoformat(data_str)
                except ValueError: flash(f'Formato de data inválido ignorado: {data_str}', 'warning'); continue
                if data in datas_processadas: continue
                datas_processadas.add(data)
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente:
                    flash(f'Registro para {data.strftime("%d/%m/%Y")} já existe e foi ignorado.', 'info')
                    registros_ignorados += 1; continue

                entrada_str = entradas_str[i] if i < len(entradas_str) else None
                saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None
                retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None
                saida_str_i = saidas_str[i] if i < len(saidas_str) else None
                atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None
                resultado_desc_i = resultados_produtos_desc[i].strip() if i < len(resultados_produtos_desc) and resultados_produtos_desc[i] else None
                observacao_i = observacoes_desc[i].strip() if i < len(observacoes_desc) and observacoes_desc[i] else None

                try:
                    entrada_t = time.fromisoformat(entrada_str) if entrada_str else None
                    saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None
                    retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None
                    saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError:
                    flash(f'Formato de hora inválido para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning')
                    registros_erro_almoco += 1
                    continue

                # --- Validação do Almoço Obrigatório ---
                if entrada_t and saida_t:
                    if not saida_almoco_t or not retorno_almoco_t:
                        flash(f'Erro na data {data.strftime("%d/%m/%Y")}: Horários de almoço obrigatórios para dias trabalhados. Registro ignorado.', 'warning')
                        registros_erro_almoco += 1
                        continue
                    try:
                        saida_almoco_dt = datetime.combine(data, saida_almoco_t)
                        retorno_almoco_dt = datetime.combine(data, retorno_almoco_t)
                        if retorno_almoco_dt <= saida_almoco_dt:
                            retorno_almoco_dt += timedelta(days=1)
                        duracao_almoco = retorno_almoco_dt - saida_almoco_dt
                        if duracao_almoco.total_seconds() < 3600:
                            flash(f'Erro na data {data.strftime("%d/%m/%Y")}: Intervalo de almoço deve ser de no mínimo 1 hora. Registro ignorado.', 'warning')
                            registros_erro_almoco += 1
                            continue
                    except (TypeError, ValueError):
                         flash(f'Erro ao calcular duração do almoço para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning')
                         registros_erro_almoco += 1
                         continue
                # --- Fim da Validação do Almoço ---

                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)
                novo_registro = Ponto(
                    user_id=current_user.id, data=data, entrada=entrada_t,
                    saida_almoco=saida_almoco_t, retorno_almoco=retorno_almoco_t,
                    saida=saida_t, horas_trabalhadas=horas_calculadas,
                    afastamento=False, tipo_afastamento=None,
                    resultados_produtos=resultado_desc_i,
                    observacoes=observacao_i
                )
                db.session.add(novo_registro)
                try:
                    db.session.flush()
                    if atividade_desc_i: db.session.add(Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i))
                    db.session.commit(); registros_criados += 1
                except Exception as commit_err:
                    db.session.rollback()
                    logger.error(f"Erro ao salvar registro/atividade para {data}: {commit_err}", exc_info=True)
                    flash(f'Erro ao salvar registro para {data.strftime("%d/%m/%Y")}.', 'danger')

            msg_parts = []
            if registros_criados > 0: msg_parts.append(f'{registros_criados} registro(s) criado(s)')
            if registros_ignorados > 0: msg_parts.append(f'{registros_ignorados} data(s) ignorada(s) por já existir registro')
            if registros_erro_almoco > 0: msg_parts.append(f'{registros_erro_almoco} registro(s) ignorado(s) por erro nos dados de almoço')

            if not msg_parts:
                 if len(datas_processadas) == 0:
                     flash('Nenhuma data válida foi informada para registro.', 'warning')
                 else:
                     flash('Nenhum novo registro criado (datas já possuíam registro ou tiveram erro).', 'info')
            else:
                final_msg = ". ".join(msg_parts) + "."
                category = 'success' if registros_criados > 0 and registros_erro_almoco == 0 else 'warning'
                flash(final_msg, category)

            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro inesperado ao processar múltiplos pontos: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao processar os registros. Tente novamente.', 'danger')
            return redirect(url_for('main.registrar_multiplo_ponto'))
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos")

# Rota para registrar/editar atividade de um ponto existente (sem alterações)
@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    """Registra ou edita a atividade de um ponto específico."""
    ponto = Ponto.query.get_or_404(ponto_id)
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar atividades deste registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = AtividadeForm()
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if form.validate_on_submit():
        try:
            descricao = form.descricao.data.strip()
            if atividade_existente:
                atividade_existente.descricao = descricao
            else:
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao)
                db.session.add(nova_atividade)
            db.session.commit()
            flash('Atividade salva com sucesso!', 'success')
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar atividade para ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao salvar a atividade.', 'danger')
    elif request.method == 'GET':
        if atividade_existente:
            form.descricao.data = atividade_existente.descricao
    return render_template(
        'main/registrar_atividade.html',
        ponto=ponto,
        form=form,
        title="Registrar/Editar Atividade"
    )

