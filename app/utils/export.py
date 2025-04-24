import os
from datetime import datetime
from flask import render_template, current_app
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from io import BytesIO

def create_pdf(template_name, output_path, **context):
    """
    Cria um arquivo PDF a partir de um template HTML com estilos visuais preservados
    
    Args:
        template_name: Nome do template HTML
        output_path: Caminho onde o PDF será salvo
        context: Variáveis de contexto para o template
    
    Returns:
        bool: True se o PDF foi criado com sucesso, False caso contrário
    """
    # Renderiza o template HTML com o contexto fornecido
    html_content = render_template(template_name, **context)
    
    # Adiciona estilos CSS específicos para PDF
    pdf_styles = """
    <style>
        @page {
            size: letter portrait;
            margin: 1cm;
        }
        body {
            font-family: Arial, sans-serif;
            color: #333;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .header h1 {
            color: #0d6efd;
            margin: 0;
        }
        .header p {
            color: #6c757d;
            margin: 5px 0 0 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th {
            background-color: #0d6efd;
            color: white;
            font-weight: bold;
            text-align: left;
            padding: 8px;
        }
        td {
            border: 1px solid #ddd;
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .footer {
            text-align: center;
            font-size: 10px;
            margin-top: 30px;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }
        .card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #fff;
        }
        .card-header {
            background-color: #0d6efd;
            color: white;
            padding: 10px;
            margin: -15px -15px 15px -15px;
            border-radius: 5px 5px 0 0;
        }
        .card-body {
            padding: 0;
        }
        .badge {
            display: inline-block;
            padding: 3px 7px;
            font-size: 12px;
            font-weight: 700;
            border-radius: 10px;
        }
        .badge-success {
            background-color: #198754;
            color: white;
        }
        .badge-warning {
            background-color: #ffc107;
            color: #212529;
        }
        .badge-danger {
            background-color: #dc3545;
            color: white;
        }
        .badge-info {
            background-color: #0dcaf0;
            color: #212529;
        }
        .text-center {
            text-align: center;
        }
        .text-end {
            text-align: right;
        }
        .text-muted {
            color: #6c757d;
        }
    </style>
    """
    
    # Insere os estilos no HTML
    html_content = html_content.replace('</head>', f'{pdf_styles}</head>')
    
    # Cria o diretório de saída se não existir
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Converte HTML para PDF
    with open(output_path, "wb") as output_file:
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=output_file
        )
    
    # Retorna True se a conversão foi bem-sucedida
    return pisa_status.err == 0

def create_excel(data, headers, output_path):
    """
    Cria um arquivo Excel com dados brutos formatados como banco de dados
    
    Args:
        data: Lista de dicionários com os dados
        headers: Dicionário mapeando chaves de dados para títulos de colunas
        output_path: Caminho onde o Excel será salvo
    
    Returns:
        bool: True se o Excel foi criado com sucesso, False caso contrário
    """
    try:
        # Cria um novo workbook e seleciona a planilha ativa
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Dados"
        
        # Define estilos
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin"), 
            right=Side(style="thin"), 
            top=Side(style="thin"), 
            bottom=Side(style="thin")
        )
        
        # Adiciona cabeçalhos
        for col_idx, header_text in enumerate(headers.values(), 1):
            cell = ws.cell(row=1, column=col_idx, value=header_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Adiciona dados
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, key in enumerate(headers.keys(), 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(key, ""))
                cell.border = thin_border
        
        # Ajusta a largura das colunas
        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 15
        
        # Cria o diretório de saída se não existir
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Salva o arquivo
        wb.save(output_path)
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao criar arquivo Excel: {e}")
        return False

def export_registros_pdf(registros, usuario, mes, ano, output_path):
    """
    Exporta registros de ponto para PDF com visual gráfico
    
    Args:
        registros: Lista de registros de ponto
        usuario: Objeto do usuário
        mes: Número do mês
        ano: Ano
        output_path: Caminho onde o PDF será salvo
    
    Returns:
        bool: True se o PDF foi criado com sucesso, False caso contrário
    """
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes - 1]
    
    # Prepara o contexto para o template
    context = {
        'registros': registros,
        'usuario': usuario,
        'mes': mes,
        'ano': ano,
        'nome_mes': nome_mes,
        'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'titulo': f'Relatório de Ponto - {nome_mes}/{ano}'
    }
    
    # Cria o PDF
    return create_pdf('exports/relatorio_ponto_pdf.html', output_path, **context)

def export_registros_excel(registros, usuario, mes, ano, output_path):
    """
    Exporta registros de ponto para Excel com dados brutos
    
    Args:
        registros: Lista de registros de ponto
        usuario: Objeto do usuário
        mes: Número do mês
        ano: Ano
        output_path: Caminho onde o Excel será salvo
    
    Returns:
        bool: True se o Excel foi criado com sucesso, False caso contrário
    """
    # Define os cabeçalhos das colunas
    headers = {
        'data': 'Data',
        'entrada': 'Entrada',
        'saida_almoco': 'Saída Almoço',
        'retorno_almoco': 'Retorno Almoço',
        'saida': 'Saída',
        'horas_trabalhadas': 'Horas Trabalhadas',
        'afastamento': 'Afastamento',
        'tipo_afastamento': 'Tipo Afastamento',
        'observacoes': 'Observações'
    }
    
    # Prepara os dados para o Excel
    data = []
    for registro in registros:
        row = {
            'data': registro.data.strftime('%d/%m/%Y') if registro.data else '',
            'entrada': registro.entrada.strftime('%H:%M') if registro.entrada else '',
            'saida_almoco': registro.saida_almoco.strftime('%H:%M') if registro.saida_almoco else '',
            'retorno_almoco': registro.retorno_almoco.strftime('%H:%M') if registro.retorno_almoco else '',
            'saida': registro.saida.strftime('%H:%M') if registro.saida else '',
            'horas_trabalhadas': registro.horas_trabalhadas if registro.horas_trabalhadas else 0,
            'afastamento': 'Sim' if registro.afastamento else 'Não',
            'tipo_afastamento': registro.tipo_afastamento if registro.tipo_afastamento else '',
            'observacoes': registro.observacoes if registro.observacoes else ''
        }
        data.append(row)
    
    # Cria o Excel
    return create_excel(data, headers, output_path)
