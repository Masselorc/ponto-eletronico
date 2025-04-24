import os
from datetime import datetime, date
from flask import render_template, current_app
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from io import BytesIO
from app.models.ponto import Ponto, Feriado, Atividade
from app.models.user import User
from calendar import monthrange

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
    try:
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
    except Exception as e:
        current_app.logger.error(f"Erro ao criar PDF: {e}")
        return False

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

def calcular_estatisticas_mes(user_id, mes, ano):
    """
    Calcula estatísticas do mês para um usuário
    
    Args:
        user_id: ID do usuário
        mes: Número do mês
        ano: Ano
    
    Returns:
        dict: Dicionário com estatísticas do mês
    """
    try:
        # Obtém o primeiro e último dia do mês
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        
        # Obtém os registros de ponto do mês para o usuário
        registros = Ponto.query.filter(
            Ponto.user_id == user_id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all()
        
        # Obtém os feriados do mês
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        
        # Cria um conjunto de datas de feriados para fácil verificação
        feriados_datas = {feriado.data for feriado in feriados}
        
        # Calcula estatísticas
        dias_uteis = 0
        dias_trabalhados = 0
        dias_afastamento = 0
        horas_trabalhadas = 0
        
        # Itera pelos dias do mês
        for dia in range(1, ultimo_dia.day + 1):
            data_atual = date(ano, mes, dia)
            
            # Verifica se é dia útil (segunda a sexta e não é feriado)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis += 1
                
                # Verifica se há registro para este dia
                registro = next((r for r in registros if r.data == data_atual), None)
                if registro:
                    if registro.afastamento:
                        # Se for um dia de afastamento
                        dias_afastamento += 1
                    elif registro.horas_trabalhadas:
                        # Se tiver horas trabalhadas registradas
                        dias_trabalhados += 1
                        horas_trabalhadas += registro.horas_trabalhadas
        
        # Calcula a carga horária devida (8h por dia útil, excluindo dias de afastamento)
        carga_horaria_devida = 8 * (dias_uteis - dias_afastamento)
        
        # Calcula o saldo de horas
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        
        return {
            'dias_uteis': dias_uteis,
            'dias_trabalhados': dias_trabalhados,
            'dias_afastamento': dias_afastamento,
            'horas_trabalhadas': horas_trabalhadas,
            'carga_horaria_devida': carga_horaria_devida,
            'saldo_horas': saldo_horas
        }
    except Exception as e:
        current_app.logger.error(f"Erro ao calcular estatísticas: {e}")
        return {
            'dias_uteis': 0,
            'dias_trabalhados': 0,
            'dias_afastamento': 0,
            'horas_trabalhadas': 0,
            'carga_horaria_devida': 0,
            'saldo_horas': 0
        }

def generate_pdf(user_id, mes, ano):
    """
    Gera um arquivo PDF com o relatório mensal de ponto
    
    Args:
        user_id: ID do usuário
        mes: Número do mês
        ano: Ano
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    try:
        # Obtém o usuário
        usuario = User.query.get(user_id)
        if not usuario:
            raise ValueError(f"Usuário com ID {user_id} não encontrado")
        
        # Obtém o primeiro e último dia do mês
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        
        # Obtém os registros de ponto do mês para o usuário
        registros = Ponto.query.filter(
            Ponto.user_id == user_id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all()
        
        # Obtém as atividades para cada registro
        for registro in registros:
            registro.atividades_lista = Atividade.query.filter_by(ponto_id=registro.id).all()
        
        # Calcula estatísticas do mês
        estatisticas = calcular_estatisticas_mes(user_id, mes, ano)
        
        # Nomes dos meses em português
        nomes_meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        nome_mes = nomes_meses[mes - 1]
        
        # Define o caminho do arquivo de saída
        static_dir = os.path.join(current_app.root_path, 'static')
        exports_dir = os.path.join(static_dir, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        filename = f"relatorio_{usuario.matricula}_{mes}_{ano}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        output_path = os.path.join(exports_dir, filename)
        
        # Prepara o contexto para o template
        context = {
            'registros': registros,
            'usuario': usuario,
            'mes': mes,
            'ano': ano,
            'nome_mes': nome_mes,
            'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'titulo': f'Relatório de Ponto - {nome_mes}/{ano}',
            'dias_uteis': estatisticas['dias_uteis'],
            'dias_trabalhados': estatisticas['dias_trabalhados'],
            'dias_afastamento': estatisticas['dias_afastamento'],
            'horas_trabalhadas': estatisticas['horas_trabalhadas'],
            'carga_horaria_devida': estatisticas['carga_horaria_devida'],
            'saldo_horas': estatisticas['saldo_horas']
        }
        
        # Cria o PDF
        success = create_pdf('exports/relatorio_ponto_pdf.html', output_path, **context)
        
        if success:
            return f"exports/{filename}"
        else:
            raise Exception("Falha ao gerar PDF")
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF: {e}")
        return None

def generate_excel(user_id, mes, ano):
    """
    Gera um arquivo Excel com o relatório mensal de ponto
    
    Args:
        user_id: ID do usuário
        mes: Número do mês
        ano: Ano
    
    Returns:
        str: Caminho do arquivo Excel gerado
    """
    try:
        # Obtém o usuário
        usuario = User.query.get(user_id)
        if not usuario:
            raise ValueError(f"Usuário com ID {user_id} não encontrado")
        
        # Obtém o primeiro e último dia do mês
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        
        # Obtém os registros de ponto do mês para o usuário
        registros = Ponto.query.filter(
            Ponto.user_id == user_id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all()
        
        # Define os cabeçalhos das colunas
        headers = {
            'data': 'Data',
            'dia_semana': 'Dia da Semana',
            'entrada': 'Entrada',
            'saida_almoco': 'Saída Almoço',
            'retorno_almoco': 'Retorno Almoço',
            'saida': 'Saída',
            'horas_trabalhadas': 'Horas Trabalhadas',
            'afastamento': 'Afastamento',
            'tipo_afastamento': 'Tipo Afastamento',
            'observacoes': 'Observações',
            'atividades': 'Atividades'
        }
        
        # Dias da semana em português
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        # Prepara os dados para o Excel
        data = []
        for registro in registros:
            # Obtém as atividades para este registro
            atividades = Atividade.query.filter_by(ponto_id=registro.id).all()
            atividades_texto = "; ".join([a.descricao for a in atividades]) if atividades else ""
            
            row = {
                'data': registro.data.strftime('%d/%m/%Y') if registro.data else '',
                'dia_semana': dias_semana[registro.data.weekday()] if registro.data else '',
                'entrada': registro.entrada.strftime('%H:%M') if registro.entrada else '',
                'saida_almoco': registro.saida_almoco.strftime('%H:%M') if registro.saida_almoco else '',
                'retorno_almoco': registro.retorno_almoco.strftime('%H:%M') if registro.retorno_almoco else '',
                'saida': registro.saida.strftime('%H:%M') if registro.saida else '',
                'horas_trabalhadas': registro.horas_trabalhadas if registro.horas_trabalhadas else 0,
                'afastamento': 'Sim' if registro.afastamento else 'Não',
                'tipo_afastamento': registro.tipo_afastamento if registro.tipo_afastamento else '',
                'observacoes': registro.observacoes if registro.observacoes else '',
                'atividades': atividades_texto
            }
            data.append(row)
        
        # Define o caminho do arquivo de saída
        static_dir = os.path.join(current_app.root_path, 'static')
        exports_dir = os.path.join(static_dir, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        filename = f"relatorio_{usuario.matricula}_{mes}_{ano}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        output_path = os.path.join(exports_dir, filename)
        
        # Cria o Excel
        success = create_excel(data, headers, output_path)
        
        if success:
            return f"exports/{filename}"
        else:
            raise Exception("Falha ao gerar Excel")
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar Excel: {e}")
        return None

# Funções de compatibilidade para manter a API existente
def export_registros_pdf(registros, usuario, mes, ano, output_path):
    """
    Função de compatibilidade para manter a API existente
    Exporta registros de ponto para PDF com visual gráfico
    """
    try:
        # Obtém as atividades para cada registro
        for registro in registros:
            registro.atividades_lista = Atividade.query.filter_by(ponto_id=registro.id).all()
        
        # Calcula estatísticas do mês
        estatisticas = calcular_estatisticas_mes(usuario.id, mes, ano)
        
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
            'titulo': f'Relatório de Ponto - {nome_mes}/{ano}',
            'dias_uteis': estatisticas['dias_uteis'],
            'dias_trabalhados': estatisticas['dias_trabalhados'],
            'dias_afastamento': estatisticas['dias_afastamento'],
            'horas_trabalhadas': estatisticas['horas_trabalhadas'],
            'carga_horaria_devida': estatisticas['carga_horaria_devida'],
            'saldo_horas': estatisticas['saldo_horas']
        }
        
        # Cria o PDF
        return create_pdf('exports/relatorio_ponto_pdf.html', output_path, **context)
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar PDF: {e}")
        return False

def export_registros_excel(registros, usuario, mes, ano, output_path):
    """
    Função de compatibilidade para manter a API existente
    Exporta registros de ponto para Excel com dados brutos
    """
    try:
        # Define os cabeçalhos das colunas
        headers = {
            'data': 'Data',
            'dia_semana': 'Dia da Semana',
            'entrada': 'Entrada',
            'saida_almoco': 'Saída Almoço',
            'retorno_almoco': 'Retorno Almoço',
            'saida': 'Saída',
            'horas_trabalhadas': 'Horas Trabalhadas',
            'afastamento': 'Afastamento',
            'tipo_afastamento': 'Tipo Afastamento',
            'observacoes': 'Observações',
            'atividades': 'Atividades'
        }
        
        # Dias da semana em português
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        # Prepara os dados para o Excel
        data = []
        for registro in registros:
            # Obtém as atividades para este registro
            atividades = Atividade.query.filter_by(ponto_id=registro.id).all()
            atividades_texto = "; ".join([a.descricao for a in atividades]) if atividades else ""
            
            row = {
                'data': registro.data.strftime('%d/%m/%Y') if registro.data else '',
                'dia_semana': dias_semana[registro.data.weekday()] if registro.data else '',
                'entrada': registro.entrada.strftime('%H:%M') if registro.entrada else '',
                'saida_almoco': registro.saida_almoco.strftime('%H:%M') if registro.saida_almoco else '',
                'retorno_almoco': registro.retorno_almoco.strftime('%H:%M') if registro.retorno_almoco else '',
                'saida': registro.saida.strftime('%H:%M') if registro.saida else '',
                'horas_trabalhadas': registro.horas_trabalhadas if registro.horas_trabalhadas else 0,
                'afastamento': 'Sim' if registro.afastamento else 'Não',
                'tipo_afastamento': registro.tipo_afastamento if registro.tipo_afastamento else '',
                'observacoes': registro.observacoes if registro.observacoes else '',
                'atividades': atividades_texto
            }
            data.append(row)
        
        # Cria o Excel
        return create_excel(data, headers, output_path)
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar Excel: {e}")
        return False
