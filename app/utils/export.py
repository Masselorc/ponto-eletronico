# -*- coding: utf-8 -*-
import os
from datetime import datetime, date
from flask import render_template, current_app
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from io import BytesIO
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.models.user import User
from calendar import monthrange
# Importa a função auxiliar refatorada do controlador
from app.controllers.main import _get_relatorio_mensal_data

# Função create_pdf (mantida)
def create_pdf(template_name, output_path, **context):
    """Cria um arquivo PDF a partir de um template HTML."""
    try:
        html_content = render_template(template_name, **context)
        # Adiciona estilos CSS específicos para PDF (mantidos)
        pdf_styles = """
        <style>
            @page { size: letter portrait; margin: 1cm; }
            body { font-family: Arial, sans-serif; color: #333; font-size: 10pt; }
            .header { text-align: center; margin-bottom: 20px; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
            .header h1 { color: #0d6efd; margin: 0; font-size: 16pt; }
            .header p { color: #6c757d; margin: 3px 0 0 0; font-size: 9pt; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 9pt; }
            th { background-color: #e9ecef; color: #212529; font-weight: bold; text-align: center; padding: 5px; border: 1px solid #ccc; }
            td { border: 1px solid #ccc; padding: 5px; vertical-align: top; }
            tr:nth-child(even) { background-color: #f8f9fa; }
            .footer { text-align: center; font-size: 8pt; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 5px; color: #6c757d; position: fixed; bottom: 0; width: 100%; }
            .card { border: 1px solid #ddd; border-radius: 4px; margin-bottom: 15px; background-color: #fff; }
            .card-header { background-color: #f8f9fa; color: #212529; padding: 8px 12px; border-bottom: 1px solid #ddd; border-radius: 4px 4px 0 0; }
            .card-header h2 { font-size: 11pt; margin: 0; }
            .card-body { padding: 12px; }
            .card-body p { margin-bottom: 8px; line-height: 1.4; }
            .badge { display: inline-block; padding: .25em .6em; font-size: 75%; font-weight: 700; line-height: 1; text-align: center; white-space: nowrap; vertical-align: baseline; border-radius: .25rem; }
            .badge-success { color: #fff; background-color: #198754; }
            .badge-warning { color: #000; background-color: #ffc107; }
            .badge-danger { color: #fff; background-color: #dc3545; }
            .badge-info { color: #000; background-color: #0dcaf0; }
            .badge-secondary { color: #fff; background-color: #6c757d; }
            .text-center { text-align: center; }
            .text-end { text-align: right; }
            .text-muted { color: #6c757d; }
            .fw-bold { font-weight: bold; }
            .fst-italic { font-style: italic; }
            .small { font-size: 8pt; }
            /* Estilos específicos para autoavaliação */
            .autoavaliacao-section p { margin-left: 15px; }
            .declaracao-box { border: 1px solid #ccc; padding: 10px; margin-top: 10px; background-color: #f8f9fa; }
        </style>
        """
        html_content = html_content.replace('</head>', f'{pdf_styles}</head>')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as output_file:
            pisa_status = pisa.CreatePDF(html_content, dest=output_file)
        return pisa_status.err == 0
    except Exception as e:
        current_app.logger.error(f"Erro ao criar PDF: {e}", exc_info=True)
        return False

# Função create_excel (mantida)
def create_excel(data, headers, output_path):
    # ... (código mantido) ...
    try:
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Dados"
        header_font = Font(bold=True); header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid"); header_alignment = Alignment(horizontal="center", vertical="center"); thin_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
        for col_idx, header_text in enumerate(headers.values(), 1): cell = ws.cell(row=1, column=col_idx, value=header_text); cell.font = header_font; cell.fill = header_fill; cell.alignment = header_alignment; cell.border = thin_border
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, key in enumerate(headers.keys(), 1): cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(key, "")); cell.border = thin_border
        for col_idx in range(1, len(headers) + 1): ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 15
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        wb.save(output_path); return True
    except Exception as e: current_app.logger.error(f"Erro ao criar Excel: {e}"); return False

# Função calcular_estatisticas_mes (mantida, mas pode ser removida se _get_relatorio_mensal_data for usada sempre)
def calcular_estatisticas_mes(user_id, mes, ano):
    # ... (código mantido) ...
    try:
        primeiro_dia = date(ano, mes, 1); ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        registros = Ponto.query.filter(Ponto.user_id == user_id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data).all()
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all()
        feriados_datas = {feriado.data for feriado in feriados}
        dias_uteis_potenciais = 0; dias_afastamento = 0; dias_trabalhados = 0; horas_trabalhadas = 0
        registros_dict = {r.data: r for r in registros}
        for dia in range(1, ultimo_dia.day + 1):
            data_atual = date(ano, mes, dia)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro = registros_dict.get(data_atual)
                if registro and registro.afastamento: dias_afastamento += 1
        for r_data, r_obj in registros_dict.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                if r_data.weekday() < 5 and r_data not in feriados_datas: dias_trabalhados += 1; horas_trabalhadas += r_obj.horas_trabalhadas
        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        return {'dias_uteis': dias_uteis_potenciais, 'dias_trabalhados': dias_trabalhados, 'dias_afastamento': dias_afastamento, 'horas_trabalhadas': horas_trabalhadas, 'carga_horaria_devida': carga_horaria_devida, 'saldo_horas': saldo_horas}
    except Exception as e: current_app.logger.error(f"Erro ao calcular estatísticas: {e}"); return {'dias_uteis': 0, 'dias_trabalhados': 0, 'dias_afastamento': 0, 'horas_trabalhadas': 0, 'carga_horaria_devida': 0, 'saldo_horas': 0}

# --- generate_pdf ATUALIZADA ---
def generate_pdf(user_id, mes, ano, context_completo=None):
    """
    Gera um arquivo PDF com o relatório mensal de ponto.
    Aceita um contexto completo opcional para incluir dados de autoavaliação.
    """
    try:
        context = {}
        if context_completo:
            # Usa o contexto fornecido (que já inclui dados base + autoavaliação)
            context = context_completo
            # Garante que 'usuario' está no contexto, caso contrário busca
            if 'usuario' not in context or not context['usuario']:
                 usuario = User.query.get(user_id)
                 if not usuario: raise ValueError(f"Usuário ID {user_id} não encontrado.")
                 context['usuario'] = usuario
            usuario = context['usuario'] # Pega o usuário do contexto
        else:
            # Busca os dados padrão se nenhum contexto completo foi fornecido
            dados_base = _get_relatorio_mensal_data(user_id, mes, ano)
            usuario = dados_base['usuario'] # Pega o usuário dos dados base
            # Monta o contexto padrão
            context = {
                **dados_base, # Desempacota todos os dados base
                'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'titulo': f'Relatório de Ponto - {dados_base["nome_mes"]}/{ano}'
                # Não inclui chaves de autoavaliação aqui
            }

        # Define o caminho do arquivo de saída
        static_dir = os.path.join(current_app.root_path, 'static')
        exports_dir = os.path.join(static_dir, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        filename = f"relatorio_{'completo_' if context_completo else ''}{usuario.matricula}_{mes}_{ano}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        output_path = os.path.join(exports_dir, filename)

        # Cria o PDF usando o contexto montado
        success = create_pdf('exports/relatorio_ponto_pdf.html', output_path, **context)

        if success:
            return f"exports/{filename}" # Retorna caminho relativo
        else:
            raise Exception("Falha ao gerar PDF via create_pdf")
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF para user {user_id}, {mes}/{ano}: {e}", exc_info=True)
        return None
# --- Fim da Atualização ---

# Função generate_excel (mantida)
def generate_excel(user_id, mes, ano):
    # ... (código mantido) ...
    try:
        usuario = User.query.get(user_id);
        if not usuario: raise ValueError(f"Usuário ID {user_id} não encontrado")
        primeiro_dia = date(ano, mes, 1); ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        registros = Ponto.query.filter(Ponto.user_id == user_id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data).all()
        headers = {'data': 'Data', 'dia_semana': 'Dia da Semana', 'entrada': 'Entrada', 'saida_almoco': 'Saída Almoço', 'retorno_almoco': 'Retorno Almoço', 'saida': 'Saída', 'horas_trabalhadas': 'Horas Trabalhadas', 'afastamento': 'Afastamento', 'tipo_afastamento': 'Tipo Afastamento', 'observacoes': 'Observações', 'resultados_produtos': 'Resultados/Produtos', 'atividades': 'Atividades'}
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        data_excel = []
        for registro in registros:
            atividades = Atividade.query.filter_by(ponto_id=registro.id).all()
            atividades_texto = "; ".join([a.descricao for a in atividades]) if atividades else ""
            row = {'data': registro.data.strftime('%d/%m/%Y') if registro.data else '', 'dia_semana': dias_semana[registro.data.weekday()] if registro.data else '', 'entrada': registro.entrada.strftime('%H:%M') if registro.entrada else '', 'saida_almoco': registro.saida_almoco.strftime('%H:%M') if registro.saida_almoco else '', 'retorno_almoco': registro.retorno_almoco.strftime('%H:%M') if registro.retorno_almoco else '', 'saida': registro.saida.strftime('%H:%M') if registro.saida else '', 'horas_trabalhadas': registro.horas_trabalhadas if registro.horas_trabalhadas is not None else '', 'afastamento': 'Sim' if registro.afastamento else 'Não', 'tipo_afastamento': registro.tipo_afastamento if registro.tipo_afastamento else '', 'observacoes': registro.observacoes if registro.observacoes else '', 'resultados_produtos': registro.resultados_produtos if registro.resultados_produtos else '', 'atividades': atividades_texto}
            data_excel.append(row)
        static_dir = os.path.join(current_app.root_path, 'static'); exports_dir = os.path.join(static_dir, 'exports'); os.makedirs(exports_dir, exist_ok=True)
        filename = f"relatorio_{usuario.matricula}_{mes}_{ano}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"; output_path = os.path.join(exports_dir, filename)
        success = create_excel(data_excel, headers, output_path)
        if success: return f"exports/{filename}"
        else: raise Exception("Falha ao gerar Excel")
    except Exception as e: current_app.logger.error(f"Erro ao gerar Excel: {e}", exc_info=True); return None

# Aliases antigos (podem ser removidos se não usados em outros lugares)
export_registros_pdf = generate_pdf
export_registros_excel = generate_excel
