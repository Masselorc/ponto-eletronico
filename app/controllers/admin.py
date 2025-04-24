from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, send_file
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado  # Importação corrigida do modelo Feriado
from app import db
from app.forms.admin import UserForm, FeriadoForm
from app.forms.ponto import RegistroPontoForm, AtividadeForm
from datetime import datetime, date, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.utils.excel_generator import generate_excel_report
from app.utils.export import export_registros_pdf, export_registros_excel
import os

# Blueprint para área administrativa - Versão corrigida Abril 2025
admin = Blueprint('admin', __name__, url_prefix='/admin')

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
    """Cria um novo usuário no sistema"""
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
    """Edita um usuário existente"""
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
    """Exclui um usuário do sistema"""
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
    """Lista todos os feriados cadastrados"""
    feriados = Feriado.query.order_by(Feriado.data).all()
    return render_template('admin/feriados.html', feriados=feriados)

@admin.route('/feriado/novo', methods=['GET', 'POST'])
@login_required
def novo_feriado():
    """Cadastra um novo feriado"""
    form = FeriadoForm()
    # Busca todos os feriados existentes para exibir na página
    feriados = Feriado.query.order_by(Feriado.data).all()
    
    if form.validate_on_submit():
        feriado = Feriado(
            data=form.data.data,
            descricao=form.descricao.data
        )
        db.session.add(feriado)
        db.session.commit()
        flash('Feriado registrado com sucesso!', 'success')
        return redirect(url_for('admin.novo_feriado'))
    
    return render_template('admin/form_feriado.html', form=form, title='Novo Feriado', feriados=feriados)

@admin.route('/feriado/excluir/<int:feriado_id>', methods=['POST'])
@login_required
def excluir_feriado(feriado_id):
    """Exclui um feriado cadastrado"""
    feriado = Feriado.query.get_or_404(feriado_id)
    db.session.delete(feriado)
    db.session.commit()
    flash('Feriado excluído com sucesso!', 'success')
    return redirect(url_for('admin.novo_feriado'))

@admin.route('/relatorios')
@login_required
def relatorios():
    """Página de relatórios administrativos"""
    # Busca todos os usuários, incluindo administradores
    usuarios = User.query.all()
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/relatorio/<int:user_id>')
@login_required
def relatorio_usuario(user_id):
    """Exibe relatório detalhado de um usuário"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano da URL ou usa o mês atual
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
    
    # Obtém todos os registros do mês selecionado
    registros = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data < ultimo_dia
    ).order_by(Ponto.data).all()
    
    # Organiza os registros por data para fácil acesso no template
    registros_por_data = {registro.data: registro for registro in registros}
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data < ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Cria um dicionário de feriados para exibir as descrições
    feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
    
    # Calcula o saldo de horas do mês
    dias_uteis = 0
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano, mes, dia)
        if data.weekday() < 5 and data not in feriados_datas:  # 0-4 são dias de semana (seg-sex)
            dias_uteis += 1
    
    horas_esperadas = dias_uteis * 8  # 8 horas por dia útil
    horas_trabalhadas = sum(registro.horas_trabalhadas or 0 for registro in registros)
    saldo_horas = horas_trabalhadas - horas_esperadas
    
    return render_template('admin/relatorio_usuario.html', 
                          user=user,
                          registros=registros,
                          registros_por_data=registros_por_data,
                          mes=mes,
                          ano=ano,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          feriados_datas=feriados_datas,
                          feriados_dict=feriados_dict,
                          date=date,
                          horas_esperadas=horas_esperadas,
                          horas_trabalhadas=horas_trabalhadas,
                          saldo_horas=saldo_horas)

@admin.route('/ponto/editar/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Edita um registro de ponto existente"""
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
    """Cria um novo registro de ponto para um usuário"""
    user = User.query.get_or_404(user_id)
    form = RegistroPontoForm()
    
    # Se uma data for fornecida via GET, preenche o formulário
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            form.data.data = data_selecionada
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    
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
    """Exclui um registro de ponto"""
    ponto = Ponto.query.get_or_404(ponto_id)
    user_id = ponto.user_id
    
    db.session.delete(ponto)
    db.session.commit()
    flash('Registro de ponto excluído com sucesso!', 'success')
    return redirect(url_for('admin.relatorio_usuario', user_id=user_id))

@admin.route('/atividade/nova/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def nova_atividade(ponto_id):
    """Registra uma nova atividade para um ponto"""
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
    """Exclui uma atividade registrada"""
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
    """Gera um relatório em PDF para um usuário"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano da URL ou usa o mês atual
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Obtém todos os registros do mês selecionado
    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
    
    # Gera o PDF usando a função utilitária
    pdf_path = export_registros_pdf(user_id, mes, ano)
    
    if pdf_path:
        return send_file(pdf_path, as_attachment=True, download_name=f'relatorio_{user.matricula}_{mes}_{ano}.pdf')
    else:
        flash('Erro ao gerar o PDF. Tente novamente.', 'danger')
        return redirect(url_for('admin.relatorio_usuario', user_id=user_id))

@admin.route('/relatorio/<int:user_id>/excel')
@login_required
def relatorio_usuario_excel(user_id):
    """Gera um relatório em Excel para um usuário"""
    user = User.query.get_or_404(user_id)
    
    # Obtém o mês e ano da URL ou usa o mês atual
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Gera o Excel usando a função utilitária
    excel_path = export_registros_excel(user_id, mes, ano)
    
    if excel_path:
        return send_file(excel_path, as_attachment=True, download_name=f'relatorio_{user.matricula}_{mes}_{ano}.xlsx')
    else:
        flash('Erro ao gerar o Excel. Tente novamente.', 'danger')
        return redirect(url_for('admin.relatorio_usuario', user_id=user_id))
