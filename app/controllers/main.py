from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.ponto import Ponto
from app.models.user import User
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, RegistroMultiploPontoForm, EditarPontoForm
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@main.route('/dashboard/<int:user_id>')
@login_required
def dashboard(user_id=None):
    # Se for admin e um user_id for fornecido, mostra o dashboard daquele usuário
    if current_user.is_admin and user_id and user_id != current_user.id:
        usuario = User.query.get_or_404(user_id)
    else:
        # Usa o usuário atual
        usuario = current_user
        user_id = current_user.id
    
    # Lista de usuários para o seletor (apenas para admin)
    usuarios = []
    if current_user.is_admin:
        usuarios = User.query.order_by(User.name).all()
    
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
    
    # Obtém o registro de hoje
    registro_hoje = Ponto.query.filter_by(
        user_id=user_id,
        data=hoje
    ).first()
    
    # Obtém todos os registros do mês atual
    registros_mes = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).order_by(Ponto.data.desc()).all()
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]  # Ajuste para índice 0-based
    
    # Calcular estatísticas do mês
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Calcular dias úteis e estatísticas
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (seg-sex e não é feriado)
        if data.weekday() < 5 and data not in feriados_datas:
            dias_uteis += 1
            
            # Verifica se tem registro para este dia
            registro = next((r for r in registros_mes if r.data == data), None)
            if registro:
                # Verifica se é afastamento
                if registro.afastamento:
                    dias_afastamento += 1
                    logger.info(f"Dia {data} contabilizado como afastamento: {registro.tipo_afastamento}")
                # Se não for afastamento e tiver horas trabalhadas, conta como dia trabalhado
                elif registro.horas_trabalhadas:
                    dias_trabalhados += 1
                    horas_trabalhadas += registro.horas_trabalhadas
    
    # Calcular carga horária devida (8h por dia útil, excluindo afastamentos)
    dias_uteis_efetivos = dias_uteis - dias_afastamento
    carga_horaria_devida = dias_uteis_efetivos * 8
    
    # Calcular saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    return render_template('main/dashboard.html', 
                          registro_hoje=registro_hoje,
                          registros_mes=registros_mes,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          hoje=hoje,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          feriados_datas=feriados_datas,
                          usuario=usuario,
                          usuarios=usuarios,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas)

@main.route('/calendario')
@main.route('/calendario/<int:user_id>')
@login_required
def calendario(user_id=None):
    # Se for admin e um user_id for fornecido, mostra o calendário daquele usuário
    if current_user.is_admin and user_id and user_id != current_user.id:
        usuario = User.query.get_or_404(user_id)
    else:
        # Usa o usuário atual
        usuario = current_user
        user_id = current_user.id
    
    # Lista de usuários para o seletor (apenas para admin)
    usuarios = []
    if current_user.is_admin:
        usuarios = User.query.order_by(User.name).all()
    
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
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Log para debug
    logger.info(f"Recuperados {len(registros)} registros para o mês {mes_atual}/{ano_atual}")
    for registro in registros:
        logger.info(f"Registro {registro.id}: data={registro.data}, afastamento={registro.afastamento}, tipo={registro.tipo_afastamento}")
    
    # Organiza os registros por data para fácil acesso no template
    registros_por_data = {registro.data: registro for registro in registros}
    
    # Obtém feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    feriados_datas = [feriado.data for feriado in feriados]
    
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]  # Ajuste para índice 0-based
    
    # Calcular estatísticas do mês
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Calcular dias úteis e estatísticas
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (seg-sex e não é feriado)
        if data.weekday() < 5 and data not in feriados_datas:
            dias_uteis += 1
            
            # Verifica se tem registro para este dia
            if data in registros_por_data:
                registro = registros_por_data[data]
                
                # Verifica se é afastamento
                if registro.afastamento:
                    dias_afastamento += 1
                    logger.info(f"Dia {data} contabilizado como afastamento: {registro.tipo_afastamento}")
                # Se não for afastamento e tiver horas trabalhadas, conta como dia trabalhado
                elif registro.horas_trabalhadas:
                    dias_trabalhados += 1
                    horas_trabalhadas += registro.horas_trabalhadas
    
    # Calcular carga horária devida (8h por dia útil, excluindo afastamentos)
    dias_uteis_efetivos = dias_uteis - dias_afastamento
    carga_horaria_devida = dias_uteis_efetivos * 8
    
    # Calcular saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    return render_template('main/calendario.html', 
                          registros=registros_por_data,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          hoje=hoje,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          feriados_datas=feriados_datas,
                          timedelta=timedelta,
                          date=date,
                          usuario=usuario,
                          usuarios=usuarios,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    form = RegistroPontoForm()
    
    if form.validate_on_submit():
        # Verifica se já existe um registro para hoje
        hoje = datetime.now().date()
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=hoje
        ).first()
        
        if registro_existente:
            flash('Já existe um registro para hoje. Você pode editá-lo.', 'warning')
            return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
        
        # Cria um novo registro
        novo_registro = Ponto(
            user_id=current_user.id,
            data=hoje,
            entrada=datetime.now(),
            observacoes="Registro automático de entrada"
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        flash('Entrada registrada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_ponto.html', form=form)

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    form = RegistroMultiploPontoForm()
    
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
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'warning')
            return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
        
        # Cria um novo registro
        novo_registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada
        )
        
        # Adiciona observações se o campo existir no formulário
        if hasattr(form, 'observacoes'):
            novo_registro.observacoes = form.observacoes.data
        
        # Verifica se é um registro de afastamento
        if form.afastamento.data:
            novo_registro.afastamento = True
            novo_registro.tipo_afastamento = form.tipo_afastamento.data
            logger.info(f"Registrando afastamento: {form.tipo_afastamento.data} para {data_selecionada}")
        else:
            # Processa os horários apenas se não for afastamento
            if form.entrada.data:
                hora, minuto = map(int, form.entrada.data.split(':'))
                novo_registro.entrada = datetime.combine(data_selecionada, datetime.min.time().replace(hour=hora, minute=minuto))
            
            if form.saida_almoco.data:
                hora, minuto = map(int, form.saida_almoco.data.split(':'))
                novo_registro.saida_almoco = datetime.combine(data_selecionada, datetime.min.time().replace(hour=hora, minute=minuto))
            
            if form.retorno_almoco.data:
                hora, minuto = map(int, form.retorno_almoco.data.split(':'))
                novo_registro.retorno_almoco = datetime.combine(data_selecionada, datetime.min.time().replace(hour=hora, minute=minuto))
            
            if form.saida.data:
                hora, minuto = map(int, form.saida.data.split(':'))
                novo_registro.saida = datetime.combine(data_selecionada, datetime.min.time().replace(hour=hora, minute=minuto))
            
            # Calcula as horas trabalhadas
            novo_registro.calcular_horas_trabalhadas()
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        flash('Registro de ponto realizado com sucesso!', 'success')
        return redirect(url_for('main.calendario'))
    
    return render_template('main/registrar_multiplo_ponto.html', form=form)

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para visualizar este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/visualizar_ponto.html', ponto=ponto)

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para editar este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = EditarPontoForm()
    
    if request.method == 'GET':
        # Preenche o formulário com os dados existentes
        form.data.data = ponto.data
        form.observacoes.data = ponto.observacoes
        form.afastamento.data = ponto.afastamento
        form.tipo_afastamento.data = ponto.tipo_afastamento if ponto.tipo_afastamento else 'outro'
        
        if ponto.entrada:
            form.entrada.data = ponto.entrada.strftime('%H:%M')
        
        if ponto.saida_almoco:
            form.saida_almoco.data = ponto.saida_almoco.strftime('%H:%M')
        
        if ponto.retorno_almoco:
            form.retorno_almoco.data = ponto.retorno_almoco.strftime('%H:%M')
        
        if ponto.saida:
            form.saida.data = ponto.saida.strftime('%H:%M')
    
    if form.validate_on_submit():
        # Atualiza os dados do ponto
        ponto.data = form.data.data
        ponto.observacoes = form.observacoes.data
        
        # Verifica se é um registro de afastamento
        ponto.afastamento = form.afastamento.data
        if ponto.afastamento:
            ponto.tipo_afastamento = form.tipo_afastamento.data
            # Limpa os horários se for afastamento
            ponto.entrada = None
            ponto.saida_almoco = None
            ponto.retorno_almoco = None
            ponto.saida = None
            ponto.horas_trabalhadas = None
            logger.info(f"Atualizando registro para afastamento: {form.tipo_afastamento.data}")
        else:
            ponto.tipo_afastamento = None
            
            # Processa os horários apenas se não for afastamento
            if form.entrada.data:
                hora, minuto = map(int, form.entrada.data.split(':'))
                ponto.entrada = datetime.combine(ponto.data, datetime.min.time().replace(hour=hora, minute=minuto))
            else:
                ponto.entrada = None
            
            if form.saida_almoco.data:
                hora, minuto = map(int, form.saida_almoco.data.split(':'))
                ponto.saida_almoco = datetime.combine(ponto.data, datetime.min.time().replace(hour=hora, minute=minuto))
            else:
                ponto.saida_almoco = None
            
            if form.retorno_almoco.data:
                hora, minuto = map(int, form.retorno_almoco.data.split(':'))
                ponto.retorno_almoco = datetime.combine(ponto.data, datetime.min.time().replace(hour=hora, minute=minuto))
            else:
                ponto.retorno_almoco = None
            
            if form.saida.data:
                hora, minuto = map(int, form.saida.data.split(':'))
                ponto.saida = datetime.combine(ponto.data, datetime.min.time().replace(hour=hora, minute=minuto))
            else:
                ponto.saida = None
            
            # Calcula as horas trabalhadas
            ponto.calcular_horas_trabalhadas()
        
        # Salva no banco de dados
        from app import db
        db.session.commit()
        
        flash('Registro de ponto atualizado com sucesso!', 'success')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto.id))
    
    return render_template('main/editar_ponto.html', form=form, ponto=ponto)

@main.route('/perfil')
@login_required
def perfil():
    return render_template('main/perfil.html')

@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para registrar atividade neste ponto
    if ponto.user_id != current_user.id:
        flash('Você não tem permissão para registrar atividade neste ponto.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Implementação futura
    return render_template('main/registrar_atividade.html', ponto=ponto)
