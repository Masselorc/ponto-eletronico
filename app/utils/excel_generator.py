from io import BytesIO
import xlsxwriter

def generate_excel_report(user, registros, mes, ano, horas_esperadas, horas_trabalhadas, saldo_horas):
    """
    Gera um relatório Excel com os dados do banco de horas do usuário.
    
    Args:
        user: Objeto do usuário
        registros: Lista de registros de ponto
        mes: Número do mês (1-12)
        ano: Ano
        horas_esperadas: Total de horas esperadas no mês
        horas_trabalhadas: Total de horas trabalhadas no mês
        saldo_horas: Saldo de horas (trabalhadas - esperadas)
        
    Returns:
        BytesIO: Buffer contendo o arquivo Excel
    """
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes - 1]
    
    # Criar buffer para o arquivo Excel
    output = BytesIO()
    
    # Criar workbook e worksheet
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Relatório')
    
    # Definir formatos
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    subtitle_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4B8BF5',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    date_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': 'dd/mm/yyyy'
    })
    
    time_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': 'hh:mm'
    })
    
    number_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0.0'
    })
    
    positive_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0.0',
        'font_color': 'green',
        'bold': True
    })
    
    negative_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0.0',
        'font_color': 'red',
        'bold': True
    })
    
    # Ajustar largura das colunas
    worksheet.set_column('A:A', 15)  # Data
    worksheet.set_column('B:E', 12)  # Horários
    worksheet.set_column('F:F', 15)  # Horas trabalhadas
    
    # Título e subtítulo
    worksheet.merge_range('A1:F1', 'Relatório de Banco de Horas', title_format)
    worksheet.merge_range('A2:F2', f'Funcionário: {user.name} ({user.matricula})', subtitle_format)
    worksheet.merge_range('A3:F3', f'Período: {nome_mes} de {ano}', subtitle_format)
    
    # Resumo
    worksheet.merge_range('A5:F5', 'Resumo do Banco de Horas', subtitle_format)
    
    worksheet.write('A6', 'Horas Esperadas', header_format)
    worksheet.write('B6', 'Horas Trabalhadas', header_format)
    worksheet.write('C6', 'Saldo de Horas', header_format)
    
    worksheet.write('A7', horas_esperadas, number_format)
    worksheet.write('B7', horas_trabalhadas, number_format)
    
    # Usar formato diferente dependendo se o saldo é positivo ou negativo
    if saldo_horas >= 0:
        worksheet.write('C7', saldo_horas, positive_format)
    else:
        worksheet.write('C7', saldo_horas, negative_format)
    
    # Registros detalhados
    worksheet.merge_range('A9:F9', 'Registros Detalhados', subtitle_format)
    
    # Cabeçalhos
    worksheet.write('A10', 'Data', header_format)
    worksheet.write('B10', 'Entrada', header_format)
    worksheet.write('C10', 'Saída Almoço', header_format)
    worksheet.write('D10', 'Retorno Almoço', header_format)
    worksheet.write('E10', 'Saída', header_format)
    worksheet.write('F10', 'Horas', header_format)
    
    # Dados
    row = 10
    for registro in registros:
        row += 1
        
        # Converter data para formato Excel
        worksheet.write(row, 0, registro.data, date_format)
        
        # Horários
        if registro.entrada:
            worksheet.write_datetime(row, 1, registro.entrada, time_format)
        else:
            worksheet.write(row, 1, '--:--', cell_format)
            
        if registro.saida_almoco:
            worksheet.write_datetime(row, 2, registro.saida_almoco, time_format)
        else:
            worksheet.write(row, 2, '--:--', cell_format)
            
        if registro.retorno_almoco:
            worksheet.write_datetime(row, 3, registro.retorno_almoco, time_format)
        else:
            worksheet.write(row, 3, '--:--', cell_format)
            
        if registro.saida:
            worksheet.write_datetime(row, 4, registro.saida, time_format)
        else:
            worksheet.write(row, 4, '--:--', cell_format)
        
        # Horas trabalhadas
        if registro.afastamento:
            worksheet.write(row, 5, 'Afastamento', cell_format)
        elif registro.horas_trabalhadas:
            worksheet.write(row, 5, registro.horas_trabalhadas, number_format)
        else:
            worksheet.write(row, 5, 'Pendente', cell_format)
    
    # Fechar workbook
    workbook.close()
    
    # Retornar ao início do buffer
    output.seek(0)
    
    return output
