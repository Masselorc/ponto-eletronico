from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from app import db
from app.forms.admin import UserForm, FeriadoForm
from app.forms.ponto import RegistroPontoForm, AtividadeForm
from datetime import datetime, date, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.before_request
def check_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('main.dashboard'))

@admin.route('/')
@login_required
def index():
    return render_template('admin/index.html')

@admin.route('/usuarios')
@login_required
def listar_usuarios():
    usuarios = User.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin.route('/usuario/visualizar/<int:user_id>')
@login_required
def visualizar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês atual
    hoje = datetime.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    if mes_atual == 12:
        ultimo_dia = date(ano_atual + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano_atual, mes_atual + 1, 1) - timedelta(days=1)
    
    # Obtém todos os registros do mês atual
    registros_mes = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Obtém o total de registros
    total_registros = Ponto.query.filter_by(user_id=user_id).count()
    
    # Calcula as horas trabalhadas no mês
    horas_mes = sum(registro.horas_trabalhadas or 0 for registro in registros_mes)
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Calcula o saldo de horas do mês
    dias_uteis = 0
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano_atual, mes_atual, dia)
        if data.weekday() < 5 and data not in feriados_datas:  # 0-4 são dias de semana (seg-sex)
            dias_uteis += 1
    
    horas_esperadas = dias_uteis * 8  # 8 horas por dia útil
    saldo_horas = horas_mes - horas_esperadas
    
    # Obtém os últimos 5 registros
    ultimos_registros = Ponto.query.filter_by(user_id=user_id).order_by(Ponto.data.desc()).limit(5).all()
    
    return render_template('admin/visualizar_usuario.html', 
                          user=user,
                          total_registros=total_registros,
                          horas_mes=horas_mes,
                          saldo_horas=saldo_horas,
                          ultimos_registros=ultimos_registros)

@admin.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            matricula=form.matricula.data,
            cargo=form.cargo.data,
            uf=form.uf.data,
            telefone=form.telefone.data,
            vinculo=form.vinculo.data,
            is_admin=form.is_admin.data
        )
        
        # Processar foto se enviada
        if form.foto.data:
            # Lógica para salvar a foto será implementada aqui
            pass
            
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/form_usuario.html', form=form, title='Novo Usuário')

@admin.route('/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.matricula = form.matricula.data
        user.cargo = form.cargo.data
        user.uf = form.uf.data
        user.telefone = form.telefone.data
        user.vinculo = form.vinculo.data
        user.is_admin = form.is_admin.data
        
        # Processar foto se enviada
        if form.foto.data:
            # Lógica para salvar a foto será implementada aqui
            pass
            
        if form.password.data:
            user.set_password(form.password.data)
            
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/form_usuario.html', form=form, title='Editar Usuário')

@admin.route('/usuario/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário!', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_usuarios'))

@admin.route('/feriados')
@login_required
def listar_feriados():
    feriados = Feriado.query.order_by(Feriado.data).all()
    return render_template('admin/feriados.html', feriados=feriados)

@admin.route('/feriado/novo', methods=['GET', 'POST'])
@login_required
def novo_feriado():
    form = FeriadoForm()
    if form.validate_on_submit():
        feriado = Feriado(
            data=form.data.data,
            descricao=form.descricao.data
        )
        db.session.add(feriado)
        db.session.commit()
        flash('Feriado registrado com sucesso!', 'success')
        return redirect(url_for('admin.listar_feriados'))
    
    return render_template('admin/form_feriado.html', form=form, title='Novo Feriado')

@admin.route('/feriado/excluir/<int:feriado_id>', methods=['POST'])
@login_required
def excluir_feriado(feriado_id):
    feriado = Feriado.query.get_or_404(feriado_id)
    db.session.delete(feriado)
    db.session.commit()
    flash('Feriado excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_feriados'))

@admin.route('/relatorios')
@login_required
def relatorios():
    # Busca todos os usuários, incluindo administradores
    usuarios = User.query.all()
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/relatorio/<int:user_id>')
@login_required
def relatorio_usuario(user_id):
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano da URL ou usa o mês atual
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Obtém todos os registros do mês selecionado
    primeiro_dia = datetime(ano, mes, 1).date()
    if mes == 12:
        ultimo_dia = datetime(ano + 1, 1, 1).date()
    else:
        ultimo_dia = datetime(ano, mes + 1, 1).date()
    
    registros = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data < ultimo_dia
    ).order_by(Ponto.data).all()
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data < ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Calcula o saldo de horas do mês
    dias_uteis = 0
    for dia in range(1, ultimo_dia.day if mes != 12 else 32):
        data = datetime(ano, mes, dia).date()
        if data.month != mes:  # Para meses com menos de 31 dias
            break
        if data.weekday() < 5 and data not in feriados_datas:  # 0-4 são dias de semana (seg-sex)
            dias_uteis += 1
    
    horas_esperadas = dias_uteis * 8  # 8 horas por dia útil
    horas_trabalhadas = sum(registro.horas_trabalhadas or 0 for registro in registros)
    saldo_horas = horas_trabalhadas - horas_esperadas
    
    return render_template('admin/relatorio_usuario.html', 
                          user=user,
                          registros=registros,
                          mes=mes,
                          ano=ano,
                          horas_esperadas=horas_esperadas,
                          horas_trabalhadas=horas_trabalhadas,
                          saldo_horas=saldo_horas)

@admin.route('/ponto/editar/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    if request.method == 'POST':
        entrada = request.form.get('entrada')
        saida_almoco = request.form.get('saida_almoco')
        retorno_almoco = request.form.get('retorno_almoco')
        saida = request.form.get('saida')
        
        # Converte strings para objetos time
        if entrada:
            ponto.entrada = datetime.strptime(entrada, '%H:%M').time()
        if saida_almoco:
            ponto.saida_almoco = datetime.strptime(saida_almoco, '%H:%M').time()
        if retorno_almoco:
            ponto.retorno_almoco = datetime.strptime(retorno_almoco, '%H:%M').time()
        if saida:
            ponto.saida = datetime.strptime(saida, '%H:%M').time()
        
        # Recalcula horas trabalhadas
        if ponto.entrada and ponto.saida_almoco and ponto.retorno_almoco and ponto.saida:
            # Tempo antes do almoço
            t1 = datetime.combine(ponto.data, ponto.saida_almoco) - datetime.combine(ponto.data, ponto.entrada)
            
            # Tempo depois do almoço
            t2 = datetime.combine(ponto.data, ponto.saida) - datetime.combine(ponto.data, ponto.retorno_almoco)
            
            # Total de horas trabalhadas
            total_segundos = t1.total_seconds() + t2.total_seconds()
            ponto.horas_trabalhadas = total_segundos / 3600  # Converte para horas
        
        db.session.commit()
        flash('Registro de ponto atualizado com sucesso!', 'success')
        return redirect(url_for('admin.relatorio_usuario', user_id=ponto.user_id))
    
    return render_template('admin/editar_ponto.html', ponto=ponto)

@admin.route('/ponto/novo/<int:user_id>', methods=['GET', 'POST'])
@login_required
def novo_ponto(user_id):
    user = User.query.get_or_404(user_id)
    form = RegistroPontoForm()
    
    if form.validate_on_submit():
        data_selecionada = form.data.data
        hora_selecionada = form.hora.data
        tipo = form.tipo.data
        
        # Verifica se já existe registro para a data selecionada
        registro = Ponto.query.filter_by(
            user_id=user_id,
            data=data_selecionada
        ).first()
        
        if not registro:
            registro = Ponto(user_id=user_id, data=data_selecionada)
        
        # Usa a hora selecionada pelo usuário
        if tipo == 'entrada':
            registro.entrada = hora_selecionada
        elif tipo == 'saida_almoco':
            registro.saida_almoco = hora_selecionada
        elif tipo == 'retorno_almoco':
            registro.retorno_almoco = hora_selecionada
        elif tipo == 'saida':
            registro.saida = hora_selecionada
            
        # Calcula horas trabalhadas se tiver todos os registros
        if (registro.entrada and registro.saida_almoco and 
            registro.retorno_almoco and registro.saida):
            
            # Tempo antes do almoço
            t1 = datetime.combine(data_selecionada, registro.saida_almoco) - datetime.combine(data_selecionada, registro.entrada)
            
            # Tempo depois do almoço
            t2 = datetime.combine(data_selecionada, registro.saida) - datetime.combine(data_selecionada, registro.retorno_almoco)
            
            # Total de horas trabalhadas
            total_segundos = t1.total_seconds() + t2.total_seconds()
            registro.horas_trabalhadas = total_segundos / 3600  # Converte para horas
        
        if not registro.id:
            db.session.add(registro)
        
        db.session.commit()
        flash(f'Registro de {tipo} adicionado com sucesso para o usuário {user.name}!', 'success')
        return redirect(url_for('admin.relatorio_usuario', user_id=user_id))
    
    return render_template('admin/novo_ponto.html', form=form, user=user)

@admin.route('/ponto/excluir/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    user_id = ponto.user_id
    
    db.session.delete(ponto)
    db.session.commit()
    flash('Registro de ponto excluído com sucesso!', 'success')
    return redirect(url_for('admin.relatorio_usuario', user_id=user_id))

@admin.route('/atividade/nova/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def nova_atividade(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    form = AtividadeForm()
    
    if form.validate_on_submit():
        atividade = Atividade(
            ponto_id=ponto_id,
            descricao=form.descricao.data
        )
        db.session.add(atividade)
        db.session.commit()
        flash('Atividade registrada com sucesso!', 'success')
        return redirect(url_for('admin.relatorio_usuario', user_id=ponto.user_id))
    
    return render_template('admin/nova_atividade.html', form=form, ponto=ponto)

@admin.route('/atividade/excluir/<int:atividade_id>', methods=['POST'])
@login_required
def excluir_atividade(atividade_id):
    atividade = Atividade.query.get_or_404(atividade_id)
    ponto = Ponto.query.get(atividade.ponto_id)
    user_id = ponto.user_id
    
    db.session.delete(atividade)
    db.session.commit()
    flash('Atividade excluída com sucesso!', 'success')
    return redirect(url_for('admin.relatorio_usuario', user_id=user_id))

@admin.route('/relatorio/<int:user_id>/pdf')
@login_required
def relatorio_usuario_pdf(user_id):
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano da URL ou usa o mês atual
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Obtém todos os registros do mês selecionado
    primeiro_dia = datetime(ano, mes, 1).date()
    if mes == 12:
        ultimo_dia = datetime(ano + 1, 1, 1).date()
    else:
        ultimo_dia = datetime(ano, mes + 1, 1).date()
    
    registros = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data < ultimo_dia
    ).order_by(Ponto.data).all()
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data < ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Calcula o saldo de horas do mês
    dias_uteis = 0
    for dia in range(1, ultimo_dia.day if mes != 12 else 32):
        data = datetime(ano, mes, dia).date()
        if data.month != mes:  # Para meses com menos de 31 dias
            break
        if data.weekday() < 5 and data not in feriados_datas:  # 0-4 são dias de semana (seg-sex)
            dias_uteis += 1
    
    horas_esperadas = dias_uteis * 8  # 8 horas por dia útil
    horas_trabalhadas = sum(registro.horas_trabalhadas or 0 for registro in registros)
    saldo_horas = horas_trabalhadas - horas_esperadas
    
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes - 1]
    
    # Criar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Título
    elements.append(Paragraph(f"Relatório de Banco de Horas", title_style))
    elements.append(Paragraph(f"Funcionário: {user.name} ({user.matricula})", subtitle_style))
    elements.append(Paragraph(f"Período: {nome_mes} de {ano}", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Resumo
    elements.append(Paragraph("Resumo do Banco de Horas", subtitle_style))
    resumo_data = [
        ["Horas Esperadas", "Horas Trabalhadas", "Saldo de Horas"],
        [f"{horas_esperadas:.1f}h", f"{horas_trabalhadas:.1f}h", f"{saldo_horas:.1f}h"]
    ]
    resumo_table = Table(resumo_data, colWidths=[150, 150, 150])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(resumo_table)
    elements.append(Spacer(1, 20))
    
    # Registros Detalhados
    elements.append(Paragraph("Registros Detalhados", subtitle_style))
    
    if registros:
        registros_data = [
            ["Data", "Entrada", "Saída Almoço", "Retorno Almoço", "Saída", "Horas"]
        ]
        
        for registro in registros:
            data_formatada = registro.data.strftime('%d/%m/%Y')
            entrada = registro.entrada.strftime('%H:%M') if registro.entrada else '--:--'
            saida_almoco = registro.saida_almoco.strftime('%H:%M') if registro.saida_almoco else '--:--'
            retorno_almoco = registro.retorno_almoco.strftime('%H:%M') if registro.retorno_almoco else '--:--'
            saida = registro.saida.strftime('%H:%M') if registro.saida else '--:--'
            
            if registro.afastamento:
                horas = "Afastamento"
            elif registro.horas_trabalhadas:
                horas = f"{registro.horas_trabalhadas:.1f}h"
            else:
                horas = "Pendente"
                
            registros_data.append([
                data_formatada, entrada, saida_almoco, retorno_almoco, saida, horas
            ])
        
        registros_table = Table(registros_data, colWidths=[70, 70, 90, 90, 70, 60])
        registros_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(registros_table)
    else:
        elements.append(Paragraph("Nenhum registro encontrado para o período selecionado.", normal_style))
    
    # Gerar PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    # Criar resposta
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{user.matricula}_{mes}_{ano}.pdf'
    
    return response
