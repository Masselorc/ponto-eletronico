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
from sqlalchemy import desc # Importado para ordenação
# --- CORREÇÃO: Importar novo modelo ---
from app.models.relatorio_completo import RelatorioMensalCompleto
# ------------------------------------

# --- Definição do Blueprint 'main' ANTES das importações da app ---
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# --- FIM DA CORREÇÃO ANTERIOR (ImportError) ---

# Importações de módulos da aplicação
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
# Importa todos os forms necessários
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app.forms.relatorio import RelatorioCompletoForm
from app import db
# Importa a função auxiliar refatorada (se aplicável, senão definir aqui)
# from .utils import _get_relatorio_mensal_data # Exemplo se refatorado para utils

# --- Função Auxiliar Refatorada para buscar dados do relatório ---
# (Coloque a definição de _get_relatorio_mensal_data aqui se não estiver em utils)
def _get_relatorio_mensal_data(user_id, mes, ano, order_desc=False):
    """Busca e calcula os dados necessários para o relatório mensal."""
    usuario = User.query.get(user_id)
    if not usuario: raise ValueError(f"Usuário com ID {user_id} não encontrado.")
    if not (1 <= mes <= 12): raise ValueError("Mês inválido.")
    primeiro_dia = date(ano, mes, 1); num_dias_mes = calendar.monthrange(ano, mes)[1]; ultimo_dia = date(ano, mes, num_dias_mes)
    order_column = Ponto.data.desc() if order_desc else Ponto.data.asc()
    registros = Ponto.query.filter(Ponto.user_id == user_id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(order_column).all()
    feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all()
    feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
    registros_por_data = {r.data: r for r in registros}; ponto_ids = [r.id for r in registros]; atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all(); atividades_por_ponto = {}
    for atv in atividades:
        if atv.ponto_id not in atividades_por_ponto: atividades_por_ponto[atv.ponto_id] = []
        atividades_por_ponto[atv.ponto_id].append(atv.descricao)
    dias_uteis_potenciais = 0; dias_afastamento = 0; dias_trabalhados = 0; horas_trabalhadas = 0.0
    for dia_num in range(1, ultimo_dia.day + 1):
        data_atual = date(ano, mes, dia_num)
        if data_atual.weekday() < 5 and data_atual not in feriados_datas:
            dias_uteis_potenciais += 1; registro_dia = registros_por_data.get(data_atual)
            if registro_dia and registro_dia.afastamento: dias_afastamento += 1
    for r_data, r_obj in registros_por_data.items():
        if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
             if r_data.weekday() < 5 and r_data not in feriados_datas: dias_trabalhados += 1; horas_trabalhadas += r_obj.horas_trabalhadas
    carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
    nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes]
    mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano); proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)
    return {'usuario': usuario, 'registros': registros, 'registros_por_data': registros_por_data, 'primeiro_dia': primeiro_dia, 'ultimo_dia': ultimo_dia, 'mes_atual': mes, 'ano_atual': ano, 'nome_mes': nome_mes, 'mes_anterior': mes_anterior, 'ano_anterior': ano_anterior, 'proximo_mes': proximo_mes, 'proximo_ano': proximo_ano, 'dias_uteis': dias_uteis_potenciais, 'dias_trabalhados': dias_trabalhados, 'dias_afastamento': dias_afastamento, 'horas_trabalhadas': horas_trabalhadas, 'carga_horaria_devida': carga_horaria_devida, 'saldo_horas': saldo_horas, 'media_diaria': media_diaria, 'feriados_dict': feriados_dict, 'feriados_datas': feriados_datas, 'atividades_por_ponto': atividades_por_ponto, 'date_obj': date}

# Função calcular_horas (mantida)
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    """Calcula as horas trabalhadas com base nos horários fornecidos."""
    if not entrada or not saida:
        return None # Retorna None se entrada ou saída estiverem faltando
    try:
        # Combina a data de referência com os horários para criar objetos datetime
        entrada_dt = datetime.combine(data_ref, entrada)
        saida_dt = datetime.combine(data_ref, saida)

        # Se a saída for no dia seguinte (ex: trabalho noturno)
        if saida_dt < entrada_dt:
            saida_dt += timedelta(days=1)

        # Calcula a diferença total
        diff_total = saida_dt - entrada_dt
        horas_trabalhadas = diff_total.total_seconds() / 3600 # Converte para horas

        # Se houver registro de almoço, subtrai a duração do almoço
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco)
            retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)

            # Se o retorno do almoço for no dia seguinte
            if retorno_almoco_dt < saida_almoco_dt:
                retorno_almoco_dt += timedelta(days=1)

            diff_almoco = retorno_almoco_dt - saida_almoco_dt
            horas_trabalhadas -= diff_almoco.total_seconds() / 3600

        # Garante que as horas não sejam negativas
        return max(0, horas_trabalhadas)
    except Exception as e:
        # Loga o erro se ocorrer algum problema no cálculo
        logger.error(f"Erro ao calcular horas para data {data_ref}: {e}", exc_info=True)
        return None # Retorna None em caso de erro

# Função get_usuario_contexto (mantida)
def get_usuario_contexto():
    """Obtém o usuário a ser exibido (atual ou selecionado pelo admin)."""
    user_id_req = request.args.get('user_id', type=int) # Pega user_id da URL
    usuario_selecionado = current_user # Por padrão, é o usuário logado

    # Se o usuário logado for admin e um user_id foi passado na URL
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req) # Busca o usuário solicitado
        if usuario_req:
            usuario_selecionado = usuario_req # Define como usuário selecionado
        else:
            flash(f"Usuário com ID {user_id_req} não encontrado.", "warning")

    # Busca todos os usuários para o seletor do admin
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

# Rota index (mantida)
@main.route('/')
@login_required
def index():
    """Redireciona para o dashboard."""
    return redirect(url_for('main.dashboard'))

# Rota dashboard (mantida)
@main.route('/dashboard')
@login_required
def dashboard():
    """Exibe o dashboard principal com resumo mensal e últimos registros."""
    try:
        # Obtém o usuário do contexto (pode ser o logado ou um selecionado pelo admin)
        usuario_ctx, usuarios_admin = get_usuario_contexto()

        # Obtém mês e ano da URL ou usa o mês/ano atual
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Valida o mês
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido selecionado.', 'warning')

        # Busca os dados do relatório para o usuário e período selecionados
        # 'order_desc=True' para mostrar os mais recentes primeiro no dashboard
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req, order_desc=True)

        # Combina os dados do relatório com a lista de usuários (para o seletor do admin)
        contexto_template = {**dados_relatorio, 'usuarios': usuarios_admin}

        # Renderiza o template do dashboard passando o contexto
        return render_template('main/dashboard.html', **contexto_template)
    except ValueError as ve:
        # Erro ao buscar usuário ou mês inválido
        flash(str(ve), 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        # Qualquer outro erro inesperado
        logger.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
        flash('Ocorreu um erro ao carregar o dashboard.', 'danger')
        return redirect(url_for('main.index')) # Redireciona para uma página segura

# Rota registrar_ponto
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Registra um novo ponto para um dia específico."""
    form = RegistroPontoForm()

    # Se for um GET, verifica se uma data foi passada na URL para preencher o form
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try:
                # Tenta converter a data da URL e preencher o campo do formulário
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                # Se a data na URL for inválida, mostra um aviso
                flash('Data na URL inválida.', 'warning')

    # Se o formulário for enviado (POST) e for válido
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            # Verifica se já existe um registro para este usuário nesta data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Calcula as horas trabalhadas
            horas_calculadas = calcular_horas(
                data_selecionada,
                form.entrada.data,
                form.saida.data,
                form.saida_almoco.data,
                form.retorno_almoco.data
            )

            # Cria o novo objeto Ponto
            novo_registro = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data,
                retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data,
                horas_trabalhadas=horas_calculadas,
                observacoes=form.observacoes.data,
                resultados_produtos=form.resultados_produtos.data,
                afastamento=False, # Novo registro não é afastamento por padrão
                tipo_afastamento=None
            )
            db.session.add(novo_registro)
            db.session.flush() # Garante que o novo_registro tenha um ID

            # Adiciona atividades se foram preenchidas
            if form.atividades.data and form.atividades.data.strip():
                db.session.add(Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip()))

            db.session.commit() # Salva no banco
            flash('Registro de ponto criado com sucesso!', 'success')
            # Redireciona para o dashboard do mês do registro
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback() # Desfaz alterações em caso de erro
            logger.error(f"Erro ao registrar ponto: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o ponto.', 'danger')

    # Renderiza o template para GET ou se a validação falhar
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")

# Rota editar_ponto (mantida)
@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Edita um registro de ponto existente."""
    registro = Ponto.query.get_or_404(ponto_id) # Busca o registro ou retorna 404

    # Verifica permissão: usuário só pode editar seus próprios pontos (ou admin pode editar qualquer um)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = EditarPontoForm(obj=registro) # Cria o form preenchendo com dados do registro
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    # Se for GET, preenche o campo de atividades se existir
    if request.method == 'GET':
        if atividade_existente and not form.atividades.data:
            form.atividades.data = atividade_existente.descricao

    # Se o formulário for enviado e válido
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            # Atualiza os dados básicos do registro
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            registro.resultados_produtos = form.resultados_produtos.data

            # Se for afastamento, limpa os horários
            if is_afastamento:
                registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else:
                # Se não for afastamento, atualiza os horários e recalcula as horas
                registro.entrada=form.entrada.data
                registro.saida_almoco=form.saida_almoco.data
                registro.retorno_almoco=form.retorno_almoco.data
                registro.saida=form.saida.data
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada, form.entrada.data, form.saida.data,
                    form.saida_almoco.data, form.retorno_almoco.data
                )

            # Atualiza ou cria/remove a atividade
            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                if atividade_existente:
                    atividade_existente.descricao = descricao_atividade # Atualiza
                else:
                    db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade)) # Cria
            elif atividade_existente:
                db.session.delete(atividade_existente) # Remove se o campo ficou vazio

            db.session.commit() # Salva as alterações
            flash('Registro atualizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao atualizar o registro.', 'danger')

    # Renderiza o template para GET ou se a validação falhar
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

# Rota registrar_afastamento (mantida)
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    """Registra um dia como afastamento (férias, licença, etc.)."""
    form = RegistroAfastamentoForm()

    # Preenche data da URL se existir
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
            tipo_afastamento = form.tipo_afastamento.data

            # Verifica se já existe registro para o dia
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Cria um novo registro de ponto marcado como afastamento
            novo_afastamento = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                afastamento=True, # Marca como afastamento
                tipo_afastamento=tipo_afastamento,
                # Horários e outros campos ficam como None
                entrada=None, saida_almoco=None, retorno_almoco=None, saida=None,
                horas_trabalhadas=None, observacoes=None, resultados_produtos=None
            )
            db.session.add(novo_afastamento)
            db.session.commit()
            flash('Afastamento registrado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar afastamento: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o afastamento.', 'danger')

    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")

# Rota registrar_ferias (mantida - redireciona para afastamento)
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
     """Rota antiga para férias, agora redireciona para registrar_afastamento."""
     flash('Use a opção "Registrar Afastamento" para registrar férias.', 'info')
     # Mantém os parâmetros da URL (como 'data') ao redirecionar
     return redirect(url_for('main.registrar_afastamento', **request.args))

# Rota do Calendário (mantida)
@main.route('/calendario')
@login_required
def calendario():
    """Exibe o calendário mensal com os registros de ponto."""
    try:
        # Obtém usuário e período
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        # Busca os dados do relatório para o período
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req)

        # Gera a estrutura do calendário usando a biblioteca calendar
        cal = calendar.Calendar(firstweekday=6) # Começa no Domingo (6)
        semanas_mes = cal.monthdayscalendar(ano_req, mes_req)
        calendario_data = [] # Lista para armazenar os dados formatados para o template

        # Itera sobre as semanas e dias gerados pela biblioteca calendar
        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                # Cria um dicionário com informações padrão para cada célula do calendário
                dia_info = {
                    'dia': dia, # Número do dia (0 se for de outro mês)
                    'data': None, # Objeto date (será preenchido se for do mês atual)
                    'is_mes_atual': False, # Flag para indicar se o dia pertence ao mês atual
                    'registro': None, # Objeto Ponto (se houver registro)
                    'feriado': None, # Descrição do feriado (se houver)
                    'is_hoje': False, # Flag para o dia atual
                    'is_fim_semana': False # Flag para sábado/domingo
                }
                # Se o dia não for 0 (pertence ao mês atual)
                if dia != 0:
                    data_atual = date(ano_req, mes_req, dia)
                    # Atualiza o dicionário com informações específicas do dia
                    dia_info.update({
                        'data': data_atual,
                        'is_mes_atual': True,
                        'registro': dados_relatorio['registros_por_data'].get(data_atual), # Pega o registro (ou None)
                        'feriado': dados_relatorio['feriados_dict'].get(data_atual), # Pega o feriado (ou None)
                        'is_hoje': (data_atual == hoje),
                        'is_fim_semana': (data_atual.weekday() >= 5) # 5=Sábado, 6=Domingo
                    })
                semana_data.append(dia_info) # Adiciona info do dia à semana
            calendario_data.append(semana_data) # Adiciona semana ao calendário

        # Combina os dados do relatório com a estrutura do calendário e a lista de usuários
        contexto_template = {**dados_relatorio, 'calendario_data': calendario_data, 'usuarios': usuarios_admin}

        # Renderiza o template do calendário
        return render_template('main/calendario.html', **contexto_template)
    except Exception as e:
        logger.error(f"Erro ao carregar calendário: {e}", exc_info=True)
        flash('Ocorreu um erro ao carregar o calendário.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para o Relatório Mensal detalhado (GET)
@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Exibe o relatório mensal detalhado com opção de exportação e autoavaliação."""
    try:
        # Obtém usuário e período
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Busca os dados do relatório (ordenados por data ascendente para a tabela)
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req, order_desc=False)

        # Cria uma instância do formulário de autoavaliação
        form_completo = RelatorioCompletoForm()

        # Preenche dados dos campos ocultos no objeto form
        form_completo.user_id.data = str(usuario_ctx.id)
        form_completo.mes.data = str(mes_req)
        form_completo.ano.data = str(ano_req)

        # --- CORREÇÃO: Verifica se já existe um relatório completo salvo ---
        relatorio_completo_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=usuario_ctx.id,
            ano=ano_req,
            mes=mes_req
        ).first()
        # -----------------------------------------------------------------

        # Combina os dados do relatório com a lista de usuários e o form de autoavaliação
        contexto_template = {
            **dados_relatorio,
            'usuarios': usuarios_admin,
            'form_completo': form_completo,
            'relatorio_completo_salvo': relatorio_completo_salvo # Passa o resultado da consulta para o template
        }

        # Renderiza o template do relatório mensal
        return render_template('main/relatorio_mensal.html', **contexto_template)
    except ValueError as ve:
        flash(str(ve), 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True)
        flash('Erro ao gerar o relatório mensal.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para exportar o relatório mensal padrão em PDF (mantida)
@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    """Gera e envia o relatório mensal padrão em formato PDF."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user # Usuário padrão é o logado

    # Se admin e user_id especificado, busca o usuário alvo
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
            flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
            return redirect(request.referrer or url_for('main.dashboard'))

    # Obtém mês e ano
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Importa a função de geração de PDF (dentro do try para evitar erro se a importação falhar)
        from app.utils.export import generate_pdf
        # Gera o PDF padrão (sem contexto completo)
        pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano)

        if pdf_rel_path:
            # Constrói o caminho absoluto para o arquivo PDF gerado
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                # Define o nome do arquivo para download
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                # Envia o arquivo PDF para o usuário
                return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else:
                logger.error(f"Arquivo PDF não encontrado após geração: {pdf_abs_path}")
                flash('Erro interno: Arquivo PDF gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em PDF.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao gerar/enviar PDF: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')

    # Redireciona de volta para a página anterior ou para o relatório mensal
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para exportar o relatório mensal em Excel (mantida)
@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    """Gera e envia o relatório mensal em formato Excel."""
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user

    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
            flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
            return redirect(request.referrer or url_for('main.dashboard'))

    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        from app.utils.export import generate_excel
        excel_rel_path = generate_excel(usuario_alvo.id, mes, ano)

        if excel_rel_path:
            excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path)
            if os.path.exists(excel_abs_path):
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"
                # Envia o arquivo Excel
                return send_file(
                    excel_abs_path,
                    as_attachment=True,
                    download_name=download_name,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                logger.error(f"Arquivo Excel não encontrado após geração: {excel_abs_path}")
                flash('Erro interno: Arquivo Excel gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em Excel.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao gerar/enviar Excel: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o Excel.', 'danger')

    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# --- CORREÇÃO: Renomeada a rota e alterada a lógica para SALVAR ---
@main.route('/salvar-relatorio-completo', methods=['POST'])
@login_required
def salvar_relatorio_completo():
    """Salva os dados da autoavaliação no banco de dados."""
    form = RelatorioCompletoForm()
    user_id_fb = current_user.id
    mes_fb = date.today().month
    ano_fb = date.today().year

    # Tenta obter os dados do formulário para o redirect em caso de erro
    try:
        user_id_fb = int(form.user_id.data) if form.user_id.data else current_user.id
        mes_fb = int(form.mes.data) if form.mes.data else date.today().month
        ano_fb = int(form.ano.data) if form.ano.data else date.today().year
    except ValueError:
        pass # Usa os fallbacks se a conversão falhar

    if form.validate_on_submit():
        try:
            user_id_str = form.user_id.data
            mes_str = form.mes.data
            ano_str = form.ano.data

            if not user_id_str or not mes_str or not ano_str:
                logger.error(f"Dados ausentes no formulário ao salvar: user_id='{user_id_str}', mes='{mes_str}', ano='{ano_str}'")
                flash("Erro ao processar dados do formulário (ID, mês ou ano ausente). Tente novamente.", 'danger')
                return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))

            user_id = int(user_id_str)
            mes = int(mes_str)
            ano = int(ano_str)

            # Verifica se o usuário logado é o dono do relatório ou admin
            if user_id != current_user.id and not current_user.is_admin:
                 flash("Você não tem permissão para salvar este relatório.", 'danger')
                 return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))

            # Verifica se já existe um relatório salvo para este período/usuário
            relatorio_existente = RelatorioMensalCompleto.query.filter_by(
                user_id=user_id, ano=ano, mes=mes
            ).first()

            if relatorio_existente:
                # Atualiza o relatório existente
                relatorio_existente.autoavaliacao = form.autoavaliacao.data
                relatorio_existente.dificuldades = form.dificuldades.data
                relatorio_existente.sugestoes = form.sugestoes.data
                relatorio_existente.declaracao_marcada = form.declaracao.data
                relatorio_existente.updated_at = datetime.utcnow() # Atualiza timestamp
                flash_msg = 'Relatório completo atualizado com sucesso!'
            else:
                # Cria um novo registro
                novo_relatorio = RelatorioMensalCompleto(
                    user_id=user_id,
                    ano=ano,
                    mes=mes,
                    autoavaliacao=form.autoavaliacao.data,
                    dificuldades=form.dificuldades.data,
                    sugestoes=form.sugestoes.data,
                    declaracao_marcada=form.declaracao.data
                )
                db.session.add(novo_relatorio)
                flash_msg = 'Relatório completo salvo com sucesso!'

            db.session.commit() # Salva as alterações no banco
            flash(flash_msg, 'success')
            # Redireciona de volta para a página do relatório
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        except ValueError as ve:
            db.session.rollback()
            logger.error(f"ValueError ao salvar relatório completo: {ve}", exc_info=True)
            flash(f"Erro ao processar dados do relatório: {ve}. Verifique os valores.", 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro inesperado ao salvar relatório completo: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao salvar o relatório completo.', 'danger')
    else:
        # Se a validação do formulário falhar
        for field, errors in form.errors.items():
            for error in errors:
                label = getattr(getattr(form, field, None), 'label', None)
                field_name = label.text if label else field
                flash(f"Erro no campo '{field_name}': {error}", 'danger')

    # Redireciona de volta para a página do relatório em caso de erro de validação ou exceção
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))
# --- FIM DA ROTA DE SALVAR ---

# --- NOVA ROTA: Exportar PDF Completo ---
@main.route('/exportar-relatorio-completo/pdf')
@login_required
def exportar_relatorio_completo_pdf():
    """Gera e envia o PDF do relatório completo que foi previamente salvo."""
    try:
        # Tenta obter user_id, mes e ano da URL
        user_id = request.args.get('user_id', type=int)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not user_id or not mes or not ano:
            flash("Informações insuficientes para exportar o relatório (usuário, mês ou ano ausente).", 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        # Verifica permissão (usuário só pode exportar o seu, admin pode qualquer um)
        if user_id != current_user.id and not current_user.is_admin:
            flash("Você não tem permissão para exportar este relatório.", 'danger')
            return redirect(url_for('main.dashboard'))

        # Busca o relatório completo salvo no banco
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=user_id, ano=ano, mes=mes
        ).first()

        if not relatorio_salvo:
            flash("Nenhum relatório completo salvo encontrado para este período.", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        # Busca os dados base do relatório mensal
        dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)

        # Cria o contexto completo para o PDF, combinando dados base e dados salvos
        contexto_completo = {
            **dados_relatorio_base,
            'autoavaliacao_data': relatorio_salvo.autoavaliacao,
            'dificuldades_data': relatorio_salvo.dificuldades,
            'sugestoes_data': relatorio_salvo.sugestoes,
            'declaracao_marcada': relatorio_salvo.declaracao_marcada,
            'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y %H:%M:%S'), # Usa data da última atualização
            'titulo': f'Relatório de Ponto e Autoavaliação - {dados_relatorio_base["nome_mes"]}/{ano}'
        }

        # Gera o PDF
        from app.utils.export import generate_pdf
        pdf_rel_path = generate_pdf(user_id, mes, ano, context_completo=contexto_completo)

        if pdf_rel_path:
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                usuario_alvo = dados_relatorio_base['usuario']
                nome_mes_str = dados_relatorio_base['nome_mes'].lower()
                download_name = f"relatorio_completo_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                # Envia o arquivo
                return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else:
                logger.error(f"Arquivo PDF completo (export) não encontrado: {pdf_abs_path}")
                flash('Erro interno: Arquivo PDF gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório completo em PDF para exportação.', 'danger')

    except ValueError as ve:
        logger.error(f"ValueError ao exportar PDF completo: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para exportação: {ve}.", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao exportar PDF completo: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao exportar o relatório completo.', 'danger')

    # Redireciona de volta para a página do relatório em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))
# --- FIM DA NOVA ROTA ---


# Rotas visualizar_ponto, excluir_ponto, perfil, registrar_multiplo_ponto, registrar_atividade (mantidas)
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    """Exibe os detalhes de um registro de ponto específico."""
    registro = Ponto.query.get_or_404(ponto_id)

    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Busca atividades e o usuário dono do ponto
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono:
        flash('Usuário associado a este ponto não encontrado.', 'danger')
        return redirect(url_for('main.dashboard')) # Ou para admin.listar_usuarios

    return render_template('main/visualizar_ponto.html', registro=registro, atividades=atividades, usuario=usuario_dono, title="Visualizar Registro")

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """Exclui um registro de ponto."""
    registro = Ponto.query.get_or_404(ponto_id)
    data_registro = registro.data # Guarda a data para redirecionar

    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # Exclui o registro e suas atividades associadas (devido ao cascade)
        db.session.delete(registro)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
        flash('Ocorreu um erro ao excluir o registro.', 'danger')

    # Redireciona para o dashboard do mês do registro excluído
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

@main.route('/perfil')
@login_required
def perfil():
    """Exibe a página de perfil do usuário logado."""
    # Busca o usuário novamente para garantir dados atualizados
    usuario_atualizado = User.query.get(current_user.id)
    if not usuario_atualizado:
        flash('Erro ao carregar dados do perfil.', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Permite registrar pontos para múltiplos dias de uma vez."""
    form = MultiploPontoForm() # Form vazio, usado apenas para CSRF token

    if form.validate_on_submit(): # Valida o CSRF token
        try:
            # Obtém as listas de dados do formulário (enviados pelo JS)
            datas_str = request.form.getlist('datas[]')
            entradas_str = request.form.getlist('entradas[]')
            saidas_almoco_str = request.form.getlist('saidas_almoco[]')
            retornos_almoco_str = request.form.getlist('retornos_almoco[]')
            saidas_str = request.form.getlist('saidas[]')
            atividades_desc = request.form.getlist('atividades[]')
            resultados_produtos_desc = request.form.getlist('resultados_produtos[]')
            observacoes_desc = request.form.getlist('observacoes[]')

            registros_criados, registros_ignorados, registros_erro_almoco = 0, 0, 0
            datas_processadas = set() # Para evitar processar a mesma data duas vezes

            # Itera sobre as datas enviadas
            for i in range(len(datas_str)):
                data_str = datas_str[i]
                if not data_str: continue # Pula se a data estiver vazia

                try:
                    data = date.fromisoformat(data_str) # Converte string para date
                except ValueError:
                    flash(f'Formato de data inválido ignorado: {data_str}', 'warning')
                    continue

                if data in datas_processadas: continue # Pula se já processou esta data
                datas_processadas.add(data)

                # Verifica se já existe registro para o dia
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente:
                    flash(f'Registro para {data.strftime("%d/%m/%Y")} já existe e foi ignorado.', 'info')
                    registros_ignorados += 1
                    continue

                # Obtém os dados correspondentes para esta data (cuidado com índices)
                entrada_str = entradas_str[i] if i < len(entradas_str) else None
                saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None
                retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None
                saida_str_i = saidas_str[i] if i < len(saidas_str) else None
                atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None
                resultado_desc_i = resultados_produtos_desc[i].strip() if i < len(resultados_produtos_desc) and resultados_produtos_desc[i] else None
                observacao_i = observacoes_desc[i].strip() if i < len(observacoes_desc) and observacoes_desc[i] else None

                try:
                    # Converte strings de hora para objetos time
                    entrada_t = time.fromisoformat(entrada_str) if entrada_str else None
                    saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None
                    retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None
                    saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError:
                    flash(f'Formato de hora inválido para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning')
                    registros_erro_almoco += 1
                    continue

                # Validação do almoço (se entrada e saída foram preenchidas)
                if entrada_t and saida_t:
                    if not saida_almoco_t or not retorno_almoco_t:
                        flash(f'Erro na data {data.strftime("%d/%m/%Y")}: Horários de almoço obrigatórios para dias trabalhados. Registro ignorado.', 'warning')
                        registros_erro_almoco += 1
                        continue
                    try:
                        # Verifica duração mínima do almoço (1 hora)
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

                # Calcula horas e cria o novo registro
                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)
                novo_registro = Ponto(
                    user_id=current_user.id, data=data, entrada=entrada_t,
                    saida_almoco=saida_almoco_t, retorno_almoco=retorno_almoco_t, saida=saida_t,
                    horas_trabalhadas=horas_calculadas, afastamento=False, tipo_afastamento=None,
                    resultados_produtos=resultado_desc_i, observacoes=observacao_i
                )
                db.session.add(novo_registro)

                try:
                    db.session.flush() # Garante ID para a atividade
                    if atividade_desc_i:
                        db.session.add(Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i))
                    db.session.commit() # Salva registro e atividade
                    registros_criados += 1
                except Exception as commit_err:
                    db.session.rollback()
                    logger.error(f"Erro ao salvar registro/atividade para {data}: {commit_err}", exc_info=True)
                    flash(f'Erro ao salvar registro para {data.strftime("%d/%m/%Y")}.', 'danger')

            # Monta mensagem final para o usuário
            msg_parts = []
            if registros_criados > 0: msg_parts.append(f'{registros_criados} registro(s) criado(s)')
            if registros_ignorados > 0: msg_parts.append(f'{registros_ignorados} data(s) ignorada(s) por já existir registro')
            if registros_erro_almoco > 0: msg_parts.append(f'{registros_erro_almoco} registro(s) ignorado(s) por erro nos dados de almoço')

            if not msg_parts:
                 if len(datas_processadas) == 0: flash('Nenhuma data válida foi informada para registro.', 'warning')
                 else: flash('Nenhum novo registro criado (datas já possuíam registro ou tiveram erro).', 'info')
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

    # Renderiza a página para GET
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos")

@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    """Registra ou edita a atividade de um registro de ponto específico."""
    ponto = Ponto.query.get_or_404(ponto_id)

    # Verifica permissão
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar atividades deste registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = AtividadeForm()
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    if form.validate_on_submit():
        try:
            descricao = form.descricao.data.strip()
            if atividade_existente:
                atividade_existente.descricao = descricao # Atualiza
            else:
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao) # Cria
                db.session.add(nova_atividade)
            db.session.commit()
            flash('Atividade salva com sucesso!', 'success')
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar atividade para ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao salvar a atividade.', 'danger')
    elif request.method == 'GET':
        # Preenche o form com a descrição existente se for GET
        if atividade_existente:
            form.descricao.data = atividade_existente.descricao

    return render_template('main/registrar_atividade.html', ponto=ponto, form=form, title="Registrar/Editar Atividade")

