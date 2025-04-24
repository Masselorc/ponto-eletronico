from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, RegistroMultiploPontoForm, EditarPontoForm, AtividadeForm
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging
import os

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

@main.route('/')
def index():
    """Rota para a página inicial."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main.route('/perfil')
@login_required
def perfil():
    """Rota para a página de perfil do usuário."""
    # CORREÇÃO: Buscar o usuário real do banco de dados em vez de usar o proxy
    usuario = User.query.get(current_user.id)
    return render_template('main/perfil.html', usuario=usuario)

@main.route('/dashboard')
@login_required
def dashboard():
    """Rota para o dashboard do usuário."""
    # Obtém o ID do usuário da query string (para admins visualizarem outros usuários)
    user_id = request.args.get('user_id', type=int)
    
    # Se for admin e um ID de usuário for fornecido, obtém o usuário correspondente
    if current_user.is_admin and user_id:
        usuario = User.query.get_or_404(user_id)
    else:
        usuario = current_user
    
    # Obtém a lista de usuários para o seletor (apenas para admins)
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.filter_by(is_active=True).order_by(User.name).all()
    
    # Obtém o mês e ano atuais
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
    # Obtém os registros de ponto do mês para o usuário
    registros = Ponto.query.filter(
        Ponto.user_id == usuario.id,
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
    
    # CORREÇÃO: Melhorar o cálculo de dias úteis para excluir feriados e afastamentos
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Cria um dicionário de afastamentos para fácil acesso
    afastamentos_dict = {}
    for registro in registros:
        if registro.afastamento:
            afastamentos_dict[registro.data] = registro.tipo_afastamento
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta)
        if data_atual.weekday() < 5:
            # Verifica se não é feriado e não é dia de afastamento
            if data_atual not in feriados_dict and data_atual not in afastamentos_dict:
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
    
    # CORREÇÃO: Corrigir o cálculo da carga horária devida (8h por dia útil)
    # Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # CORREÇÃO: Adicionar cálculo da média diária de horas trabalhadas
    media_diaria = 0
    if dias_trabalhados > 0:
        media_diaria = horas_trabalhadas / dias_trabalhados
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('main/dashboard.html',
                          usuario=usuario,
                          usuarios=usuarios,
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
                          media_diaria=media_diaria)

@main.route('/calendario')
@login_required
def calendario():
    """Rota para o calendário de ponto."""
    # Obtém o ID do usuário da query string (para admins visualizarem outros usuários)
    user_id = request.args.get('user_id', type=int)
    
    # Se for admin e um ID de usuário for fornecido, obtém o usuário correspondente
    if current_user.is_admin and user_id:
        usuario = User.query.get_or_404(user_id)
    else:
        usuario = current_user
    
    # Obtém o mês e ano da query string
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
        Ponto.user_id == usuario.id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).all()
    
    # Cria um dicionário de registros para fácil acesso
    registros_dict = {registro.data: registro for registro in registros}
    
    # Obtém os feriados do mês
    feriados = Feriado.query.filter(
        Feriado.data >= primeiro_dia,
        Feriado.data <= ultimo_dia
    ).all()
    
    # Cria um dicionário de feriados para fácil acesso
    feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
    
    # Obtém o dia da semana do primeiro dia do mês (0 = segunda, 6 = domingo)
    primeiro_dia_semana = primeiro_dia.weekday()
    # Ajusta para o formato do calendário (0 = domingo, 6 = sábado)
    primeiro_dia_semana = (primeiro_dia_semana + 1) % 7
    
    # Obtém o último dia do mês anterior
    if mes_atual == 1:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
    else:
        mes_anterior = mes_atual - 1
        ano_anterior = ano_atual
    
    ultimo_dia_mes_anterior = date(ano_anterior, mes_anterior, monthrange(ano_anterior, mes_anterior)[1])
    
    # Obtém o primeiro dia do mês seguinte
    if mes_atual == 12:
        mes_seguinte = 1
        ano_seguinte = ano_atual + 1
    else:
        mes_seguinte = mes_atual + 1
        ano_seguinte = ano_atual
    
    primeiro_dia_mes_seguinte = date(ano_seguinte, mes_seguinte, 1)
    
    # Cria a matriz do calendário
    calendario_matriz = []
    
    # Adiciona os dias do mês anterior
    semana_atual = []
    for i in range(primeiro_dia_semana):
        dia = ultimo_dia_mes_anterior.day - primeiro_dia_semana + i + 1
        data = date(ano_anterior, mes_anterior, dia)
        semana_atual.append({
            'dia': dia,
            'mes': mes_anterior,
            'ano': ano_anterior,
            'data': data,
            'atual': False,
            'feriado': None,
            'registro': None
        })
    
    # Adiciona os dias do mês atual
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano_atual, mes_atual, dia)
        
        # Se a semana atual já tem 7 dias, adiciona à matriz e começa uma nova semana
        if len(semana_atual) == 7:
            calendario_matriz.append(semana_atual)
            semana_atual = []
        
        # Verifica se há registro para este dia
        registro = registros_dict.get(data)
        
        # Verifica se é feriado
        feriado = feriados_dict.get(data)
        
        semana_atual.append({
            'dia': dia,
            'mes': mes_atual,
            'ano': ano_atual,
            'data': data,
            'atual': True,
            'feriado': feriado,
            'registro': registro
        })
    
    # Adiciona os dias do mês seguinte
    dias_restantes = 7 - len(semana_atual)
    for dia in range(1, dias_restantes + 1):
        data = date(ano_seguinte, mes_seguinte, dia)
        semana_atual.append({
            'dia': dia,
            'mes': mes_seguinte,
            'ano': ano_seguinte,
            'data': data,
            'atual': False,
            'feriado': None,
            'registro': None
        })
    
    # Adiciona a última semana à matriz
    calendario_matriz.append(semana_atual)
    
    # Se a matriz não tem 6 semanas, adiciona mais uma
    if len(calendario_matriz) < 6:
        semana_atual = []
        for dia in range(dias_restantes + 1, dias_restantes + 8):
            if dia <= monthrange(ano_seguinte, mes_seguinte)[1]:
                data = date(ano_seguinte, mes_seguinte, dia)
                semana_atual.append({
                    'dia': dia,
                    'mes': mes_seguinte,
                    'ano': ano_seguinte,
                    'data': data,
                    'atual': False,
                    'feriado': None,
                    'registro': None
                })
            else:
                # Se ultrapassar o último dia do mês seguinte, adiciona dias do mês subsequente
                if mes_seguinte == 12:
                    mes_subsequente = 1
                    ano_subsequente = ano_seguinte + 1
                else:
                    mes_subsequente = mes_seguinte + 1
                    ano_subsequente = ano_seguinte
                
                dia_subsequente = dia - monthrange(ano_seguinte, mes_seguinte)[1]
                data = date(ano_subsequente, mes_subsequente, dia_subsequente)
                semana_atual.append({
                    'dia': dia_subsequente,
                    'mes': mes_subsequente,
                    'ano': ano_subsequente,
                    'data': data,
                    'atual': False,
                    'feriado': None,
                    'registro': None
                })
        
        calendario_matriz.append(semana_atual)
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # CORREÇÃO: Melhorar o cálculo de dias úteis para excluir feriados e afastamentos
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Cria um dicionário de afastamentos para fácil acesso
    afastamentos_dict = {}
    for registro in registros:
        if registro.afastamento:
            afastamentos_dict[registro.data] = registro.tipo_afastamento
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta)
        if data_atual.weekday() < 5:
            # Verifica se não é feriado e não é dia de afastamento
            if data_atual not in feriados_dict and data_atual not in afastamentos_dict:
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
    
    # CORREÇÃO: Corrigir o cálculo da carga horária devida (8h por dia útil)
    # Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # CORREÇÃO: Adicionar cálculo da média diária de horas trabalhadas
    media_diaria = 0
    if dias_trabalhados > 0:
        media_diaria = horas_trabalhadas / dias_trabalhados
    
    return render_template('main/calendario.html',
                          usuario=usuario,
                          calendario=calendario_matriz,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas,
                          media_diaria=media_diaria)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Rota para registrar ponto."""
    form = RegistroPontoForm()
    
    # Se uma data for fornecida via GET, preenche o formulário
    data_str = request.args.get('data')
    if data_str:
        try:
            # CORREÇÃO DEFINITIVA: Armazenar a data original como string e converter para date
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            form.data.data = data_selecionada
            form.data_original.data = data_str
            logger.info(f"Data original armazenada via GET: {data_str}")
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    else:
        # CORREÇÃO DEFINITIVA: Não preencher automaticamente com a data atual
        # Deixar o campo vazio para forçar o usuário a selecionar uma data
        form.data_original.data = ""
        logger.info("Nenhuma data fornecida via GET, campo deixado vazio")
    
    if form.validate_on_submit():
        # CORREÇÃO DEFINITIVA: Usar a data original do formulário se disponível
        data_selecionada = None
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                logger.warning(f"Erro ao converter data original: {form.data_original.data}")
                data_selecionada = None
        
        # Se não conseguiu usar a data original, usa a data do campo normal
        if data_selecionada is None:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        logger.info(f"Registrando ponto para a data: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Por favor, edite o registro existente.', 'warning')
            return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
        
        # Cria um novo registro com a data selecionada
        novo_registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada,  # CORREÇÃO DEFINITIVA: Usar a data selecionada
            entrada=form.entrada.data
        )
        
        # Adiciona observações se o campo existir no formulário
        if hasattr(form, 'observacoes'):
            novo_registro.observacoes = form.observacoes.data
        
        # Calcula as horas trabalhadas
        novo_registro.calcular_horas_trabalhadas()
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        flash(f'Registro de ponto realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_ponto.html', form=form)

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Rota para registrar ponto com múltiplos campos."""
    form = RegistroMultiploPontoForm()
    
    # Se uma data for fornecida via GET, preenche o formulário
    data_str = request.args.get('data')
    if data_str:
        try:
            # CORREÇÃO DEFINITIVA: Armazenar a data original como string e converter para date
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            form.data.data = data_selecionada
            form.data_original.data = data_str
            logger.info(f"Data original armazenada via GET: {data_str}")
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    else:
        # CORREÇÃO DEFINITIVA: Não preencher automaticamente com a data atual
        # Deixar o campo vazio para forçar o usuário a selecionar uma data
        form.data_original.data = ""
        logger.info("Nenhuma data fornecida via GET, campo deixado vazio")
    
    if form.validate_on_submit():
        # CORREÇÃO DEFINITIVA: Usar a data original do formulário se disponível
        data_selecionada = None
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                logger.warning(f"Erro ao converter data original: {form.data_original.data}")
                data_selecionada = None
        
        # Se não conseguiu usar a data original, usa a data do campo normal
        if data_selecionada is None:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        logger.info(f"Registrando ponto para a data: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Por favor, edite o registro existente.', 'warning')
            return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))
        
        # Cria um novo registro com a data selecionada
        novo_registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada,  # CORREÇÃO DEFINITIVA: Usar a data selecionada
            afastamento=form.afastamento.data,
            observacoes=form.observacoes.data
        )
        
        # Verifica se é um registro de afastamento
        if form.afastamento.data:
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
        if form.atividades.data:
            from app.models.ponto import Atividade
            atividade = Atividade(
                ponto_id=novo_registro.id,
                descricao=form.atividades.data
            )
            db.session.add(atividade)
            db.session.commit()
            logger.info(f"Atividade registrada para o ponto {novo_registro.id}")
        
        flash(f'Registro de ponto realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_multiplo_ponto.html', form=form)

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    """Rota para visualizar um registro de ponto."""
    # Obtém o registro de ponto
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para visualizar este registro
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém as atividades relacionadas a este ponto
    atividades = ponto.atividades
    
    # CORREÇÃO: Buscar o usuário real do banco de dados em vez de usar o proxy
    usuario = User.query.get(ponto.user_id)
    
    return render_template('main/visualizar_ponto.html', ponto=ponto, atividades=atividades, usuario=usuario)

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Rota para editar um registro de ponto."""
    # Obtém o registro de ponto
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para editar este registro
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Cria o formulário e preenche com os dados do registro
    form = EditarPontoForm(obj=ponto)
    
    # CORREÇÃO DEFINITIVA: Armazenar a data original como string
    form.data_original.data = ponto.data.strftime('%Y-%m-%d')
    logger.info(f"Data original armazenada: {form.data_original.data}")
    
    if form.validate_on_submit():
        # CORREÇÃO DEFINITIVA: Usar a data original do formulário se disponível
        data_selecionada = None
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                logger.warning(f"Erro ao converter data original: {form.data_original.data}")
                data_selecionada = None
        
        # Se não conseguiu usar a data original, usa a data do campo normal
        if data_selecionada is None:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        logger.info(f"Atualizando ponto para a data: {data_selecionada}")
        
        # Verifica se a data foi alterada e se já existe um registro para a nova data
        if data_selecionada != ponto.data:
            registro_existente = Ponto.query.filter_by(
                user_id=ponto.user_id,
                data=data_selecionada
            ).first()
            
            if registro_existente and registro_existente.id != ponto.id:
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Por favor, escolha outra data.', 'danger')
                return render_template('main/editar_ponto.html', form=form, ponto=ponto)
        
        # Atualiza os dados do registro
        ponto.data = data_selecionada  # CORREÇÃO DEFINITIVA: Usar a data selecionada
        ponto.afastamento = form.afastamento.data
        ponto.observacoes = form.observacoes.data
        
        # Verifica se é um registro de afastamento
        if form.afastamento.data:
            ponto.tipo_afastamento = form.tipo_afastamento.data
            # Limpa os horários se for afastamento
            ponto.entrada = None
            ponto.saida_almoco = None
            ponto.retorno_almoco = None
            ponto.saida = None
            ponto.horas_trabalhadas = 0
        else:
            # Limpa o tipo de afastamento
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
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash(f'Registro de ponto atualizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto.id))
    
    # Preenche os campos de horário no formato HH:MM
    if ponto.entrada:
        form.entrada.data = ponto.entrada.strftime('%H:%M')
    
    if ponto.saida_almoco:
        form.saida_almoco.data = ponto.saida_almoco.strftime('%H:%M')
    
    if ponto.retorno_almoco:
        form.retorno_almoco.data = ponto.retorno_almoco.strftime('%H:%M')
    
    if ponto.saida:
        form.saida.data = ponto.saida.strftime('%H:%M')
    
    return render_template('main/editar_ponto.html', form=form, ponto=ponto)

@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    """Rota para registrar uma atividade para um ponto."""
    # Obtém o registro de ponto
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para registrar atividades para este ponto
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para registrar atividades para este ponto.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Cria o formulário
    form = AtividadeForm()
    
    if form.validate_on_submit():
        # Cria uma nova atividade
        from app.models.ponto import Atividade
        atividade = Atividade(
            ponto_id=ponto.id,
            descricao=form.descricao.data
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(atividade)
        db.session.commit()
        
        flash('Atividade registrada com sucesso!', 'success')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto.id))
    
    return render_template('main/registrar_atividade.html', form=form, ponto=ponto)

@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Rota para o relatório mensal de ponto."""
    # Obtém o ID do usuário da query string (para admins visualizarem outros usuários)
    user_id = request.args.get('user_id', type=int)
    
    # Se for admin e um ID de usuário for fornecido, obtém o usuário correspondente
    if current_user.is_admin and user_id:
        usuario = User.query.get_or_404(user_id)
    else:
        usuario = current_user
    
    # Obtém o mês e ano da query string
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
        Ponto.user_id == usuario.id,
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
    
    # CORREÇÃO: Melhorar o cálculo de dias úteis para excluir feriados e afastamentos
    dias_uteis = 0
    dias_trabalhados = 0
    dias_afastamento = 0
    horas_trabalhadas = 0
    
    # Cria um dicionário de afastamentos para fácil acesso
    afastamentos_dict = {}
    for registro in registros:
        if registro.afastamento:
            afastamentos_dict[registro.data] = registro.tipo_afastamento
    
    # Itera pelos dias do mês
    for dia in range(1, ultimo_dia.day + 1):
        data_atual = date(ano_atual, mes_atual, dia)
        
        # Verifica se é dia útil (segunda a sexta)
        if data_atual.weekday() < 5:
            # Verifica se não é feriado e não é dia de afastamento
            if data_atual not in feriados_dict and data_atual not in afastamentos_dict:
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
    
    # CORREÇÃO: Corrigir o cálculo da carga horária devida (8h por dia útil)
    # Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # CORREÇÃO: Adicionar cálculo da média diária de horas trabalhadas
    media_diaria = 0
    if dias_trabalhados > 0:
        media_diaria = horas_trabalhadas / dias_trabalhados
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('main/relatorio_mensal.html',
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
                          media_diaria=media_diaria,
                          feriados_dict=feriados_dict)

# CORREÇÃO: Adicionando a rota excluir_ponto que estava faltando
@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """Rota para excluir um registro de ponto."""
    # Obtém o registro de ponto
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o usuário tem permissão para excluir este registro
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Armazena a data para exibir na mensagem
    data_formatada = ponto.data.strftime('%d/%m/%Y')
    
    # Exclui o registro
    from app import db
    db.session.delete(ponto)
    db.session.commit()
    
    flash(f'Registro de ponto para {data_formatada} excluído com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))
