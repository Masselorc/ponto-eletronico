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
# Importar novo modelo
from app.models.relatorio_completo import RelatorioMensalCompleto

# --- Definição do Blueprint 'main' MOVIDA PARA CIMA ---
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# --- FIM DA MOVIMENTAÇÃO ---

# Importações de módulos da aplicação (AGORA DEPOIS DA DEFINIÇÃO DO BLUEPRINT)
from app import db # Importa db DEPOIS que 'main' foi definido
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
# Importa todos os forms necessários
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app.forms.relatorio import RelatorioCompletoForm
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
    # ... (código omitido por brevidade) ...
    pass

# Função get_usuario_contexto (mantida)
def get_usuario_contexto():
    # ... (código omitido por brevidade) ...
    pass

# Rota index (mantida)
@main.route('/')
@login_required
def index():
    # ... (código omitido por brevidade) ...
    pass

# Rota dashboard (mantida)
@main.route('/dashboard')
@login_required
def dashboard():
    # ... (código omitido por brevidade) ...
    pass

# Rota registrar_ponto (mantida)
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    # ... (código omitido por brevidade) ...
    pass

# Rota editar_ponto (mantida)
@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    # ... (código omitido por brevidade) ...
    pass

# Rota registrar_afastamento (mantida)
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    # ... (código omitido por brevidade) ...
    pass

# Rota registrar_ferias (mantida)
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
     # ... (código omitido por brevidade) ...
     pass

# Rota do Calendário (mantida)
@main.route('/calendario')
@login_required
def calendario():
    # ... (código omitido por brevidade) ...
    pass

# Rota para o Relatório Mensal detalhado (GET) (mantida)
@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    # ... (código omitido por brevidade, mas inclui pré-preenchimento do form) ...
    pass

# Rota para exportar o relatório mensal padrão em PDF (mantida)
@main.route('/relatorio-mensal/pdf')
@login_required
def relatorio_mensal_pdf():
    # ... (código omitido por brevidade) ...
    pass

# Rota para exportar o relatório mensal em Excel (mantida)
@main.route('/relatorio-mensal/excel')
@login_required
def relatorio_mensal_excel():
    # ... (código omitido por brevidade) ...
    pass

# Rota para SALVAR o relatório completo (mantida)
@main.route('/salvar-relatorio-completo', methods=['POST'])
@login_required
def salvar_relatorio_completo():
    # ... (código omitido por brevidade) ...
    pass

# Rota para EXPORTAR o PDF Completo (mantida)
@main.route('/exportar-relatorio-completo/pdf')
@login_required
def exportar_relatorio_completo_pdf():
    # ... (código omitido por brevidade) ...
    pass

# --- ROTA ATUALIZADA: Visualizar Relatório Completo em HTML ---
@main.route('/visualizar-relatorio-completo')
@login_required
def visualizar_relatorio_completo():
    """Exibe o relatório completo salvo em formato HTML."""
    # Inicializa valores de fallback para o redirect em caso de erro
    user_id_fb = current_user.id
    mes_fb = date.today().month
    ano_fb = date.today().year

    try:
        # Tenta obter user_id, mes e ano da URL
        user_id = request.args.get('user_id', type=int)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        # Atualiza os valores de fallback se os argumentos estiverem presentes
        user_id_fb = user_id if user_id else user_id_fb
        mes_fb = mes if mes else mes_fb
        ano_fb = ano if ano else ano_fb

        # Verifica se os parâmetros necessários foram recebidos
        if not user_id or not mes or not ano:
            flash("Informações insuficientes para visualizar o relatório (usuário, mês ou ano ausente).", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb)) # Usa fallbacks

        # Verifica permissão
        if user_id != current_user.id and not current_user.is_admin:
            flash("Você não tem permissão para visualizar este relatório.", 'danger')
            return redirect(url_for('main.dashboard'))

        # Busca o relatório completo salvo no banco
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=user_id, ano=ano, mes=mes
        ).first()

        # Verifica se o relatório salvo foi encontrado
        if not relatorio_salvo:
            flash("Nenhum relatório completo salvo encontrado para este período.", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        # Busca os dados base do relatório mensal (pode levantar ValueError)
        dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)

        # --- CORREÇÃO: Construção segura do contexto ---
        contexto_completo = {
            **dados_relatorio_base, # Desempacota dados base primeiro
            # Usa getattr para acessar atributos do relatorio_salvo com segurança
            'autoavaliacao_data': getattr(relatorio_salvo, 'autoavaliacao', ''),
            'dificuldades_data': getattr(relatorio_salvo, 'dificuldades', ''),
            'sugestoes_data': getattr(relatorio_salvo, 'sugestoes', ''),
            'declaracao_marcada': getattr(relatorio_salvo, 'declaracao_marcada', False),
            # Verifica se updated_at existe antes de formatar
            'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y %H:%M:%S') if relatorio_salvo.updated_at else 'N/A',
            'mes_atual': mes, # Passa para o template
            'ano_atual': ano, # Passa para o template
            # Define o título usando .get para nome_mes com fallback
            'titulo': f'Relatório de Produtividade Mensal - {dados_relatorio_base.get("nome_mes", "Mês Inválido")}/{ano}'
        }
        # --- FIM DA CORREÇÃO ---

        # Renderiza o template HTML de visualização
        return render_template('main/visualizar_relatorio_completo.html', **contexto_completo)

    except ValueError as ve: # Captura erros de _get_relatorio_mensal_data ou conversão
        logger.error(f"ValueError ao visualizar relatório completo: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para visualização: {ve}.", 'danger')
    except Exception as e: # Captura outros erros inesperados (possivelmente de template)
        logger.error(f"Erro inesperado ao visualizar relatório completo: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao visualizar o relatório completo. Verifique os logs para detalhes.', 'danger') # Mensagem mais informativa

    # Redireciona de volta para a página do relatório mensal em caso de qualquer erro
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))
# --- FIM DA ROTA ATUALIZADA ---


# Rotas visualizar_ponto, excluir_ponto, perfil, registrar_multiplo_ponto, registrar_atividade (mantidas)
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    # ... (código omitido por brevidade) ...
    pass

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    # ... (código omitido por brevidade) ...
    pass

@main.route('/perfil')
@login_required
def perfil():
    # ... (código omitido por brevidade) ...
    pass

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    # ... (código omitido por brevidade) ...
    pass

@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    # ... (código omitido por brevidade) ...
    pass
