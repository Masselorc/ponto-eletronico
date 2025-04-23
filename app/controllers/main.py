from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.ponto import Ponto, Atividade
from app.models.user import User
from app import db
from app.forms.ponto import RegistroPontoForm, AtividadeForm
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    # Obtém a data atual
    hoje = datetime.now().date()
    
    # Verifica se já existe registro para hoje
    registro_hoje = Ponto.query.filter_by(
        user_id=current_user.id,
        data=hoje
    ).first()
    
    # Obtém registros da semana atual
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    registros_semana = Ponto.query.filter(
        Ponto.user_id == current_user.id,
        Ponto.data >= inicio_semana,
        Ponto.data <= fim_semana
    ).all()
    
    return render_template('main/dashboard.html', 
                          registro_hoje=registro_hoje,
                          registros_semana=registros_semana,
                          hoje=hoje)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    form = RegistroPontoForm()
    hoje = datetime.now().date()
    
    # Verifica se já existe registro para hoje
    registro = Ponto.query.filter_by(
        user_id=current_user.id,
        data=hoje
    ).first()
    
    if not registro:
        registro = Ponto(user_id=current_user.id, data=hoje)
    
    if form.validate_on_submit():
        tipo = form.tipo.data
        hora_atual = datetime.now().time()
        
        if tipo == 'entrada':
            registro.entrada = hora_atual
        elif tipo == 'saida_almoco':
            registro.saida_almoco = hora_atual
        elif tipo == 'retorno_almoco':
            registro.retorno_almoco = hora_atual
        elif tipo == 'saida':
            registro.saida = hora_atual
            
        # Calcula horas trabalhadas se tiver todos os registros
        if (registro.entrada and registro.saida_almoco and 
            registro.retorno_almoco and registro.saida):
            
            # Tempo antes do almoço
            t1 = datetime.combine(hoje, registro.saida_almoco) - datetime.combine(hoje, registro.entrada)
            
            # Tempo depois do almoço
            t2 = datetime.combine(hoje, registro.saida) - datetime.combine(hoje, registro.retorno_almoco)
            
            # Total de horas trabalhadas
            total_segundos = t1.total_seconds() + t2.total_seconds()
            registro.horas_trabalhadas = total_segundos / 3600  # Converte para horas
        
        if not registro.id:
            db.session.add(registro)
        
        db.session.commit()
        flash(f'Registro de {tipo} realizado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_ponto.html', form=form, registro=registro)

@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual
    if ponto.user_id != current_user.id:
        flash('Você não tem permissão para acessar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = AtividadeForm()
    
    if form.validate_on_submit():
        atividade = Atividade(
            ponto_id=ponto_id,
            descricao=form.descricao.data
        )
        db.session.add(atividade)
        db.session.commit()
        flash('Atividade registrada com sucesso!', 'success')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
    
    return render_template('main/registrar_atividade.html', form=form, ponto=ponto)

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para acessar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    
    return render_template('main/visualizar_ponto.html', ponto=ponto, atividades=atividades)

@main.route('/calendario')
@login_required
def calendario():
    # Obtém o mês atual
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Obtém todos os registros do mês atual
    primeiro_dia = datetime(ano_atual, mes_atual, 1).date()
    if mes_atual == 12:
        ultimo_dia = datetime(ano_atual + 1, 1, 1).date() - timedelta(days=1)
    else:
        ultimo_dia = datetime(ano_atual, mes_atual + 1, 1).date() - timedelta(days=1)
    
    registros = Ponto.query.filter(
        Ponto.user_id == current_user.id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Organiza os registros por data para fácil acesso no template
    registros_por_data = {registro.data: registro for registro in registros}
    
    return render_template('main/calendario.html', 
                          registros=registros_por_data,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual)
