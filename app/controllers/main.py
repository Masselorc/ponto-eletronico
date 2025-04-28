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

# Definição do Blueprint 'main'
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Importações de módulos da aplicação
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
# Importa todos os forms necessários
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app.forms.relatorio import RelatorioCompletoForm # Importa o novo form
from app import db

# --- Funções Auxiliares (mantidas) ---
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    # ... (código da função mantido) ...
    if not entrada or not saida: return None
    try:
        entrada_dt = datetime.combine(data_ref, entrada); saida_dt = datetime.combine(data_ref, saida)
        if saida_dt < entrada_dt: saida_dt += timedelta(days=1)
        diff_total = saida_dt - entrada_dt; horas_trabalhadas = diff_total.total_seconds() / 3600
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco); retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)
            if retorno_almoco_dt < saida_almoco_dt: retorno_almoco_dt += timedelta(days=1)
            diff_almoco = retorno_almoco_dt - saida_almoco_dt; horas_trabalhadas -= diff_almoco.total_seconds() / 3600
        return max(0, horas_trabalhadas)
    except Exception as e: logger.error(f"Erro calc horas {data_ref}: {e}", exc_info=True); return None

def get_usuario_contexto():
    # ... (código da função mantido) ...
    user_id_req = request.args.get('user_id', type=int); usuario_selecionado = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_selecionado = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

# --- Função Auxiliar Refatorada para buscar dados do relatório ---
def _get_relatorio_mensal_data(user_id, mes, ano):
    """Busca e calcula os dados necessários para o relatório mensal."""
    usuario = User.query.get(user_id)
    if not usuario:
        raise ValueError(f"Usuário com ID {user_id} não encontrado.")

    if not (1 <= mes <= 12):
        raise ValueError("Mês inválido.")

    primeiro_dia = date(ano, mes, 1)
    num_dias_mes = calendar.monthrange(ano, mes)[1]
    ultimo_dia = date(ano, mes, num_dias_mes)

    # Busca registros e feriados
    registros = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).order_by(Ponto.data).all()

    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    feriados_dict = {f.data: f.descricao for f in feriados}
    feriados_datas = set(feriados_dict.keys())

    # Busca atividades
    registros_por_data = {r.data: r for r in registros}
    ponto_ids = [r.id for r in registros]
    atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
    atividades_por_ponto = {}
    for atv in atividades:
        if atv.ponto_id not in atividades_por_ponto:
            atividades_por_ponto[atv.ponto_id] = []
        atividades_por_ponto[atv.ponto_id].append(atv.descricao)

    # Calcula estatísticas
    dias_uteis_potenciais = 0
    dias_afastamento = 0
    dias_trabalhados = 0
    horas_trabalhadas = 0.0
    for dia_num in range(1, ultimo_dia.day + 1):
        data_atual = date(ano, mes, dia_num)
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

    # Nomes e navegação de meses
    nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    nome_mes = nomes_meses[mes]
    mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano)
    proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)

    # Retorna um dicionário com todos os dados calculados
    return {
        'usuario': usuario,
        'registros': registros,
        'registros_por_data': registros_por_data,
        'mes_atual': mes, 'ano_atual': ano, 'nome_mes': nome_mes,
        'mes_anterior': mes_anterior, 'ano_anterior': ano_anterior,
        'proximo_mes': proximo_mes, 'proximo_ano': proximo_ano,
        'dias_uteis': dias_uteis_potenciais, # Nome mantido para compatibilidade de template
        'dias_trabalhados': dias_trabalhados,
        'dias_afastamento': dias_afastamento,
        'horas_trabalhadas': horas_trabalhadas,
        'carga_horaria_devida': carga_horaria_devida,
        'saldo_horas': saldo_horas,
        'media_diaria': media_diaria,
        'feriados_dict': feriados_dict, 'feriados_datas': feriados_datas,
        'atividades_por_ponto': atividades_por_ponto,
        'ultimo_dia': ultimo_dia,
        'date_obj': date # Passa o objeto date para uso no template
    }
# --- Fim da Função Auxiliar ---

# Rota principal (mantida)
@main.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

# Rota do Dashboard (mantida)
@main.route('/dashboard')
@login_required
def dashboard():
    # ... (código mantido, usa _get_relatorio_mensal_data internamente se refatorado) ...
    # Ou mantém a lógica original aqui
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano_req, mes_req, 1); num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]; ultimo_dia = date(ano_req, mes_req, num_dias_mes)
        registros = Ponto.query.filter(Ponto.user_id == usuario_ctx.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data.desc()).all()
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all()
        feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        dias_uteis_potenciais = 0; dias_afastamento = 0; dias_trabalhados = 0; horas_trabalhadas = 0.0
        registros_dict = {r.data: r for r in registros}
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro_dia = registros_dict.get(data_atual)
                if registro_dia and registro_dia.afastamento: dias_afastamento += 1
        for r_data, r_obj in registros_dict.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                if r_data.weekday() < 5 and r_data not in feriados_datas: dias_trabalhados += 1; horas_trabalhadas += r_obj.horas_trabalhadas
        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req); proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)
        return render_template('main/dashboard.html', registros=registros, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes, dias_uteis=dias_uteis_potenciais, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, usuario=usuario_ctx, usuarios=usuarios_admin, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano)
    except Exception as e: logger.error(f"Erro dashboard: {e}", exc_info=True); flash('Erro ao carregar dashboard.', 'danger'); return redirect(url_for('main.index')) # Redireciona para index em caso de erro grave

# Rotas de Registro/Edição de Ponto (mantidas)
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    # ... (código mantido) ...
    form = RegistroPontoForm()
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try: form.data.data = date.fromisoformat(data_query)
            except ValueError: flash('Data na URL inválida.', 'warning')
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente: flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger'); return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
            horas_calculadas = calcular_horas(data_selecionada, form.entrada.data, form.saida.data, form.saida_almoco.data, form.retorno_almoco.data)
            novo_registro = Ponto(user_id=current_user.id, data=data_selecionada, entrada=form.entrada.data, saida_almoco=form.saida_almoco.data, retorno_almoco=form.retorno_almoco.data, saida=form.saida.data, horas_trabalhadas=horas_calculadas, observacoes=form.observacoes.data, resultados_produtos=form.resultados_produtos.data, afastamento=False, tipo_afastamento=None)
            db.session.add(novo_registro); db.session.flush()
            if form.atividades.data and form.atividades.data.strip(): db.session.add(Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip()))
            db.session.commit(); flash('Registro de ponto criado com sucesso!', 'success'); return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e: db.session.rollback(); logger.error(f"Erro reg ponto: {e}", exc_info=True); flash('Erro ao registrar.', 'danger')
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    # ... (código mantido) ...
    registro = Ponto.query.get_or_404(ponto_id)
    if registro.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    form = EditarPontoForm(obj=registro); atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if request.method == 'GET':
        if atividade_existente and not form.atividades.data: form.atividades.data = atividade_existente.descricao
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data; is_afastamento = form.afastamento.data; tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None
            registro.data = data_selecionada; registro.afastamento = is_afastamento; registro.tipo_afastamento = tipo_afastamento; registro.observacoes = form.observacoes.data; registro.resultados_produtos = form.resultados_produtos.data
            if is_afastamento: registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else: registro.entrada=form.entrada.data; registro.saida_almoco=form.saida_almoco.data; registro.retorno_almoco=form.retorno_almoco.data; registro.saida=form.saida.data; registro.horas_trabalhadas = calcular_horas(data_selecionada, form.entrada.data, form.saida.data, form.saida_almoco.data, form.retorno_almoco.data)
            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                if atividade_existente: atividade_existente.descricao = descricao_atividade
                else: db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade))
            elif atividade_existente: db.session.delete(atividade_existente)
            db.session.commit(); flash('Registro atualizado!', 'success'); return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))
        except Exception as e: db.session.rollback(); logger.error(f"Erro edit ponto {ponto_id}: {e}", exc_info=True); flash('Erro ao atualizar.', 'danger')
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

# Rota registrar_afastamento (mantida)
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    # ... (código mantido) ...
    form = RegistroAfastamentoForm();
    if request.method == 'GET': data_query = request.args.get('data');
    if data_query: try: form.data.data = date.fromisoformat(data_query); except ValueError: flash('Data URL inválida.', 'warning')
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data; tipo_afastamento = form.tipo_afastamento.data; registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente: flash(f'Registro para {data_selecionada.strftime("%d/%m/%Y")} já existe.', 'danger'); return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
            novo_afastamento = Ponto(user_id=current_user.id, data=data_selecionada, afastamento=True, tipo_afastamento=tipo_afastamento, entrada=None, saida_almoco=None, retorno_almoco=None, saida=None, horas_trabalhadas=None, observacoes=None, resultados_produtos=None)
            db.session.add(novo_afastamento); db.session.commit(); flash('Afastamento registrado!', 'success'); return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e: db.session.rollback(); logger.error(f"Erro reg afastamento: {e}", exc_info=True); flash('Erro ao registrar.', 'danger')
    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")

# Rota registrar_ferias (mantida)
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
     flash('Use "Registrar Afastamento".', 'info'); return redirect(url_for('main.registrar_afastamento', **request.args))

# Rota do Calendário (mantida)
@main.route('/calendario')
@login_required
def calendario():
    # ... (lógica mantida, usa _get_relatorio_mensal_data internamente se refatorado) ...
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today(); mes_req = request.args.get('mes', default=hoje.month, type=int); ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano_req, mes_req, 1); num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]; ultimo_dia = date(ano_req, mes_req, num_dias_mes)
        registros = Ponto.query.filter(Ponto.user_id == usuario_ctx.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).all(); registros_dict = {r.data: r for r in registros}
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all(); feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        dias_uteis_potenciais = 0; dias_afastamento = 0; dias_trabalhados = 0; horas_trabalhadas = 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 dias_uteis_potenciais += 1
                 registro_dia = registros_dict.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
        for r_data, r_obj in registros_dict.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                if r_data.weekday() < 5 and r_data not in feriados_datas: dias_trabalhados += 1; horas_trabalhadas += r_obj.horas_trabalhadas
        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req); proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)
        cal = calendar.Calendar(firstweekday=6); semanas_mes = cal.monthdayscalendar(ano_req, mes_req); calendario_data = []
        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                dia_info = {'dia': dia, 'data': None, 'is_mes_atual': False, 'registro': None, 'feriado': None, 'is_hoje': False, 'is_fim_semana': False}
                if dia != 0: data_atual = date(ano_req, mes_req, dia); dia_info.update({'data': data_atual, 'is_mes_atual': True, 'registro': registros_dict.get(data_atual), 'feriado': feriados_dict.get(data_atual), 'is_hoje': (data_atual == hoje), 'is_fim_semana': (data_atual.weekday() >= 5)})
                semana_data.append(dia_info)
            calendario_data.append(semana_data)
        return render_template('main/calendario.html', calendario_data=calendario_data, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes, dias_uteis=dias_uteis_potenciais, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, usuario=usuario_ctx, usuarios=usuarios_admin, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano)
    except Exception as e: logger.error(f"Erro calendário: {e}", exc_info=True); flash('Erro ao carregar calendário.', 'danger'); return redirect(url_for('main.dashboard'))

# Rota para o Relatório Mensal detalhado (GET)
@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Exibe o relatório mensal detalhado e o formulário de autoavaliação."""
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Busca os dados do relatório usando a função auxiliar
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req)

        # Instancia o formulário para a seção de autoavaliação
        form_completo = RelatorioCompletoForm()

        # Adiciona o form ao contexto e passa todos os dados para o template
        contexto_template = {**dados_relatorio, 'usuarios': usuarios_admin, 'form_completo': form_completo}

        return render_template('main/relatorio_mensal.html', **contexto_template)

    except ValueError as ve:
        flash(str(ve), 'danger') # Mostra erro específico (ex: Mês inválido, Usuário não encontrado)
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True)
        flash('Erro ao gerar o relatório mensal. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para exportar o relatório mensal padrão em PDF (mantida)
@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    """Gera e envia o relatório mensal padrão em formato PDF."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))

    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_pdf
        # Chama generate_pdf sem o contexto completo para gerar o PDF padrão
        pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano)
        if pdf_rel_path:
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else: logger.error(f"Arquivo PDF não encontrado: {pdf_abs_path}"); flash('Erro interno: Arquivo PDF gerado não foi encontrado.', 'danger')
        else: flash('Erro ao gerar o relatório em PDF.', 'danger')
    except Exception as e: logger.error(f"Erro ao gerar/enviar PDF: {e}", exc_info=True); flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para exportar o relatório mensal em Excel (mantida)
@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    # ... (código mantido) ...
    user_id_req = request.args.get('user_id', type=int); usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        from app.utils.export import generate_excel; excel_rel_path = generate_excel(usuario_alvo.id, mes, ano)
        if excel_rel_path: excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path);
        if os.path.exists(excel_abs_path): nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower(); download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"; return send_file(excel_abs_path, as_attachment=True, download_name=download_name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else: logger.error(f"Excel não encontrado: {excel_abs_path}"); flash('Erro: Excel não encontrado.', 'danger')
        else: flash('Erro ao gerar Excel.', 'danger')
    except Exception as e: logger.error(f"Erro gerar/enviar Excel: {e}", exc_info=True); flash('Erro inesperado ao gerar Excel.', 'danger')
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# --- NOVA ROTA para gerar PDF completo com autoavaliação ---
@main.route('/gerar-relatorio-completo/pdf', methods=['POST'])
@login_required
def gerar_relatorio_completo_pdf():
    """Processa o formulário de autoavaliação e gera o PDF completo."""
    form = RelatorioCompletoForm()
    if form.validate_on_submit():
        try:
            # Obtém dados do formulário
            user_id = int(form.user_id.data)
            mes = int(form.mes.data)
            ano = int(form.ano.data)
            autoavaliacao_data = form.autoavaliacao.data
            dificuldades_data = form.dificuldades.data
            sugestoes_data = form.sugestoes.data
            declaracao_marcada = form.declaracao.data # Deve ser True

            # Busca os dados base do relatório
            dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)

            # Monta o contexto completo para o PDF
            contexto_completo = {
                **dados_relatorio_base, # Inclui todos os dados padrão
                'autoavaliacao_data': autoavaliacao_data,
                'dificuldades_data': dificuldades_data,
                'sugestoes_data': sugestoes_data,
                'declaracao_marcada': declaracao_marcada,
                'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'), # Data/Hora da geração
                'titulo': f'Relatório de Ponto e Autoavaliação - {dados_relatorio_base["nome_mes"]}/{ano}' # Título específico
            }

            # Gera o PDF usando a função de exportação, passando o contexto completo
            from app.utils.export import generate_pdf
            pdf_rel_path = generate_pdf(user_id, mes, ano, context_completo=contexto_completo)

            if pdf_rel_path:
                pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
                if os.path.exists(pdf_abs_path):
                    # Define nome do arquivo para download
                    usuario_alvo = dados_relatorio_base['usuario']
                    nome_mes_str = dados_relatorio_base['nome_mes'].lower()
                    download_name = f"relatorio_completo_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                    return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
                else:
                    logger.error(f"Arquivo PDF completo não encontrado: {pdf_abs_path}")
                    flash('Erro interno: Arquivo PDF completo gerado não foi encontrado.', 'danger')
            else:
                flash('Erro ao gerar o relatório completo em PDF.', 'danger')

        except ValueError as ve:
            flash(f"Erro ao buscar dados para o relatório: {ve}", 'danger')
        except Exception as e:
            logger.error(f"Erro ao gerar PDF completo: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao gerar o PDF completo.', 'danger')

    else:
        # Se a validação do formulário falhar (ex: checkbox não marcado)
        # Recarrega a página de relatório mostrando os erros
        # Precisamos dos dados originais para redirecionar corretamente
        user_id = form.user_id.data or current_user.id # Fallback para usuário atual
        mes = form.mes.data or date.today().month
        ano = form.ano.data or date.today().year
        # Adiciona mensagens de erro do formulário ao flash
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')
        return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

    # Redireciona de volta para o relatório em caso de erro na geração/envio do PDF
    user_id_fallback = form.user_id.data or current_user.id
    mes_fallback = form.mes.data or date.today().month
    ano_fallback = form.ano.data or date.today().year
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fallback, mes=mes_fallback, ano=ano_fallback))
# --- Fim da Nova Rota ---

# Rotas visualizar_ponto, excluir_ponto, perfil, registrar_multiplo_ponto, registrar_atividade (mantidas)
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    # ... (código mantido) ...
    registro = Ponto.query.get_or_404(ponto_id);
    if registro.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all(); usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono: flash('Usuário não encontrado.', 'danger'); return redirect(url_for('main.dashboard'))
    return render_template('main/visualizar_ponto.html', registro=registro, atividades=atividades, usuario=usuario_dono, title="Visualizar Registro")

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    # ... (código mantido) ...
    registro = Ponto.query.get_or_404(ponto_id); data_registro = registro.data
    if registro.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    try: db.session.delete(registro); db.session.commit(); flash('Registro excluído!', 'success')
    except Exception as e: db.session.rollback(); logger.error(f"Erro excluir ponto {ponto_id}: {e}", exc_info=True); flash('Erro ao excluir.', 'danger')
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

@main.route('/perfil')
@login_required
def perfil():
    # ... (código mantido) ...
    usuario_atualizado = User.query.get(current_user.id);
    if not usuario_atualizado: flash('Erro ao carregar perfil.', 'danger'); return redirect(url_for('main.dashboard'))
    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    # ... (código mantido com validação de almoço) ...
    form = MultiploPontoForm()
    if form.validate_on_submit():
        try:
            datas_str = request.form.getlist('datas[]'); entradas_str = request.form.getlist('entradas[]'); saidas_almoco_str = request.form.getlist('saidas_almoco[]'); retornos_almoco_str = request.form.getlist('retornos_almoco[]'); saidas_str = request.form.getlist('saidas[]'); atividades_desc = request.form.getlist('atividades[]'); resultados_produtos_desc = request.form.getlist('resultados_produtos[]'); observacoes_desc = request.form.getlist('observacoes[]')
            registros_criados, registros_ignorados, registros_erro_almoco = 0, 0, 0; datas_processadas = set()
            for i in range(len(datas_str)):
                data_str = datas_str[i];
                if not data_str: continue
                try: data = date.fromisoformat(data_str)
                except ValueError: flash(f'Formato de data inválido ignorado: {data_str}', 'warning'); continue
                if data in datas_processadas: continue
                datas_processadas.add(data); registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente: flash(f'Registro para {data.strftime("%d/%m/%Y")} já existe e foi ignorado.', 'info'); registros_ignorados += 1; continue
                entrada_str = entradas_str[i] if i < len(entradas_str) else None; saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None; retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None; saida_str_i = saidas_str[i] if i < len(saidas_str) else None; atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None; resultado_desc_i = resultados_produtos_desc[i].strip() if i < len(resultados_produtos_desc) and resultados_produtos_desc[i] else None; observacao_i = observacoes_desc[i].strip() if i < len(observacoes_desc) and observacoes_desc[i] else None
                try: entrada_t = time.fromisoformat(entrada_str) if entrada_str else None; saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None; retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None; saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError: flash(f'Formato de hora inválido para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning'); registros_erro_almoco += 1; continue
                if entrada_t and saida_t:
                    if not saida_almoco_t or not retorno_almoco_t: flash(f'Erro na data {data.strftime("%d/%m/%Y")}: Horários de almoço obrigatórios para dias trabalhados. Registro ignorado.', 'warning'); registros_erro_almoco += 1; continue
                    try:
                        saida_almoco_dt = datetime.combine(data, saida_almoco_t); retorno_almoco_dt = datetime.combine(data, retorno_almoco_t)
                        if retorno_almoco_dt <= saida_almoco_dt: retorno_almoco_dt += timedelta(days=1)
                        duracao_almoco = retorno_almoco_dt - saida_almoco_dt
                        if duracao_almoco.total_seconds() < 3600: flash(f'Erro na data {data.strftime("%d/%m/%Y")}: Intervalo de almoço deve ser de no mínimo 1 hora. Registro ignorado.', 'warning'); registros_erro_almoco += 1; continue
                    except (TypeError, ValueError): flash(f'Erro ao calcular duração do almoço para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning'); registros_erro_almoco += 1; continue
                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)
                novo_registro = Ponto(user_id=current_user.id, data=data, entrada=entrada_t, saida_almoco=saida_almoco_t, retorno_almoco=retorno_almoco_t, saida=saida_t, horas_trabalhadas=horas_calculadas, afastamento=False, tipo_afastamento=None, resultados_produtos=resultado_desc_i, observacoes=observacao_i)
                db.session.add(novo_registro)
                try: db.session.flush();
                    if atividade_desc_i: db.session.add(Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i))
                    db.session.commit(); registros_criados += 1
                except Exception as commit_err: db.session.rollback(); logger.error(f"Erro ao salvar registro/atividade para {data}: {commit_err}", exc_info=True); flash(f'Erro ao salvar registro para {data.strftime("%d/%m/%Y")}.', 'danger')
            msg_parts = [];
            if registros_criados > 0: msg_parts.append(f'{registros_criados} registro(s) criado(s)')
            if registros_ignorados > 0: msg_parts.append(f'{registros_ignorados} data(s) ignorada(s) por já existir registro')
            if registros_erro_almoco > 0: msg_parts.append(f'{registros_erro_almoco} registro(s) ignorado(s) por erro nos dados de almoço')
            if not msg_parts:
                 if len(datas_processadas) == 0: flash('Nenhuma data válida foi informada para registro.', 'warning')
                 else: flash('Nenhum novo registro criado (datas já possuíam registro ou tiveram erro).', 'info')
            else: final_msg = ". ".join(msg_parts) + "."; category = 'success' if registros_criados > 0 and registros_erro_almoco == 0 else 'warning'; flash(final_msg, category)
            return redirect(url_for('main.dashboard'))
        except Exception as e: db.session.rollback(); logger.error(f"Erro inesperado ao processar múltiplos pontos: {e}", exc_info=True); flash('Ocorreu um erro inesperado ao processar os registros. Tente novamente.', 'danger'); return redirect(url_for('main.registrar_multiplo_ponto'))
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos")

@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    # ... (código mantido) ...
    ponto = Ponto.query.get_or_404(ponto_id)
    if ponto.user_id != current_user.id and not current_user.is_admin: flash('Permissão negada.', 'danger'); return redirect(url_for('main.dashboard'))
    form = AtividadeForm(); atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if form.validate_on_submit():
        try:
            descricao = form.descricao.data.strip()
            if atividade_existente: atividade_existente.descricao = descricao
            else: nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao); db.session.add(nova_atividade)
            db.session.commit(); flash('Atividade salva!', 'success'); return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e: db.session.rollback(); logger.error(f"Erro salvar atividade {ponto_id}: {e}", exc_info=True); flash('Erro ao salvar atividade.', 'danger')
    elif request.method == 'GET':
        if atividade_existente: form.descricao.data = atividade_existente.descricao
    return render_template('main/registrar_atividade.html', ponto=ponto, form=form, title="Registrar/Editar Atividade")

