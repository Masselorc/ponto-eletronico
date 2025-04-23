from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from app import db
from app.forms.admin import UserForm, FeriadoForm
from datetime import datetime

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

@admin.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            matricula=form.matricula.data,
            vinculo=form.vinculo.data,
            is_admin=form.is_admin.data
        )
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
        user.vinculo = form.vinculo.data
        user.is_admin = form.is_admin.data
        
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
    usuarios = User.query.filter_by(is_admin=False).all()
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
