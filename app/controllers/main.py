from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

@main.route('/')
@login_required
def index():
    """Rota para a página inicial."""
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    """Rota para o dashboard do usuário."""
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
    
    # CORREÇÃO: Adicionar suporte para visualização de outros usuários por administradores
    user_id = request.args.get('user_id', type=int)
    if current_user.is_admin and user_id:
        usuario = User.query.get(user_id)
        if not usuario:
            usuario = current_user
    else:
        usuario = current_user
    
    # Obtém a lista de usuários para administradores
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.all()
    
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
                          feriados_dict=feriados_dict,
                          usuario=usuario,
                          usuarios=usuarios)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Rota para registrar ponto."""
    form = RegistroPontoForm()
    
    if form.validate_on_submit():
        # CORREÇÃO: Usar a data do formulário em vez da data atual
        data_selecionada = form.data.data
        logger.info(f"Data selecionada no formulário: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash('Já existe um registro para esta data.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        # Calcula as horas trabalhadas
        horas_trabalhadas = None
        if form.entrada.data and form.saida.data:
            entrada = datetime.combine(data_selecionada, form.entrada.data)
            saida = datetime.combine(data_selecionada, form.saida.data)
            
            # Se a saída for antes da entrada, assume que é do dia seguinte
            if saida < entrada:
                saida = saida + timedelta(days=1)
            
            # Calcula a diferença em horas
            diferenca = saida - entrada
            horas_trabalhadas = diferenca.total_seconds() / 3600
            
            # Se houver almoço, subtrai o tempo de almoço
            if form.saida_almoco.data and form.retorno_almoco.data:
                saida_almoco = datetime.combine(data_selecionada, form.saida_almoco.data)
                retorno_almoco = datetime.combine(data_selecionada, form.retorno_almoco.data)
                
                # Se o retorno for antes da saída, assume que é do dia seguinte
                if retorno_almoco < saida_almoco:
                    retorno_almoco = retorno_almoco + timedelta(days=1)
                
                # Calcula a diferença em horas
                diferenca_almoco = retorno_almoco - saida_almoco
                horas_trabalhadas -= diferenca_almoco.total_seconds() / 3600
        
        # CORREÇÃO: Não passar o campo atividades diretamente ao criar o registro
        # O campo atividades é um relacionamento, não um campo direto
        registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada,
            entrada=form.entrada.data,
            saida_almoco=form.saida_almoco.data,
            retorno_almoco=form.retorno_almoco.data,
            saida=form.saida.data,
            horas_trabalhadas=horas_trabalhadas,
            afastamento=False,  # Garante que o campo afastamento seja definido
            tipo_afastamento=None,  # Garante que o campo tipo_afastamento seja definido como None
            observacoes=form.observacoes.data if hasattr(form, 'observacoes') else None
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(registro)
        db.session.commit()
        
        # CORREÇÃO: Adicionar a atividade separadamente após criar o registro
        if hasattr(form, 'atividades') and form.atividades.data:
            atividade = Atividade(
                ponto_id=registro.id,
                descricao=form.atividades.data
            )
            db.session.add(atividade)
            db.session.commit()
        
        flash('Registro de ponto criado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_ponto.html', form=form)

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Rota para editar um registro de ponto."""
    # Obtém o registro de ponto
    registro = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o registro pertence ao usuário atual
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Cria o formulário e preenche com os dados do registro
    form = EditarPontoForm(obj=registro)
    
    if form.validate_on_submit():
        # CORREÇÃO: Usar a data do formulário em vez da data atual
        data_selecionada = form.data.data
        logger.info(f"Data selecionada no formulário de edição: {data_selecionada}")
        
        # Atualiza os dados do registro
        registro.data = data_selecionada
        registro.entrada = form.entrada.data
        registro.saida_almoco = form.saida_almoco.data
        registro.retorno_almoco = form.retorno_almoco.data
        registro.saida = form.saida.data
        
        # CORREÇÃO: Atualizar observações se o campo existir
        if hasattr(form, 'observacoes'):
            registro.observacoes = form.observacoes.data
        
        # Calcula as horas trabalhadas
        if form.entrada.data and form.saida.data:
            entrada = datetime.combine(data_selecionada, form.entrada.data)
            saida = datetime.combine(data_selecionada, form.saida.data)
            
            # Se a saída for antes da entrada, assume que é do dia seguinte
            if saida < entrada:
                saida = saida + timedelta(days=1)
            
            # Calcula a diferença em horas
            diferenca = saida - entrada
            registro.horas_trabalhadas = diferenca.total_seconds() / 3600
            
            # Se houver almoço, subtrai o tempo de almoço
            if form.saida_almoco.data and form.retorno_almoco.data:
                saida_almoco = datetime.combine(data_selecionada, form.saida_almoco.data)
                retorno_almoco = datetime.combine(data_selecionada, form.retorno_almoco.data)
                
                # Se o retorno for antes da saída, assume que é do dia seguinte
                if retorno_almoco < saida_almoco:
                    retorno_almoco = retorno_almoco + timedelta(days=1)
                
                # Calcula a diferença em horas
                diferenca_almoco = retorno_almoco - saida_almoco
                registro.horas_trabalhadas -= diferenca_almoco.total_seconds() / 3600
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        # CORREÇÃO: Atualizar a atividade separadamente
        if hasattr(form, 'atividades') and form.atividades.data:
            # Verifica se já existe uma atividade para este registro
            atividade = Atividade.query.filter_by(ponto_id=registro.id).first()
            
            if atividade:
                # Atualiza a atividade existente
                atividade.descricao = form.atividades.data
            else:
                # Cria uma nova atividade
                atividade = Atividade(
                    ponto_id=registro.id,
                    descricao=form.atividades.data
                )
                db.session.add(atividade)
            
            db.session.commit()
        
        flash('Registro de ponto atualizado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/editar_ponto.html', form=form, registro=registro)

# CORREÇÃO: Modificar para permitir registro de diferentes tipos de afastamento
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    """Rota para registrar afastamento (férias, licença, etc.)."""
    form = RegistroAfastamentoForm()
    
    if form.validate_on_submit():
        # CORREÇÃO: Usar a data do formulário em vez da data atual
        data_selecionada = form.data.data
        logger.info(f"Data selecionada no formulário de afastamento: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if registro_existente:
            flash('Já existe um registro para esta data.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        # Cria um novo registro de afastamento
        registro = Ponto(
            user_id=current_user.id,
            data=data_selecionada,
            afastamento=True,
            tipo_afastamento=form.tipo_afastamento.data,
            entrada=None,
            saida_almoco=None,
            retorno_almoco=None,
            saida=None,
            horas_trabalhadas=None,
            observacoes=None
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(registro)
        db.session.commit()
        
        flash('Registro de afastamento criado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_afastamento.html', form=form)

# Mantém a rota de férias para compatibilidade com código existente
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required
def registrar_ferias():
    """Rota para registrar férias (redirecionamento para compatibilidade)."""
    return redirect(url_for('main.registrar_afastamento'))

@main.route('/calendario')
@login_required
def calendario():
    """Rota para o calendário do usuário."""
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
    
    # CORREÇÃO: Adicionar suporte para visualização de outros usuários por administradores
    user_id = request.args.get('user_id', type=int)
    if current_user.is_admin and user_id:
        usuario = User.query.get(user_id)
        if not usuario:
            usuario = current_user
    else:
        usuario = current_user
    
    # Obtém a lista de usuários para administradores
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.all()
    
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
    
    # CORREÇÃO: Criar lista de datas de feriados para o template
    feriados_datas = list(feriados_dict.keys())
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # Obtém o dia da semana do primeiro dia do mês (0 = segunda, 6 = domingo)
    dia_semana_primeiro = primeiro_dia.weekday()
    
    # Ajusta para que domingo seja 0 e sábado seja 6
    dia_semana_primeiro = (dia_semana_primeiro + 1) % 7
    
    # Obtém o último dia do mês anterior
    if mes_atual == 1:
        ultimo_dia_mes_anterior = date(ano_atual - 1, 12, 31)
    else:
        ultimo_dia_mes_anterior = date(ano_atual, mes_atual - 1, monthrange(ano_atual, mes_atual - 1)[1])
    
    # Obtém o primeiro dia do mês seguinte
    if mes_atual == 12:
        primeiro_dia_mes_seguinte = date(ano_atual + 1, 1, 1)
    else:
        primeiro_dia_mes_seguinte = date(ano_atual, mes_atual + 1, 1)
    
    # Cria a matriz do calendário
    calendario_matriz = []
    
    # Adiciona os dias do mês anterior
    semana_atual = []
    for i in range(dia_semana_primeiro):
        dia = ultimo_dia_mes_anterior.day - dia_semana_primeiro + i + 1
        data = date(ultimo_dia_mes_anterior.year, ultimo_dia_mes_anterior.month, dia)
        semana_atual.append({
            'dia': dia,
            'mes': 'anterior',
            'data': data,
            'registro': None,
            'feriado': feriados_dict.get(data)
        })
    
    # Adiciona os dias do mês atual
    for dia in range(1, ultimo_dia.day + 1):
        data = date(ano_atual, mes_atual, dia)
        if len(semana_atual) == 7:
            calendario_matriz.append(semana_atual)
            semana_atual = []
        semana_atual.append({
            'dia': dia,
            'mes': 'atual',
            'data': data,
            'registro': registros_dict.get(data),
            'feriado': feriados_dict.get(data)
        })
    
    # Adiciona os dias do mês seguinte
    dias_restantes = 7 - len(semana_atual)
    for dia in range(1, dias_restantes + 1):
        data = date(primeiro_dia_mes_seguinte.year, primeiro_dia_mes_seguinte.month, dia)
        semana_atual.append({
            'dia': dia,
            'mes': 'seguinte',
            'data': data,
            'registro': None,
            'feriado': feriados_dict.get(data)
        })
    
    # Adiciona a última semana
    calendario_matriz.append(semana_atual)
    
    # Obtém o mês anterior e o próximo mês para navegação
    if mes_atual == 1:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
    else:
        mes_anterior = mes_atual - 1
        ano_anterior = ano_atual
    
    if mes_atual == 12:
        proximo_mes = 1
        proximo_ano = ano_atual + 1
    else:
        proximo_mes = mes_atual + 1
        proximo_ano = ano_atual
    
    # CORREÇÃO: Passar as classes date e timedelta para o template
    return render_template('main/calendario.html',
                          calendario=calendario_matriz,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          mes_anterior=mes_anterior,
                          ano_anterior=ano_anterior,
                          proximo_mes=proximo_mes,
                          proximo_ano=proximo_ano,
                          primeiro_dia=primeiro_dia,
                          ultimo_dia=ultimo_dia,
                          registros_dict=registros_dict,
                          feriados_dict=feriados_dict,
                          feriados_datas=feriados_datas,
                          usuario=usuario,
                          usuarios=usuarios,
                          date=date,
                          timedelta=timedelta)

@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Rota para o relatório mensal do usuário."""
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
    
    # CORREÇÃO: Adicionar suporte para visualização de outros usuários por administradores
    user_id = request.args.get('user_id', type=int)
    if current_user.is_admin and user_id:
        usuario = User.query.get(user_id)
        if not usuario:
            usuario = current_user
    else:
        usuario = current_user
    
    # Obtém a lista de usuários para administradores
    usuarios = None
    if current_user.is_admin:
        usuarios = User.query.all()
    
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
    
    # Obtém o mês anterior e o próximo mês para navegação
    if mes_atual == 1:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
    else:
        mes_anterior = mes_atual - 1
        ano_anterior = ano_atual
    
    if mes_atual == 12:
        proximo_mes = 1
        proximo_ano = ano_atual + 1
    else:
        proximo_mes = mes_atual + 1
        proximo_ano = ano_atual
    
    return render_template('main/relatorio_mensal.html',
                          registros=registros,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual,
                          nome_mes=nome_mes,
                          mes_anterior=mes_anterior,
                          ano_anterior=ano_anterior,
                          proximo_mes=proximo_mes,
                          proximo_ano=proximo_ano,
                          dias_uteis=dias_uteis,
                          dias_trabalhados=dias_trabalhados,
                          dias_afastamento=dias_afastamento,
                          horas_trabalhadas=horas_trabalhadas,
                          carga_horaria_devida=carga_horaria_devida,
                          saldo_horas=saldo_horas,
                          media_diaria=media_diaria,
                          feriados_dict=feriados_dict,
                          usuario=usuario,
                          usuarios=usuarios)

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    """Rota para visualizar um registro de ponto."""
    # Obtém o registro de ponto
    registro = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o registro pertence ao usuário atual
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário do registro
    usuario = User.query.get(registro.user_id)
    
    return render_template('main/visualizar_ponto.html', registro=registro, usuario=usuario)

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """Rota para excluir um registro de ponto."""
    # Obtém o registro de ponto
    registro = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o registro pertence ao usuário atual
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Exclui o registro
    from app import db
    db.session.delete(registro)
    db.session.commit()
    
    flash('Registro de ponto excluído com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/perfil', methods=['GET'])
@login_required
def perfil():
    """Rota para o perfil do usuário."""
    # CORREÇÃO: Buscar o usuário real do banco de dados em vez de usar o proxy
    usuario = User.query.get(current_user.id)
    
    return render_template('main/perfil.html', usuario=usuario)

# CORREÇÃO: Adicionar a rota para registrar múltiplos pontos
@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Rota para registrar múltiplos pontos de uma vez."""
    if request.method == 'POST':
        # Obtém os dados do formulário
        datas = request.form.getlist('datas[]')
        entradas = request.form.getlist('entradas[]')
        saidas_almoco = request.form.getlist('saidas_almoco[]')
        retornos_almoco = request.form.getlist('retornos_almoco[]')
        saidas = request.form.getlist('saidas[]')
        observacoes = request.form.getlist('observacoes[]')
        
        # Verifica se há datas para registrar
        if not datas:
            flash('Nenhuma data foi informada.', 'danger')
            return redirect(url_for('main.registrar_multiplo_ponto'))
        
        # Contador de registros criados
        registros_criados = 0
        
        # Processa cada data
        for i in range(len(datas)):
            # Verifica se a data está preenchida
            if not datas[i]:
                continue
            
            # Converte a data para o formato correto
            try:
                data_str = datas[i]
                data_partes = data_str.split('-')
                data = date(int(data_partes[0]), int(data_partes[1]), int(data_partes[2]))
            except (ValueError, IndexError):
                flash(f'Data inválida: {datas[i]}', 'danger')
                continue
            
            # Verifica se já existe um registro para esta data
            registro_existente = Ponto.query.filter_by(
                user_id=current_user.id,
                data=data
            ).first()
            
            if registro_existente:
                flash(f'Já existe um registro para a data {data.strftime("%d/%m/%Y")}.', 'warning')
                continue
            
            # Obtém os valores para este índice
            entrada = entradas[i] if i < len(entradas) else None
            saida_almoco = saidas_almoco[i] if i < len(saidas_almoco) else None
            retorno_almoco = retornos_almoco[i] if i < len(retornos_almoco) else None
            saida = saidas[i] if i < len(saidas) else None
            observacao = observacoes[i] if i < len(observacoes) else None
            
            # Converte os horários para o formato correto
            try:
                entrada_time = datetime.strptime(entrada, '%H:%M').time() if entrada else None
                saida_almoco_time = datetime.strptime(saida_almoco, '%H:%M').time() if saida_almoco else None
                retorno_almoco_time = datetime.strptime(retorno_almoco, '%H:%M').time() if retorno_almoco else None
                saida_time = datetime.strptime(saida, '%H:%M').time() if saida else None
            except ValueError:
                flash(f'Horário inválido para a data {data.strftime("%d/%m/%Y")}.', 'danger')
                continue
            
            # Calcula as horas trabalhadas
            horas_trabalhadas = None
            if entrada_time and saida_time:
                entrada_dt = datetime.combine(data, entrada_time)
                saida_dt = datetime.combine(data, saida_time)
                
                # Se a saída for antes da entrada, assume que é do dia seguinte
                if saida_dt < entrada_dt:
                    saida_dt = saida_dt + timedelta(days=1)
                
                # Calcula a diferença em horas
                diferenca = saida_dt - entrada_dt
                horas_trabalhadas = diferenca.total_seconds() / 3600
                
                # Se houver almoço, subtrai o tempo de almoço
                if saida_almoco_time and retorno_almoco_time:
                    saida_almoco_dt = datetime.combine(data, saida_almoco_time)
                    retorno_almoco_dt = datetime.combine(data, retorno_almoco_time)
                    
                    # Se o retorno for antes da saída, assume que é do dia seguinte
                    if retorno_almoco_dt < saida_almoco_dt:
                        retorno_almoco_dt = retorno_almoco_dt + timedelta(days=1)
                    
                    # Calcula a diferença em horas
                    diferenca_almoco = retorno_almoco_dt - saida_almoco_dt
                    horas_trabalhadas -= diferenca_almoco.total_seconds() / 3600
            
            # Cria um novo registro de ponto
            registro = Ponto(
                user_id=current_user.id,
                data=data,
                entrada=entrada_time,
                saida_almoco=saida_almoco_time,
                retorno_almoco=retorno_almoco_time,
                saida=saida_time,
                horas_trabalhadas=horas_trabalhadas,
                observacoes=observacao,
                afastamento=False,  # CORREÇÃO: Garantir que o campo afastamento seja definido
                tipo_afastamento=None  # CORREÇÃO: Garantir que o campo tipo_afastamento seja definido como None
            )
            
            # Salva no banco de dados
            from app import db
            db.session.add(registro)
            db.session.commit()
            
            registros_criados += 1
        
        if registros_criados > 0:
            flash(f'{registros_criados} registro(s) de ponto criado(s) com sucesso!', 'success')
        else:
            flash('Nenhum registro de ponto foi criado.', 'warning')
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/registrar_multiplo_ponto.html')
