from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.ponto import Ponto, Atividade, Feriado
from app.models.user import User
from app import db
from app.forms.ponto import RegistroPontoForm, AtividadeForm
from datetime import datetime, timedelta, date

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
    
    if form.validate_on_submit():
        data_selecionada = form.data.data
        hora_selecionada = form.hora.data
        tipo = form.tipo.data
        
        # Verifica se já existe registro para a data selecionada
        registro = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if not registro:
            registro = Ponto(user_id=current_user.id, data=data_selecionada)
        
        # Extrai apenas o componente time do objeto datetime ou converte para time se necessário
        if isinstance(hora_selecionada, datetime):
            hora_time = hora_selecionada.time()
        else:
            hora_time = hora_selecionada
            
        # Usa a hora selecionada pelo usuário
        if tipo == 'entrada':
            registro.entrada = hora_time
        elif tipo == 'saida_almoco':
            registro.saida_almoco = hora_time
        elif tipo == 'retorno_almoco':
            registro.retorno_almoco = hora_time
        elif tipo == 'saida':
            registro.saida = hora_time
            
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
        
        try:
            if not registro.id:
                db.session.add(registro)
            
            db.session.commit()
            flash(f'Registro de {tipo} realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")} às {hora_time.strftime("%H:%M")}!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar ponto: {str(e)}', 'danger')
    
    return render_template('main/registrar_ponto.html', form=form, hoje=hoje)

@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual
    if ponto.user_id != current_user.id and not current_user.is_admin:
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

@main.route('/perfil')
@login_required
def perfil():
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
        Ponto.user_id == current_user.id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Obtém o total de registros
    total_registros = Ponto.query.filter_by(user_id=current_user.id).count()
    
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
    
    return render_template('main/perfil.html', 
                          total_registros=total_registros,
                          horas_mes=horas_mes,
                          saldo_horas=saldo_horas)

@main.route('/editar-perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    # Implementação da edição de perfil será adicionada aqui
    flash('Funcionalidade em desenvolvimento', 'info')
    return redirect(url_for('main.perfil'))

@main.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    # Implementação da alteração de senha será adicionada aqui
    flash('Funcionalidade em desenvolvimento', 'info')
    return redirect(url_for('main.perfil'))

@main.route('/calendario')
@login_required
def calendario():
    # Obtém o mês atual ou o mês selecionado
    hoje = datetime.now().date()
    mes_atual = request.args.get('mes', hoje.month, type=int)
    ano_atual = request.args.get('ano', hoje.year, type=int)
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    if mes_atual == 12:
        ultimo_dia = date(ano_atual + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano_atual, mes_atual + 1, 1) - timedelta(days=1)
    
    # Obtém todos os registros do mês atual
    registros = Ponto.query.filter(
        Ponto.user_id == current_user.id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Organiza os registros por data para fácil acesso no template
    registros_por_data = {registro.data: registro for registro in registros}
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    return render_template('main/calendario.html', 
                          registros=registros_por_data,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          hoje=hoje,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          feriados_datas=feriados_datas,
                          timedelta=timedelta)
