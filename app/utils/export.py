# -*- coding: utf-8 -*-
"""
Utilitários para Exportação de Dados.

Este módulo contém funções para gerar arquivos em diferentes formatos (PDF, Excel)
a partir dos dados da aplicação, como relatórios de ponto.

Funções:
    - gerar_relatorio_pdf_bytes: Gera um relatório PDF a partir de conteúdo HTML.
    - gerar_relatorio_excel_bytes: Gera um relatório Excel (XLSX) a partir de dados.
"""

import logging
from io import BytesIO

# Para PDF
from xhtml2pdf import pisa

# Para Excel (usando openpyxl como exemplo, pode ser XlsxWriter também)
# Certifique-se de ter openpyxl instalado: pip install openpyxl
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.utils.helpers import formatar_timedelta # Importar helper de formatação

logger = logging.getLogger(__name__)

def gerar_relatorio_pdf_bytes(html_content):
    """
    Converte conteúdo HTML em bytes de um arquivo PDF.

    Args:
        html_content (str): String contendo o HTML a ser renderizado em PDF.

    Returns:
        BytesIO or None: Objeto BytesIO contendo os dados do PDF gerado,
                         ou None se ocorrer um erro.
    """
    pdf_result = BytesIO()
    try:
        # Tenta converter o HTML para PDF
        pisa_status = pisa.CreatePDF(
            BytesIO(html_content.encode('UTF-8')), # Fonte HTML como bytes UTF-8
            dest=pdf_result,
            encoding='UTF-8' # Garante a codificação correta
        )

        if pisa_status.err:
            logger.error(f"Erro ao gerar PDF com xhtml2pdf: {pisa_status.err}")
            return None
        else:
            pdf_result.seek(0) # Volta ao início do stream de bytes
            logger.info("Relatório PDF gerado com sucesso.")
            return pdf_result.getvalue() # Retorna os bytes diretamente

    except Exception as e:
        logger.error(f"Exceção inesperada ao gerar PDF: {e}", exc_info=True)
        return None

# CORREÇÃO: Adicionando a função gerar_relatorio_excel_bytes
def gerar_relatorio_excel_bytes(dados_relatorio):
    """
    Gera um relatório de ponto em formato Excel (XLSX) a partir dos dados fornecidos.

    Args:
        dados_relatorio (dict): Dicionário contendo os dados para o relatório.
                                Espera chaves como 'usuario', 'ano', 'mes', 'nome_mes',
                                'relatorio_dias', 'saldo_mes', 'saldo_total', 'jornada_diaria'.

    Returns:
        bytes or None: Bytes do arquivo XLSX gerado ou None em caso de erro.
    """
    try:
        logger.info(f"Iniciando geração de relatório Excel para {dados_relatorio.get('usuario', {}).get('username', 'N/A')} - {dados_relatorio.get('nome_mes', 'N/A')}/{dados_relatorio.get('ano', 'N/A')}")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Relatório {dados_relatorio.get('mes'):02d}-{dados_relatorio.get('ano')}"

        # --- Estilos ---
        header_font = Font(bold=True, size=12)
        center_alignment = Alignment(horizontal='center', vertical='center')
        left_alignment = Alignment(horizontal='left', vertical='center')
        right_alignment = Alignment(horizontal='right', vertical='center')
        thin_border = Border(left=Side(style='thin'),
                           right=Side(style='thin'),
                           top=Side(style='thin'),
                           bottom=Side(style='thin'))

        # --- Cabeçalho do Relatório ---
        ws.merge_cells('A1:G1')
        ws['A1'] = f"Relatório de Ponto - {dados_relatorio.get('nome_mes')} / {dados_relatorio.get('ano')}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = center_alignment

        ws.merge_cells('A2:G2')
        ws['A2'] = f"Funcionário: {dados_relatorio.get('usuario').nome_completo}" # Assumindo que User tem 'nome_completo'
        ws['A2'].font = header_font
        ws['A2'].alignment = center_alignment
        ws.row_dimensions[1].height = 20
        ws.row_dimensions[2].height = 18

        # --- Cabeçalhos da Tabela ---
        headers = ["Data", "Dia", "Entradas/Saídas", "Horas Trab.", "Saldo Dia", "Saldo Acum.", "Status/Obs."]
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_num, value=header)
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = thin_border
        ws.row_dimensions[4].height = 20

        # --- Preenchimento dos Dados ---
        row_num = 5
        for dia_info in dados_relatorio.get('relatorio_dias', []):
            data_str = dia_info['data'].strftime('%d/%m/%Y')
            dia_semana = dia_info['dia_semana']

            # Formata entradas/saídas
            pontos_str_list = []
            for ponto in dia_info.get('pontos', []):
                 tipo_ponto = ponto.tipo[0] if ponto.tipo else '?' # 'E' ou 'S'
                 hora_ponto = ponto.hora.strftime('%H:%M') if ponto.hora else '--:--'
                 obs_ponto = f" ({ponto.observacao})" if ponto.observacao else ""
                 pontos_str_list.append(f"{tipo_ponto}: {hora_ponto}{obs_ponto}")
            pontos_str = " | ".join(pontos_str_list) if pontos_str_list else "---"


            horas_trab_str = formatar_timedelta(dia_info['horas_trabalhadas'])
            saldo_dia_str = formatar_timedelta(dia_info['saldo_dia'], mostrar_sinal=True)
            saldo_acum_str = formatar_timedelta(dia_info['saldo_acumulado'], mostrar_sinal=True)
            status_obs = dia_info.get('status', '')
            if dia_info.get('comentarios'):
                if status_obs: status_obs += " | "
                status_obs += " / ".join(dia_info['comentarios'])

            data_row = [
                data_str,
                dia_semana,
                pontos_str,
                horas_trab_str,
                saldo_dia_str,
                saldo_acum_str,
                status_obs
            ]

            for col_num, value in enumerate(data_row, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                cell.border = thin_border
                # Alinhamentos específicos
                if col_num <= 2: # Data, Dia
                    cell.alignment = center_alignment
                elif col_num == 3 or col_num == 7: # Entradas/Saídas, Status
                    cell.alignment = left_alignment
                else: # Horas, Saldos
                    cell.alignment = right_alignment
            row_num += 1

        # --- Rodapé com Totais ---
        row_num += 1 # Linha em branco
        ws.cell(row=row_num, column=5, value="Saldo Final do Mês:").font = header_font
        ws.cell(row=row_num, column=6, value=formatar_timedelta(dados_relatorio.get('saldo_mes'), mostrar_sinal=True)).font = header_font
        ws.cell(row=row_num, column=5).alignment = right_alignment
        ws.cell(row=row_num, column=6).alignment = right_alignment

        row_num += 1
        ws.cell(row=row_num, column=5, value="Saldo Total Banco de Horas:").font = header_font
        ws.cell(row=row_num, column=6, value=formatar_timedelta(dados_relatorio.get('saldo_total'), mostrar_sinal=True)).font = header_font
        ws.cell(row=row_num, column=5).alignment = right_alignment
        ws.cell(row=row_num, column=6).alignment = right_alignment


        # --- Ajuste da Largura das Colunas ---
        column_widths = {'A': 12, 'B': 6, 'C': 40, 'D': 12, 'E': 12, 'F': 12, 'G': 40}
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width

        # --- Salvar em Bytes ---
        excel_bytes = BytesIO()
        wb.save(excel_bytes)
        excel_bytes.seek(0)
        logger.info("Relatório Excel gerado com sucesso.")
        return excel_bytes.getvalue()

    except Exception as e:
        logger.error(f"Erro ao gerar relatório Excel: {e}", exc_info=True)
        return None

# Nota: A função formatar_timedelta precisa estar definida em app.utils.helpers
# Exemplo básico de formatar_timedelta (coloque em helpers.py):
"""
import math
from datetime import timedelta

def formatar_timedelta(delta, mostrar_sinal=False):
    if delta is None:
        return "--:--"

    total_seconds = int(delta.total_seconds())
    sign = "-" if total_seconds < 0 else "+" if mostrar_sinal else ""
    total_seconds = abs(total_seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    return f"{sign}{hours:02d}:{minutes:02d}"
"""
