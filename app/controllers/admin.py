from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app import db
from app.forms.admin import UserForm, FeriadoForm
from app.forms.ponto import RegistroPontoForm, AtividadeForm
from datetime import datetime, date, timedelta
from calendar import monthrange
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.utils.excel_generator import generate_excel_report
from app.utils.export import export_registros_pdf, export_registros_excel
import os
import logging

# Blueprint para área administrativa
admin = Blueprint('admin', __name__, url_prefix='/admin')

logger = logging.getLogger(__name__)

@admin.before_request
def check_admin():
    """Verifica se o usuário é administrador antes de acessar qualquer rota"""
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('main.dashboard'))

@admin.route('/')
@login_required
def index():
    """Página inicial da área administrativa"""
    return render_template('admin/index.html')

@admin.route('/usuarios')
@login_required
def listar_usuarios():
    """Lista todos os usuários cadastrados no sistema"""
    usuarios = User.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin.route('/usuario/visualizar/<int:user_id>')
@login_required
def visualizar_usuario(user_id):
    """Visualiza detalhes de um usuário específico"""
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
    """Cria um novo usuário"""
    form = UserForm()
    
    if form.validate_on_submit():
        # Verifica se já existe um usuário com este email
        if User.query.filter_by(email=form.email.data).first():
            flash('Email já cadastrado.', 'danger')
            return render_template('admin/novo_usuario.html', form=form)
        
        # Cria um novo usuário
        novo_user = User(
            name=form.name.data,
            email=form.email.data,
            is_admin=form.is_admin.data,
            is_active=form.is_active.data
        )
        
        # Define a senha
        novo_user.set_password(form.password.data)
        
        # Salva no banco de dados
        db.session.add(novo_user)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/novo_usuario.html', form=form)

@admin.route('/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    """Edita um usuário existente"""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    # Remove a validação de senha para edição
    form.password.validators = []
    form.password.flags.required = False
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso por outro usuário
        email_existente = User.query.filter_by(email=form.email.data).first()
        if email_existente and email_existente.id != user_id:
            flash('Email já cadastrado por outro usuário.', 'danger')
            return render_template('admin/editar_usuario.html', form=form, user=user)
        
        # Atualiza os dados do usuário
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
        # Atualiza a senha apenas se for fornecida
        if form.password.data:
            user.set_password(form.password.data)
        
        # Salva as alterações
        db.session.commit()
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/editar_usuario.html', form=form, user=user)

@admin.route('/usuario/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    """Exclui um usuário"""
    user = User.query.get_or_404(user_id)
    
    # Não permite excluir o próprio usuário
    if user.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    # Exclui o usuário
    db.session.delete(user)
    db.session.commit()
    
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_usuarios'))

@admin.route('/feriados')
@login_required
def listar_feriados():
    """Lista todos os feriados cadastrados"""
    feriados = Feriado.query.order_by(Feriado.data).all()
    return render_template('admin/feriados.html', feriados=feriados)

@admin.route('/feriado/novo', methods=['GET', 'POST'])
@login_required
def novo_feriado():
    """Cria um novo feriado"""
    form = FeriadoForm()
    
    if form.validate_on_submit():
        # Verifica se já existe um feriado nesta data
        if Feriado.query.filter_by(data=form.data.data).first():
            flash('Já existe um feriado cadastrado para esta data.', 'danger')
            return render_template('admin/novo_feriado.html', form=form)
        
        # Cria um novo feriado
        novo_feriado = Feriado(
            data=form.data.data,
            descricao=form.descricao.data
        )
        
        # Salva no banco de dados
        db.session.add(novo_feriado)
        db.session.commit()
        
        flash('Feriado cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.listar_feriados'))
    
    return render_template('admin/novo_feriado.html', form=form)

@admin.route('/feriado/editar/<int:feriado_id>', methods=['GET', 'POST'])
@login_required
def editar_feriado(feriado_id):
    """Edita um feriado existente"""
    feriado = Feriado.query.get_or_404(feriado_id)
    form = FeriadoForm(obj=feriado)
    
    if form.validate_on_submit():
        # Verifica se já existe outro feriado nesta data
        feriado_existente = Feriado.query.filter_by(data=form.data.data).first()
        if feriado_existente and feriado_existente.id != feriado_id:
            flash('Já existe outro feriado cadastrado para esta data.', 'danger')
            return render_template('admin/editar_feriado.html', form=form, feriado=feriado)
        
        # Atualiza os dados do feriado
        feriado.data = form.data.data
        feriado.descricao = form.descricao.data
        
        # Salva as alterações
        db.session.commit()
        
        flash('Feriado atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_feriados'))
    
    return render_template('admin/editar_feriado.html', form=form, feriado=feriado)

@admin.route('/feriado/excluir/<int:feriado_id>', methods=['POST'])
@login_required
def excluir_feriado(feriado_id):
    """Exclui um feriado"""
    feriado = Feriado.query.get_or_404(feriado_id)
    
    # Exclui o feriado
    db.session.delete(feriado)
    db.session.commit()
    
    flash('Feriado excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_feriados'))

@admin.route('/relatorios')
@login_required
def relatorios():
    """Página de relatórios administrativos"""
    usuarios = User.query.filter(User.is_active == True).order_by(User.name).all()
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/relatorio/<int:user_id>')
@login_required
def relatorio_usuario(user_id):
    """Exibe o relatório de um usuário específico"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano do relatório
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
    hoje = date.today()
    if not mes or not ano:
        mes_atual = hoje.month
        ano_atual = hoje.year
    else:
        mes_atual = mes
        ano_atual = ano
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
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
    
    # Cria um dicionário de feriados para fácil acesso
    feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
    
    # Calcula estatísticas
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta e não é feriado)
        if data_atual.weekday() < 5 and data_atual not in feriados_dict:
            dias_uteis += 1
    
    # Processa os registros
    for registro in registros:
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
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('admin/relatorio_usuario.html',
                          user=user,
                          registros=registros,
                          mes=mes_atual,
                          ano=ano_atual,
                          nome_mes=nome_mes,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas)

# CORREÇÃO: Adicionando a rota relatorio_usuario_pdf que estava faltando
@admin.route('/relatorio/<int:user_id>/pdf')
@login_required
def relatorio_usuario_pdf(user_id):
    """Gera um relatório em PDF para um usuário específico"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano do relatório
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
    hoje = date.today()
    if not mes or not ano:
        mes_atual = hoje.month
        ano_atual = hoje.year
    else:
        mes_atual = mes
        ano_atual = ano
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
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
    
    # Cria um dicionário de feriados para fácil acesso
    feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
    
    # Calcula estatísticas
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta e não é feriado)
        if data_atual.weekday() < 5 and data_atual not in feriados_dict:
            dias_uteis += 1
    
    # Processa os registros
    for registro in registros:
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
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # Gera o PDF
    pdf_path = export_registros_pdf(
        usuario=user,
        registros=registros,
        mes_atual=mes_atual,
        ano_atual=ano_atual,
        nome_mes=nome_mes,
        dias_uteis=dias_uteis,
        dias_trabalhados=dias_trabalhados,
        dias_afastamento=dias_afastamento,
        horas_trabalhadas=horas_trabalhadas,
        carga_horaria_devida=carga_horaria_devida,
        saldo_horas=saldo_horas,
        feriados_dict=feriados_dict
    )
    
    logger.info(f"PDF gerado com sucesso para o usuário {user.name} - {nome_mes}/{ano_atual}")
    
    return send_file(pdf_path, as_attachment=True, download_name=f'relatorio_{user.name}_{nome_mes}_{ano_atual}.pdf')

# CORREÇÃO: Adicionando a rota relatorio_usuario_excel que também pode estar faltando
@admin.route('/relatorio/<int:user_id>/excel')
@login_required
def relatorio_usuario_excel(user_id):
    """Gera um relatório em Excel para um usuário específico"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano do relatório
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
    hoje = date.today()
    if not mes or not ano:
        mes_atual = hoje.month
        ano_atual = hoje.year
    else:
        mes_atual = mes
        ano_atual = ano
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
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
    
    # Cria um dicionário de feriados para fácil acesso
    feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
    
    # Calcula estatísticas
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta e não é feriado)
        if data_atual.weekday() < 5 and data_atual not in feriados_dict:
            dias_uteis += 1
    
    # Processa os registros
    for registro in registros:
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
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # Gera o Excel
    excel_path = export_registros_excel(
        usuario=user,
        registros=registros,
        mes_atual=mes_atual,
        ano_atual=ano_atual,
        nome_mes=nome_mes,
        dias_uteis=dias_uteis,
        dias_trabalhados=dias_trabalhados,
        dias_afastamento=dias_afastamento,
        horas_trabalhadas=horas_trabalhadas,
        carga_horaria_devida=carga_horaria_devida,
        saldo_horas=saldo_horas,
        feriados_dict=feriados_dict
    )
    
    logger.info(f"Excel gerado com sucesso para o usuário {user.name} - {nome_mes}/{ano_atual}")
    
    return send_file(excel_path, as_attachment=True, download_name=f'relatorio_{user.name}_{nome_mes}_{ano_atual}.xlsx')

@admin.route('/backup')
@login_required
def backup():
    """Página de backup do banco de dados"""
    return render_template('admin/backup.html')

@admin.route('/backup/download')
@login_required
def download_backup():
    """Faz o download do arquivo de backup do banco de dados"""
    from app.utils.backup import create_backup
    
    # Cria o backup
    backup_path = create_backup()
    
    # Faz o download do arquivo
    return send_file(backup_path, as_attachment=True, download_name='backup.sqlite')

@admin.route('/backup/restaurar', methods=['POST'])
@login_required
def restaurar_backup():
    """Restaura o banco de dados a partir de um arquivo de backup"""
    from app.utils.backup import restore_backup
    
    # Verifica se foi enviado um arquivo
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo enviado.', 'danger')
        return redirect(url_for('admin.backup'))
    
    arquivo = request.files['arquivo']
    
    # Verifica se o arquivo tem um nome
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('admin.backup'))
    
    # Verifica se o arquivo é um arquivo SQLite
    if not arquivo.filename.endswith('.sqlite'):
        flash('O arquivo deve ser um arquivo SQLite (.sqlite).', 'danger')
        return redirect(url_for('admin.backup'))
    
    # Restaura o backup
    try:
        restore_backup(arquivo)
        flash('Backup restaurado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar o backup: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup'))
