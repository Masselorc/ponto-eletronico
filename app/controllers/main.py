from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
# --- CORREÇÃO CALENDÁRIO: Importar calendar ---
import calendar
# -------------------------------------------
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm
from app import db
from datetime import datetime, date, timedelta, time
# Removido monthrange pois calendar.monthcalendar substitui sua necessidade aqui
import logging
import os
import tempfile
import pandas as pd
# Importar funções de exportação se forem usadas aqui
# from app.utils.export import generate_pdf, generate_excel

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

# --- Funções Auxiliares --- (Mantidas)
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    # ... (código mantido) ...
    if not entrada or not saida:
        return None # Não pode calcular sem entrada e saída

    try:
        entrada_dt = datetime.combine(data_ref, entrada)
        saida_dt = datetime.combine(data_ref, saida)

        # Ajusta se a saída for no dia seguinte
        if saida_dt < entrada_dt:
            saida_dt += timedelta(days=1)

        # Calcula diferença total
        diff_total = saida_dt - entrada_dt
        horas_trabalhadas = diff_total.total_seconds() / 3600

        # Subtrai almoço se ambos os horários forem fornecidos
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco)
            retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)

            # Ajusta se o retorno do almoço for no dia seguinte (menos comum)
            if retorno_almoco_dt < saida_almoco_dt:
                retorno_almoco_dt += timedelta(days=1)

            diff_almoco = retorno_almoco_dt - saida_almoco_dt
            horas_trabalhadas -= diff_almoco.total_seconds() / 3600

        return max(0, horas_trabalhadas) # Evita horas negativas
    except Exception as e:
        logger.error(f"Erro ao calcular horas para data {data_ref}: {e}", exc_info=True)
        return None

def get_usuario_contexto():
    # ... (código mantido) ...
    user_id_req = request.args.get('user_id', type=int)
    usuario_selecionado = current_user # Default para o usuário logado

    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_selecionado = usuario_req
        else:
            flash(f"Usuário com ID {user_id_req} não encontrado.", "warning")
            # Mantém o usuário atual como contexto

    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None

    return usuario_selecionado, usuarios_para_admin

# --- Rotas Principais ---

@main.route('/')
@login_required
def index():
    # ... (código mantido) ...
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    # ... (código mantido como na versão anterior) ...
    usuario_ctx, usuarios_admin = get_usuario_contexto()

    hoje = date.today()
    mes_req = request.args.get('mes', default=hoje.month, type=int)
    ano_req = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Valida mês e ano
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido. Exibindo mês atual.', 'warning')
        # Adicionar validação de ano se necessário

        primeiro_dia = date(ano_req, mes_req, 1)
        # CORREÇÃO: Usar calendar.monthrange para obter o último dia
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)


        # Obtém os registros de ponto do mês para o usuário do contexto
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data.desc()).all() # Ordenar por data descendente para mostrar mais recentes primeiro

        # Obtém os feriados do mês
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # Calcula estatísticas
        dias_uteis = 0
        dias_trabalhados = 0
        dias_afastamento = 0
        horas_trabalhadas = 0.0

        # Itera pelos dias do mês para calcular dias úteis e afastamentos
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            # Verifica se é dia útil (segunda a sexta e não é feriado)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 # Verifica se houve afastamento neste dia útil
                 # Otimização: Buscar no dicionário se já tivermos os registros
                 registro_dia = next((r for r in registros if r.data == data_atual), None)
                 if registro_dia and registro_dia.afastamento:
                     dias_afastamento += 1
                 else:
                     # Só conta como dia útil se não for afastamento
                     dias_uteis += 1

        # Calcula dias trabalhados e horas trabalhadas a partir dos registros existentes
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None:
                dias_trabalhados += 1
                horas_trabalhadas += r.horas_trabalhadas

        carga_horaria_devida = dias_uteis * 8.0 # 8 horas por dia útil não afastado
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

        # Nomes dos meses
        nomes_meses = [
            '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        nome_mes = nomes_meses[mes_req]

        # Mês/Ano anterior e próximo para navegação
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)


        return render_template('main/dashboard.html',
                              registros=registros, # Registros do mês ordenados desc
                              mes_atual=mes_req,
                              ano_atual=ano_req,
                              nome_mes=nome_mes,
                              dias_uteis=dias_uteis,
                              dias_trabalhados=dias_trabalhados,
                              dias_afastamento=dias_afastamento,
                              horas_trabalhadas=horas_trabalhadas,
                              carga_horaria_devida=carga_horaria_devida,
                              saldo_horas=saldo_horas,
                              media_diaria=media_diaria,
                              usuario=usuario_ctx, # Usuário sendo visualizado
                              usuarios=usuarios_admin, # Lista de usuários para admin
                              mes_anterior=mes_anterior,
                              ano_anterior=ano_anterior,
                              proximo_mes=proximo_mes,
                              proximo_ano=proximo_ano)

    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
        flash('Erro ao carregar o dashboard. Tente novamente.', 'danger')
        # Renderiza com valores padrão ou redireciona
        return render_template('main/dashboard.html', registros=[], mes_atual=hoje.month, ano_atual=hoje.year, nome_mes="Mês Atual", dias_uteis=0, dias_trabalhados=0, dias_afastamento=0, horas_trabalhadas=0, carga_horaria_devida=0, saldo_horas=0, media_diaria=0, usuario=current_user, usuarios=None)


@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    # ... (código mantido como na versão anterior) ...
    form = RegistroPontoForm()

    # Pré-popula a data se vier da query string (ex: link do calendário)
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash('Data inválida na URL.', 'warning')

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            logger.info(f"Tentando registrar ponto para {current_user.email} na data {data_selecionada}")

            # Verifica se já existe um registro para esta data e usuário
            registro_existente = Ponto.query.filter_by(
                user_id=current_user.id,
                data=data_selecionada
            ).first()

            if registro_existente:
                flash(f'Já existe um registro para a data {data_selecionada.strftime("%d/%m/%Y")}. Use a opção de editar.', 'danger')
                # Redireciona para edição ou dashboard
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Calcula horas trabalhadas
            horas_calculadas = calcular_horas(
                data_selecionada,
                form.entrada.data,
                form.saida.data,
                form.saida_almoco.data,
                form.retorno_almoco.data
            )

            # Cria o novo registro
            novo_registro = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data,
                retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data,
                horas_trabalhadas=horas_calculadas,
                observacoes=form.observacoes.data, # Campo adicionado ao form
                afastamento=False, # Registro normal não é afastamento
                tipo_afastamento=None
            )

            db.session.add(novo_registro)
            db.session.commit() # Commit para obter o ID do novo_registro

            # Adiciona a atividade se houver
            if form.atividades.data:
                 # Verifica se o campo atividades existe e tem dados
                 # Remove espaços em branco extras e verifica se não está vazio
                descricao_atividade = form.atividades.data.strip()
                if descricao_atividade:
                    atividade = Atividade(
                        ponto_id=novo_registro.id, # Usa o ID do registro recém-criado
                        descricao=descricao_atividade
                    )
                    db.session.add(atividade)
                    db.session.commit() # Commit da atividade

            flash('Registro de ponto criado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar ponto para {current_user.email}: {e}", exc_info=True)
            flash('Erro ao registrar ponto. Tente novamente.', 'danger')

    # Se GET ou se a validação falhar
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")


@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto():
    # ... (código mantido como na versão anterior) ...
    registro = Ponto.query.get_or_404(ponto_id)

    # Verifica permissão: usuário só pode editar seus próprios pontos (ou admin)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Cria o formulário. No GET, preenche com dados do objeto 'registro'.
    form = EditarPontoForm(obj=registro)

    # Carrega atividades existentes para exibição no formulário (se houver)
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if request.method == 'GET' and atividade_existente:
         if not form.atividades.data:
              form.atividades.data = atividade_existente.descricao

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            # Validação extra: tipo_afastamento é obrigatório se is_afastamento for True
            if is_afastamento and not tipo_afastamento:
                 flash('Selecione o Tipo de Afastamento quando marcar como afastamento.', 'danger')
                 return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")


            # Atualiza os dados do registro
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento

            if is_afastamento:
                # Limpa campos de horário e horas se for afastamento
                registro.entrada = None
                registro.saida_almoco = None
                registro.retorno_almoco = None
                registro.saida = None
                registro.horas_trabalhadas = None # Ou 0, dependendo da regra
            else:
                # Atualiza horários e recalcula horas se não for afastamento
                registro.entrada = form.entrada.data
                registro.saida_almoco = form.saida_almoco.data
                registro.retorno_almoco = form.retorno_almoco.data
                registro.saida = form.saida.data
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada,
                    form.entrada.data,
                    form.saida.data,
                    form.saida_almoco.data,
                    form.retorno_almoco.data
                )

            # Atualiza observações
            registro.observacoes = form.observacoes.data

            # Atualiza ou cria atividade
            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first() # Busca novamente

            if descricao_atividade:
                if atividade_existente:
                    atividade_existente.descricao = descricao_atividade
                else:
                    nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao_atividade)
                    db.session.add(nova_atividade)
            elif atividade_existente:
                 db.session.delete(atividade_existente)


            db.session.commit() # Salva registro e atividade (se houver)

            flash('Registro de ponto atualizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Erro ao atualizar registro. Tente novamente.', 'danger')

    # Se GET ou validação falhar, renderiza o template
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")


@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    # ... (código mantido como na versão anterior) ...
    form = RegistroAfastamentoForm()

    # Pré-popula a data se vier da query string
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash('Data inválida na URL.', 'warning')

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            tipo_afastamento = form.tipo_afastamento.data

            # Verifica se já existe um registro para esta data
            registro_existente = Ponto.query.filter_by(
                user_id=current_user.id,
                data=data_selecionada
            ).first()

            if registro_existente:
                flash(f'Já existe um registro para a data {data_selecionada.strftime("%d/%m/%Y")}. Use a opção de editar.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Cria um novo registro de afastamento
            novo_afastamento = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                afastamento=True,
                tipo_afastamento=tipo_afastamento,
                entrada=None,
                saida_almoco=None,
                retorno_almoco=None,
                saida=None,
                horas_trabalhadas=None, # Afastamento não conta horas
                observacoes=None # Pode adicionar um campo de observação ao form se necessário
            )

            db.session.add(novo_afastamento)
            db.session.commit()

            flash('Registro de afastamento criado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar afastamento para {current_user.email}: {e}", exc_info=True)
            flash('Erro ao registrar afastamento. Tente novamente.', 'danger')

    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")


@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
    # ... (código mantido como na versão anterior) ...
    flash('Use a opção "Registrar Afastamento" para registrar férias.', 'info')
    return redirect(url_for('main.registrar_afastamento', **request.args))


# --- CORREÇÃO CALENDÁRIO: Função reescrita ---
@main.route('/calendario')
@login_required
def calendario():
    """Rota para o calendário do usuário."""
    usuario_ctx, usuarios_admin = get_usuario_contexto()

    hoje = date.today()
    mes_req = request.args.get('mes', default=hoje.month, type=int)
    ano_req = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Valida mês e ano
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido. Exibindo mês atual.', 'warning')
        # Adicionar validação de ano se necessário

        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)


        # Obtém os registros de ponto do mês para o usuário do contexto
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).all()
        registros_dict = {r.data: r for r in registros} # Dicionário para acesso rápido

        # Obtém os feriados do mês
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # Calcula estatísticas (igual ao dashboard)
        dias_uteis = 0
        dias_trabalhados = 0
        dias_afastamento = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_dict.get(data_atual)
                 if registro_dia and registro_dia.afastamento:
                     dias_afastamento += 1
                 else:
                     dias_uteis += 1

        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None:
                dias_trabalhados += 1
                horas_trabalhadas += r.horas_trabalhadas

        carga_horaria_devida = dias_uteis * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

        # Nomes dos meses
        nomes_meses = [
            '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        nome_mes = nomes_meses[mes_req]

        # Mês/Ano anterior e próximo para navegação
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        # --- Geração da Estrutura do Calendário usando calendar.monthcalendar ---
        cal = calendar.Calendar(firstweekday=6) # Começa a semana no Domingo (6)
        semanas_mes = cal.monthdayscalendar(ano_req, mes_req)
        calendario_data = []

        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                dia_info = {
                    'dia': dia,
                    'data': None,
                    'is_mes_atual': False,
                    'registro': None,
                    'feriado': None,
                    'is_hoje': False,
                    'is_fim_semana': False
                }
                if dia != 0: # Dia pertence ao mês atual
                    data_atual = date(ano_req, mes_req, dia)
                    dia_info['data'] = data_atual
                    dia_info['is_mes_atual'] = True
                    dia_info['registro'] = registros_dict.get(data_atual)
                    dia_info['feriado'] = feriados_dict.get(data_atual)
                    dia_info['is_hoje'] = (data_atual == hoje)
                    dia_info['is_fim_semana'] = (data_atual.weekday() >= 5) # Sábado (5) ou Domingo (6)
                # Se dia == 0, significa que é do mês anterior/seguinte,
                # o template pode lidar com isso ou podemos preencher aqui se necessário.
                # Por simplicidade, o template tratará dias 0 como células vazias ou de outro mês.
                semana_data.append(dia_info)
            calendario_data.append(semana_data)
        # ---------------------------------------------------------------------

        return render_template('main/calendario.html',
                              # Passando a nova estrutura de dados
                              calendario_data=calendario_data,
                              # Dados do resumo e navegação (mantidos)
                              mes_atual=mes_req,
                              ano_atual=ano_req,
                              nome_mes=nome_mes,
                              dias_uteis=dias_uteis,
                              dias_trabalhados=dias_trabalhados,
                              dias_afastamento=dias_afastamento,
                              horas_trabalhadas=horas_trabalhadas,
                              carga_horaria_devida=carga_horaria_devida,
                              saldo_horas=saldo_horas,
                              media_diaria=media_diaria,
                              usuario=usuario_ctx,
                              usuarios=usuarios_admin,
                              mes_anterior=mes_anterior,
                              ano_anterior=ano_anterior,
                              proximo_mes=proximo_mes,
                              proximo_ano=proximo_ano
                              )

    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao carregar calendário: {e}", exc_info=True)
        flash('Erro ao carregar o calendário. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))
# -------------------------------------------------

@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    # ... (código mantido como na versão anterior) ...
    usuario_ctx, usuarios_admin = get_usuario_contexto()

    hoje = date.today()
    mes_req = request.args.get('mes', default=hoje.month, type=int)
    ano_req = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Valida mês e ano
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido. Exibindo mês atual.', 'warning')

        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)


        # Obtém os registros de ponto do mês para o usuário do contexto
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all() # Ordenar por data ascendente para o relatório

        # Obtém os feriados do mês
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # Cria dicionário de registros por data para acesso fácil no template
        registros_por_data = {registro.data: registro for registro in registros}

        # Obtém as atividades dos registros do mês
        ponto_ids = [r.id for r in registros]
        atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
        atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto:
                atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao) # Apenas a descrição

        # Calcula estatísticas (igual ao dashboard/calendário)
        dias_uteis = 0
        dias_trabalhados = 0
        dias_afastamento = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_por_data.get(data_atual)
                 if registro_dia and registro_dia.afastamento:
                     dias_afastamento += 1
                 else:
                     dias_uteis += 1

        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None:
                dias_trabalhados += 1
                horas_trabalhadas += r.horas_trabalhadas

        carga_horaria_devida = dias_uteis * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

        # Nomes dos meses
        nomes_meses = [
            '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        nome_mes = nomes_meses[mes_req]

        # Mês/Ano anterior e próximo para navegação
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        return render_template('main/relatorio_mensal.html',
                              registros=registros, # Lista ordenada asc
                              mes_atual=mes_req,
                              ano_atual=ano_req,
                              nome_mes=nome_mes,
                              mes_anterior=mes_anterior,
                              ano_anterior=ano_anterior,
                              proximo_mes=proximo_mes,
                              proximo_ano=proximo_ano,
                              dias_uteis=dias_uteis,
                              dias_trabalhados=dias_trabalhados,
                              dias_afastamento=dias_afastamento,
                              horas_trabalhadas=horas_trabalhadas,
                              carga_horaria_devida=carga_horaria_devida,
                              saldo_horas=saldo_horas,
                              media_diaria=media_diaria,
                              feriados_dict=feriados_dict,
                              feriados_datas=feriados_datas,
                              registros_por_data=registros_por_data, # Dicionário
                              atividades_por_ponto=atividades_por_ponto, # Dicionário de atividades
                              usuario=usuario_ctx,
                              usuarios=usuarios_admin,
                              date=date, # Classe date
                              ultimo_dia=ultimo_dia, # Objeto date
                              ano=ano_req, # Alias para ano_atual
                              mes=mes_req  # Alias para mes_atual
                              )

    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True)
        flash('Erro ao gerar o relatório mensal. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))


@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    # ... (código mantido como na versão anterior) ...
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
             flash(f"Usuário com ID {user_id_req} não encontrado para gerar PDF.", "warning")
             return redirect(request.referrer or url_for('main.dashboard')) # Volta para onde veio

    # Obter mês/ano
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Importar a função de geração de PDF do utils
        from app.utils.export import generate_pdf
        pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano)

        if pdf_rel_path:
            # Constrói o caminho absoluto seguro
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                 # Gera nome do arquivo para download
                 nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower() # Nome do mês
                 download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                 return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else:
                 logger.error(f"Arquivo PDF gerado não encontrado em: {pdf_abs_path}")
                 flash('Erro: Arquivo PDF gerado não encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório PDF.', 'danger')

    except Exception as e:
        logger.error(f"Erro ao gerar/enviar PDF para usuário {usuario_alvo.id} ({mes}/{ano}): {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')

    # Redireciona de volta em caso de erro
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))


@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    # ... (código mantido como na versão anterior) ...
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
             flash(f"Usuário com ID {user_id_req} não encontrado para gerar Excel.", "warning")
             return redirect(request.referrer or url_for('main.dashboard'))

    # Obter mês/ano
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Importar a função de geração de Excel do utils
        from app.utils.export import generate_excel # Assumindo que a função existe
        excel_rel_path = generate_excel(usuario_alvo.id, mes, ano)

        if excel_rel_path:
            excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path)
            if os.path.exists(excel_abs_path):
                 nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                 download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"
                 return send_file(excel_abs_path, as_attachment=True, download_name=download_name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                 logger.error(f"Arquivo Excel gerado não encontrado em: {excel_abs_path}")
                 flash('Erro: Arquivo Excel gerado não encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório Excel.', 'danger')

    except Exception as e:
        logger.error(f"Erro ao gerar/enviar Excel para usuário {usuario_alvo.id} ({mes}/{ano}): {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o Excel.', 'danger')

    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))


@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto():
    # ... (código mantido como na versão anterior) ...
    registro = Ponto.query.get_or_404(ponto_id)

    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Busca atividades associadas
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()

    # Busca o usuário dono do registro (necessário para o template)
    usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono:
         # Situação inesperada, mas tratar por segurança
         flash('Usuário associado a este registro não encontrado.', 'danger')
         return redirect(url_for('main.dashboard'))


    # Passa a variável como 'registro' para o template
    return render_template('main/visualizar_ponto.html',
                           registro=registro,
                           atividades=atividades,
                           usuario=usuario_dono, # Passa o dono do registro
                           title="Visualizar Registro") # Adiciona title


@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto():
    # ... (código mantido como na versão anterior) ...
    registro = Ponto.query.get_or_404(ponto_id)
    data_registro = registro.data # Guarda data para redirecionamento

    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # Exclui o registro (atividades associadas devem ser excluídas pelo cascade="all, delete-orphan" no modelo Ponto)
        db.session.delete(registro)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
        flash('Erro ao excluir registro. Tente novamente.', 'danger')

    # Redireciona para o dashboard do mês/ano do registro excluído
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))


@main.route('/perfil')
@login_required
def perfil():
    # ... (código mantido como na versão anterior) ...
    usuario_atualizado = User.query.get(current_user.id)
    if not usuario_atualizado:
         # Se o usuário não for encontrado no DB (improvável, mas possível)
         flash('Erro ao carregar dados do perfil.', 'danger')
         return redirect(url_for('main.dashboard'))

    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")


@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    # ... (código mantido como na versão anterior) ...
    if request.method == 'POST':
        try:
            # Obtém os dados do formulário como listas
            datas_str = request.form.getlist('datas[]')
            entradas_str = request.form.getlist('entradas[]')
            saidas_almoco_str = request.form.getlist('saidas_almoco[]')
            retornos_almoco_str = request.form.getlist('retornos_almoco[]')
            saidas_str = request.form.getlist('saidas[]')
            atividades_desc = request.form.getlist('atividades[]')

            registros_criados = 0
            registros_ignorados = 0
            datas_processadas = set() # Para evitar processar a mesma data duas vezes se enviada

            # Itera pelo número de datas enviadas (assumindo que é o campo principal)
            for i in range(len(datas_str)):
                data_str = datas_str[i]
                if not data_str: # Pula linhas sem data
                    continue

                # Converte a data
                try:
                    data = date.fromisoformat(data_str)
                except ValueError:
                    flash(f'Formato de data inválido ignorado: {data_str}', 'warning')
                    continue

                # Evita duplicados no mesmo envio
                if data in datas_processadas:
                    continue
                datas_processadas.add(data)

                # Verifica se já existe registro para esta data
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente:
                    flash(f'Registro para {data.strftime("%d/%m/%Y")} já existe. Ignorado.', 'info')
                    registros_ignorados += 1
                    continue

                # Obtém os horários para este índice (com segurança)
                entrada_str = entradas_str[i] if i < len(entradas_str) else None
                saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None
                retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None
                saida_str_i = saidas_str[i] if i < len(saidas_str) else None
                atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None

                # Converte horários (com tratamento de erro)
                try:
                    entrada_t = time.fromisoformat(entrada_str) if entrada_str else None
                    saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None
                    retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None
                    saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError:
                    flash(f'Formato de hora inválido para {data.strftime("%d/%m/%Y")}. Ignorado.', 'warning')
                    continue

                # Calcula horas
                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)

                # Cria o novo registro de ponto
                novo_registro = Ponto(
                    user_id=current_user.id,
                    data=data,
                    entrada=entrada_t,
                    saida_almoco=saida_almoco_t,
                    retorno_almoco=retorno_almoco_t,
                    saida=saida_t,
                    horas_trabalhadas=horas_calculadas,
                    afastamento=False,
                    tipo_afastamento=None
                )
                db.session.add(novo_registro)

                # Salvar atividade associada
                try:
                    db.session.flush() # Garante que o ID esteja disponível
                    if atividade_desc_i:
                         atividade = Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i)
                         db.session.add(atividade)
                    db.session.commit() # Commit final para ponto e atividade
                    registros_criados += 1
                except Exception as commit_err:
                     db.session.rollback() # Desfaz o flush e add se o commit falhar
                     logger.error(f"Erro ao salvar registro/atividade para data {data}: {commit_err}", exc_info=True)
                     flash(f'Erro ao salvar registro para {data.strftime("%d/%m/%Y")}.', 'danger')

            # Mensagens de feedback (ajustadas)
            if registros_criados > 0 and registros_ignorados == 0:
                flash(f'{registros_criados} registro(s) de ponto criado(s) com sucesso!', 'success')
            elif registros_criados > 0 and registros_ignorados > 0:
                flash(f'{registros_criados} registro(s) criado(s). {registros_ignorados} dia(s) ignorado(s) pois já possuíam registro.', 'warning')
            elif registros_ignorados > 0 and registros_criados == 0:
                 flash('Nenhum registro novo foi criado. Registros para as datas informadas já existiam.', 'info')
            elif len(datas_processadas) == 0:
                 flash('Nenhuma data válida foi informada para registro.', 'warning')
            else: # Caso de erro ao salvar todos
                 flash('Nenhum registro foi criado devido a erros.', 'danger')


            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback() # Garante rollback em caso de erro inesperado
            logger.error(f"Erro ao processar múltiplos pontos para {current_user.email}: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao processar os registros.', 'danger')
            # Redireciona de volta para o formulário (os dados não serão mantidos)
            return redirect(url_for('main.registrar_multiplo_ponto'))

    # Se GET
    return render_template('main/registrar_multiplo_ponto.html', title="Registrar Múltiplos Pontos")


@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade():
    # ... (código mantido como na versão anterior) ...
    ponto = Ponto.query.get_or_404(ponto_id)

    # Verifica permissão
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar atividades deste registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Instancia o formulário
    form = AtividadeForm()
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    if form.validate_on_submit():
        # Processa o POST request
        try:
            descricao = form.descricao.data.strip() # Pega do formulário

            if atividade_existente:
                # Atualiza atividade existente
                atividade_existente.descricao = descricao
            else:
                # Cria nova atividade se não existir
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao)
                db.session.add(nova_atividade)

            db.session.commit()
            flash('Atividade salva com sucesso!', 'success')
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar atividade para ponto {ponto_id}: {e}", exc_info=True)
            flash('Erro ao salvar atividade.', 'danger')

    elif request.method == 'GET':
        # Preenche o formulário com dados existentes no GET request
        if atividade_existente:
            form.descricao.data = atividade_existente.descricao

    # Renderiza o template passando o form
    return render_template('main/registrar_atividade.html',
                           ponto=ponto,
                           form=form, # Passa o objeto form
                           title="Registrar/Editar Atividade")

