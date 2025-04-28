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
def _get_relatorio_mensal_data(user_id, mes, ano):
    """Busca e calcula os dados necessários para o relatório mensal."""
    usuario = User.query.get(user_id)
    if not usuario: raise ValueError(f"Usuário com ID {user_id} não encontrado.")
    if not (1 <= mes <= 12): raise ValueError("Mês inválido.")
    primeiro_dia = date(ano, mes, 1); num_dias_mes = calendar.monthrange(ano, mes)[1]; ultimo_dia = date(ano, mes, num_dias_mes)
    registros = Ponto.query.filter(Ponto.user_id == user_id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data).all()
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
    return {'usuario': usuario, 'registros': registros, 'registros_por_data': registros_por_data, 'mes_atual': mes, 'ano_atual': ano, 'nome_mes': nome_mes, 'mes_anterior': mes_anterior, 'ano_anterior': ano_anterior, 'proximo_mes': proximo_mes, 'proximo_ano': proximo_ano, 'dias_uteis': dias_uteis_potenciais, 'dias_trabalhados': dias_trabalhados, 'dias_afastamento': dias_afastamento, 'horas_trabalhadas': horas_trabalhadas, 'carga_horaria_devida': carga_horaria_devida, 'saldo_horas': saldo_horas, 'media_diaria': media_diaria, 'feriados_dict': feriados_dict, 'feriados_datas': feriados_datas, 'atividades_por_ponto': atividades_por_ponto, 'ultimo_dia': ultimo_dia, 'date_obj': date}

# Função auxiliar para calcular horas (mantida)
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    # ... (código mantido) ...
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

# Função auxiliar para obter contexto do usuário (mantida)
def get_usuario_contexto():
    # ... (código mantido) ...
    user_id_req = request.args.get('user_id', type=int); usuario_selecionado = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_selecionado = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning")
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

# Rota index (mantida)
@main.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

# Rota dashboard (mantida)
@main.route('/dashboard')
@login_required
def dashboard():
    # ... (código mantido) ...
    try:
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today(); mes_req = request.args.get('mes', default=hoje.month, type=int); ano_req = request.args.get('ano', default=hoje.year, type=int)
        if not (1 <= mes_req <= 12): mes_req = hoje.month; flash('Mês inválido.', 'warning')
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req)
        # Busca registros ordenados para o dashboard especificamente
        registros_dashboard = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= dados_relatorio['primeiro_dia'], # Assumindo que _get_relatorio_mensal_data retorna isso
            Ponto.data <= dados_relatorio['ultimo_dia']
        ).order_by(Ponto.data.desc()).all() # Ordem descendente para dashboard
        contexto_template = {**dados_relatorio, 'registros': registros_dashboard, 'usuarios': usuarios_admin}
        return render_template('main/dashboard.html', **contexto_template)
    except Exception as e: logger.error(f"Erro dashboard: {e}", exc_info=True); flash('Erro ao carregar dashboard.', 'danger'); return redirect(url_for('main.index'))

# Rota registrar_ponto
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Registra um novo ponto para um dia específico."""
    form = RegistroPontoForm()
    if request.method == 'GET':
        data_query = request.args.get('data')
        # --- CORREÇÃO DA SINTAXE (Garantir que está assim) ---
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash('Data na URL inválida.', 'warning')
        # --- FIM DA CORREÇÃO ---

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

# Restante das rotas (editar_ponto, registrar_afastamento, etc.) mantidas como estavam...
# ... (código das outras rotas) ...

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
        dados_relatorio = _get_relatorio_mensal_data(usuario_ctx.id, mes_req, ano_req)
        form_completo = RelatorioCompletoForm()
        contexto_template = {**dados_relatorio, 'usuarios': usuarios_admin, 'form_completo': form_completo}
        return render_template('main/relatorio_mensal.html', **contexto_template)
    except ValueError as ve: flash(str(ve), 'danger'); return redirect(url_for('main.dashboard'))
    except Exception as e: logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True); flash('Erro ao gerar o relatório mensal.', 'danger'); return redirect(url_for('main.dashboard'))

# Rota para gerar PDF completo com autoavaliação (POST)
@main.route('/gerar-relatorio-completo/pdf', methods=['POST'])
@login_required
def gerar_relatorio_completo_pdf():
    """Processa o formulário de autoavaliação e gera o PDF completo."""
    form = RelatorioCompletoForm()
    if form.validate_on_submit():
        try:
            user_id = int(form.user_id.data); mes = int(form.mes.data); ano = int(form.ano.data)
            autoavaliacao_data = form.autoavaliacao.data; dificuldades_data = form.dificuldades.data; sugestoes_data = form.sugestoes.data; declaracao_marcada = form.declaracao.data
            dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)
            contexto_completo = {**dados_relatorio_base, 'autoavaliacao_data': autoavaliacao_data, 'dificuldades_data': dificuldades_data, 'sugestoes_data': sugestoes_data, 'declaracao_marcada': declaracao_marcada, 'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'), 'titulo': f'Relatório de Ponto e Autoavaliação - {dados_relatorio_base["nome_mes"]}/{ano}'}
            from app.utils.export import generate_pdf
            pdf_rel_path = generate_pdf(user_id, mes, ano, context_completo=contexto_completo)
            if pdf_rel_path:
                pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
                if os.path.exists(pdf_abs_path):
                    usuario_alvo = dados_relatorio_base['usuario']; nome_mes_str = dados_relatorio_base['nome_mes'].lower(); download_name = f"relatorio_completo_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                    return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
                else: logger.error(f"Arquivo PDF completo não encontrado: {pdf_abs_path}"); flash('Erro interno: Arquivo PDF completo gerado não foi encontrado.', 'danger')
            else: flash('Erro ao gerar o relatório completo em PDF.', 'danger')
        except ValueError as ve: flash(f"Erro ao buscar dados para o relatório: {ve}", 'danger')
        except Exception as e: logger.error(f"Erro ao gerar PDF completo: {e}", exc_info=True); flash('Ocorreu um erro inesperado ao gerar o PDF completo.', 'danger')
    else:
        user_id = form.user_id.data or current_user.id; mes = form.mes.data or date.today().month; ano = form.ano.data or date.today().year
        for field, errors in form.errors.items():
            for error in errors: flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')
        return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))
    user_id_fallback = form.user_id.data or current_user.id; mes_fallback = form.mes.data or date.today().month; ano_fallback = form.ano.data or date.today().year
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fallback, mes=mes_fallback, ano=ano_fallback))

# ... (outras rotas como visualizar_ponto, excluir_ponto, perfil, etc.) ...

