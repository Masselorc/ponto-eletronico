from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, RegistroMultiploPontoForm, EditarPontoForm, AtividadeForm
from datetime import datetime, timedelta, date
from calendar import monthrange
import logging
import os
from app.utils.export import generate_pdf, generate_excel

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

@main.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@main.route('/perfil')
@login_required
def perfil():
    """Rota para exibir o perfil do usuário."""
    return render_template('main/perfil.html', usuario=current_user)

@main.route('/dashboard')
@login_required
def dashboard():
    user_id = request.args.get('user_id', type=int)
    
    # Se o usuário não for admin, só pode ver seu próprio dashboard
    if user_id and user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar o dashboard de outros usuários.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Se não for especificado um user_id ou o usuário não for admin, mostra o próprio dashboard
    if not user_id or not current_user.is_admin:
        user_id = current_user.id
        usuario = current_user
    else:
        usuario = User.query.get_or_404(user_id)
    
    # Obtém a data atual
    hoje = date.today()
    
    # Obtém o mês e ano atuais
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
    # Obtém os registros de ponto do mês atual para o usuário
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
    feriados_datas = set(feriados_dict.keys())
    
    # Obtém o registro de hoje, se existir
    registro_hoje = Ponto.query.filter_by(
        user_id=user_id,
        data=hoje
    ).first()
    
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
    
    # Se for admin, obtém a lista de usuários para o seletor
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.filter(User.is_active == True).order_by(User.name).all()
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('main/dashboard.html',
                          usuario=usuario,
                          registros=registros,
                          registros_mes=registros,
                          hoje=hoje,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas,
                          usuarios=usuarios,
                          registro_hoje=registro_hoje,
                          feriados_dict=feriados_dict,
                          feriados_datas=feriados_datas)

@main.route('/calendario')
@login_required
def calendario():
    user_id = request.args.get('user_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se o usuário não for admin, só pode ver seu próprio calendário
    if user_id and user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar o calendário de outros usuários.', 'danger')
        return redirect(url_for('main.calendario'))
    
    # Se não for especificado um user_id ou o usuário não for admin, mostra o próprio calendário
    if not user_id or not current_user.is_admin:
        user_id = current_user.id
        usuario = current_user
    else:
        usuario = User.query.get_or_404(user_id)
    
    # Obtém a data atual
    hoje = date.today()
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
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
    registros_query = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).order_by(Ponto.data)
    
    registros_lista = registros_query.all()
    logger.info(f"Recuperados {len(registros_lista)} registros para o mês {mes_atual}/{ano_atual}")
    
    # Cria um dicionário de registros indexado por data
    registros = {}
    for registro in registros_lista:
        registros[registro.data] = registro
        if registro.afastamento:
            logger.info(f"Registro {registros_lista.index(registro) + 1}: data={registro.data}, afastamento={registro.afastamento}, tipo={registro.tipo_afastamento}")
    
    # Obtém os feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    
    # Cria um conjunto de datas de feriados para fácil verificação
    feriados_datas = {feriado.data for feriado in feriados}
    
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
        if data_atual.weekday() < 5 and data_atual not in feriados_datas:
            dias_uteis += 1
            
            # Verifica se há registro para este dia
            if data_atual in registros:
                registro = registros[data_atual]
                
                if registro.afastamento:
                    # Se for um dia de afastamento
                    dias_afastamento += 1
                    logger.info(f"Dia {data_atual} contabilizado como afastamento: {registro.tipo_afastamento}")
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
    
    # Se for admin, obtém a lista de usuários para o seletor
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.filter(User.is_active == True).order_by(User.name).all()
    
    return render_template('main/calendario.html',
                          usuario=usuario,
                          registros=registros,
                          hoje=hoje,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          nome_mes=nome_mes,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas,
                          feriados_datas=feriados_datas,
                          feriados_dict=feriados_dict,
                          usuarios=usuarios,
                          timedelta=timedelta,
                          date=date)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    form = RegistroPontoForm()
    
    # Se uma data for fornecida via GET, preenche o formulário
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            form.data.data = data_selecionada
            # CORREÇÃO AVANÇADA: Armazena a data original como string
            form.data_original.data = data_str
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    
    if form.validate_on_submit():
        # CORREÇÃO AVANÇADA: Usar a data original do formulário se disponível
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                # Fallback para o campo data normal se houver erro
                data_selecionada = form.data.data
                logger.warning(f"Erro ao converter data original, usando data normal: {data_selecionada}")
        else:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        # Verifica se já existe um registro para a data selecionada
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'warning')
            return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
        
        # Cria um novo registro com a data selecionada
        novo_registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada,  # CORREÇÃO AVANÇADA: Usar a data original
            entrada=datetime.now().time(),
            observacoes="Registro automático de entrada"
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        flash(f'Entrada registrada com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
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
            # CORREÇÃO AVANÇADA: Armazena a data original como string
            form.data_original.data = data_str
            logger.info(f"Data original armazenada: {data_str}")
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    else:
        # Preenche com a data atual se não for fornecida
        hoje = datetime.now().date()
        form.data.data = hoje
        # CORREÇÃO AVANÇADA: Armazena a data atual como string
        form.data_original.data = hoje.strftime('%Y-%m-%d')
        logger.info(f"Data atual armazenada: {form.data_original.data}")
    
    if form.validate_on_submit():
        # CORREÇÃO AVANÇADA: Usar a data original do formulário se disponível
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                # Fallback para o campo data normal se houver erro
                data_selecionada = form.data.data
                logger.warning(f"Erro ao converter data original, usando data normal: {data_selecionada}")
        else:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        logger.info(f"Registrando ponto para a data: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        # Permitir registro retroativo mesmo se já existir um registro para a data
        # Se a data for hoje e já existir registro, redireciona para edição
        # Se a data for anterior e já existir registro, pergunta se deseja sobrescrever
        if registro_existente:
            hoje = date.today()
            if data_selecionada == hoje:
                flash(f'Já existe um registro para hoje. Você pode editá-lo.', 'warning')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
            else:
                # Para datas anteriores, permite sobrescrever o registro existente
                from app import db
                db.session.delete(registro_existente)
                db.session.commit()
                flash(f'Registro anterior para {data_selecionada.strftime("%d/%m/%Y")} foi substituído.', 'info')
        
        # Cria um novo registro com a data selecionada
        novo_registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada  # CORREÇÃO AVANÇADA: Usar a data original
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
                novo_registro.entrada = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.saida_almoco.data:
                hora, minuto = map(int, form.saida_almoco.data.split(':'))
                novo_registro.saida_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.retorno_almoco.data:
                hora, minuto = map(int, form.retorno_almoco.data.split(':'))
                novo_registro.retorno_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.saida.data:
                hora, minuto = map(int, form.saida.data.split(':'))
                novo_registro.saida = datetime.min.time().replace(hour=hora, minute=minuto)
            
            # Calcula as horas trabalhadas
            novo_registro.calcular_horas_trabalhadas()
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        # Registra a atividade se o campo estiver preenchido
        if hasattr(form, 'atividades') and form.atividades.data:
            atividade = Atividade(
                ponto_id=novo_registro.id,
                descricao=form.atividades.data
            )
            db.session.add(atividade)
            db.session.commit()
            logger.info(f"Atividade registrada para o ponto {novo_registro.id}")
        
        flash(f'Registro de ponto realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('main.calendario'))
    
    return render_template('main/registrar_multiplo_ponto.html', form=form)

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para editar este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = EditarPontoForm()
    
    # Preenche o formulário com os dados do registro
    if request.method == 'GET':
        form.data.data = ponto.data
        # CORREÇÃO AVANÇADA: Armazena a data original como string
        form.data_original.data = ponto.data.strftime('%Y-%m-%d')
        form.afastamento.data = ponto.afastamento
        form.tipo_afastamento.data = ponto.tipo_afastamento
        
        if ponto.entrada:
            form.entrada.data = ponto.entrada.strftime('%H:%M')
        if ponto.saida_almoco:
            form.saida_almoco.data = ponto.saida_almoco.strftime('%H:%M')
        if ponto.retorno_almoco:
            form.retorno_almoco.data = ponto.retorno_almoco.strftime('%H:%M')
        if ponto.saida:
            form.saida.data = ponto.saida.strftime('%H:%M')
        
        form.observacoes.data = ponto.observacoes
    
    if form.validate_on_submit():
        # CORREÇÃO AVANÇADA: Usar a data original do formulário se disponível
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                # Fallback para o campo data normal se houver erro
                data_selecionada = form.data.data
                logger.warning(f"Erro ao converter data original, usando data normal: {data_selecionada}")
        else:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        # Atualiza os dados do registro
        ponto.data = data_selecionada  # CORREÇÃO AVANÇADA: Usar a data original
        ponto.afastamento = form.afastamento.data
        
        if form.afastamento.data:
            ponto.tipo_afastamento = form.tipo_afastamento.data
            ponto.entrada = None
            ponto.saida_almoco = None
            ponto.retorno_almoco = None
            ponto.saida = None
            ponto.horas_trabalhadas = 0
        else:
            ponto.tipo_afastamento = None
            
            # Processa os horários apenas se não for afastamento
            if form.entrada.data:
                hora, minuto = map(int, form.entrada.data.split(':'))
                ponto.entrada = datetime.min.time().replace(hour=hora, minute=minuto)
            else:
                ponto.entrada = None
            
            if form.saida_almoco.data:
                hora, minuto = map(int, form.saida_almoco.data.split(':'))
                ponto.saida_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            else:
                ponto.saida_almoco = None
            
            if form.retorno_almoco.data:
                hora, minuto = map(int, form.retorno_almoco.data.split(':'))
                ponto.retorno_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            else:
                ponto.retorno_almoco = None
            
            if form.saida.data:
                hora, minuto = map(int, form.saida.data.split(':'))
                ponto.saida = datetime.min.time().replace(hour=hora, minute=minuto)
            else:
                ponto.saida = None
            
            # Calcula as horas trabalhadas
            ponto.calcular_horas_trabalhadas()
        
        # Atualiza as observações se o campo existir
        if hasattr(form, 'observacoes'):
            ponto.observacoes = form.observacoes.data
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash(f'Registro de ponto atualizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('main.calendario'))
    
    return render_template('main/editar_ponto.html', form=form, ponto=ponto)

@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para adicionar atividades a este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para adicionar atividades a este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = AtividadeForm()
    
    if form.validate_on_submit():
        # Cria uma nova atividade
        atividade = Atividade(
            ponto_id=ponto_id,
            descricao=form.descricao.data
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(atividade)
        db.session.commit()
        
        flash('Atividade registrada com sucesso!', 'success')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
    
    return render_template('main/registrar_atividade.html', form=form, ponto=ponto)

# IMPORTANTE: Rota visualizar_ponto que estava faltando na correção anterior
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para visualizar este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém as atividades deste ponto
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).order_by(Atividade.created_at).all()
    
    return render_template('main/visualizar_ponto.html', ponto=ponto, atividades=atividades)

@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    user_id = request.args.get('user_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se o usuário não for admin, só pode ver seu próprio relatório
    if user_id and user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar o relatório de outros usuários.', 'danger')
        return redirect(url_for('main.relatorio_mensal'))
    
    # Se não for especificado um user_id ou o usuário não for admin, mostra o próprio relatório
    if not user_id or not current_user.is_admin:
        user_id = current_user.id
        usuario = current_user
    else:
        usuario = User.query.get_or_404(user_id)
    
    # Obtém a data atual
    hoje = date.today()
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
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
    
    # Se for admin, obtém a lista de usuários para o seletor
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.filter(User.is_active == True).order_by(User.name).all()
    
    return render_template('main/relatorio_mensal.html',
                          usuario=usuario,
                          registros=registros,
                          hoje=hoje,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas,
                          usuarios=usuarios)

@main.route('/exportar-pdf')
@login_required
def exportar_pdf():
    user_id = request.args.get('user_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se o usuário não for admin, só pode exportar seu próprio relatório
    if user_id and user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para exportar o relatório de outros usuários.', 'danger')
        return redirect(url_for('main.relatorio_mensal'))
    
    # Se não for especificado um user_id ou o usuário não for admin, exporta o próprio relatório
    if not user_id or not current_user.is_admin:
        user_id = current_user.id
        usuario = current_user
    else:
        usuario = User.query.get_or_404(user_id)
    
    # Obtém a data atual
    hoje = date.today()
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
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
    pdf_path = generate_pdf(
        usuario=usuario,
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
    
    return send_file(pdf_path, as_attachment=True, download_name=f'relatorio_{usuario.name}_{nome_mes}_{ano_atual}.pdf')

@main.route('/exportar-excel')
@login_required
def exportar_excel():
    user_id = request.args.get('user_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    # Se o usuário não for admin, só pode exportar seu próprio relatório
    if user_id and user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para exportar o relatório de outros usuários.', 'danger')
        return redirect(url_for('main.relatorio_mensal'))
    
    # Se não for especificado um user_id ou o usuário não for admin, exporta o próprio relatório
    if not user_id or not current_user.is_admin:
        user_id = current_user.id
        usuario = current_user
    else:
        usuario = User.query.get_or_404(user_id)
    
    # Obtém a data atual
    hoje = date.today()
    
    # Se não for especificado mês e ano, usa o mês e ano atuais
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
    excel_path = generate_excel(
        usuario=usuario,
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
    
    return send_file(excel_path, as_attachment=True, download_name=f'relatorio_{usuario.name}_{nome_mes}_{ano_atual}.xlsx')
