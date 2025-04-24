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
    
    if form.validate_on_submit():
        hoje = date.today()
        
        # Verifica se já existe um registro para hoje
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
    else:
        # Preenche com a data atual se não for fornecida
        form.data.data = datetime.now().date()
    
    if form.validate_on_submit():
        data_selecionada = form.data.data
        
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
        
        # Registra a atividade se o campo estiver preenchido
        if hasattr(form, 'atividades') and form.atividades.data:
            atividade = Atividade(
                ponto_id=novo_registro.id,
                descricao=form.atividades.data
            )
            db.session.add(atividade)
            db.session.commit()
            logger.info(f"Atividade registrada para o ponto {novo_registro.id}")
        
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
    
    # Obtém as atividades relacionadas a este ponto
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    
    return render_template('main/visualizar_ponto.html', ponto=ponto, atividades=atividades)

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
        form.afastamento.data = ponto.afastamento
        
        if ponto.afastamento:
            form.tipo_afastamento.data = ponto.tipo_afastamento
        else:
            if ponto.entrada:
                form.entrada.data = ponto.entrada.strftime('%H:%M')
            if ponto.saida_almoco:
                form.saida_almoco.data = ponto.saida_almoco.strftime('%H:%M')
            if ponto.retorno_almoco:
                form.retorno_almoco.data = ponto.retorno_almoco.strftime('%H:%M')
            if ponto.saida:
                form.saida.data = ponto.saida.strftime('%H:%M')
        
        if hasattr(form, 'observacoes'):
            form.observacoes.data = ponto.observacoes
    
    if form.validate_on_submit():
        # Atualiza os dados do ponto
        ponto.data = form.data.data
        ponto.afastamento = form.afastamento.data
        
        if ponto.afastamento:
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
            
            # Atualiza os horários
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
            
            # Recalcula as horas trabalhadas
            ponto.calcular_horas_trabalhadas()
        
        # Atualiza as observações se o campo existir
        if hasattr(form, 'observacoes'):
            ponto.observacoes = form.observacoes.data
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash('Registro de ponto atualizado com sucesso!', 'success')
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
    
    # Verifica se foi solicitado um formato de exportação
    formato = request.args.get('formato')
    if formato:
        if formato == 'pdf':
            # Gera o PDF
            pdf_path = generate_pdf(usuario, registros, mes_atual, ano_atual, nome_mes, dias_uteis, 
                                   dias_trabalhados, dias_afastamento, horas_trabalhadas, 
                                   carga_horaria_devida, saldo_horas, feriados_dict)
            
            # Retorna o arquivo para download
            return send_file(pdf_path, as_attachment=True, download_name=f'relatorio_{usuario.name}_{mes_atual}_{ano_atual}.pdf')
        
        elif formato == 'excel':
            # Gera o Excel
            excel_path = generate_excel(usuario, registros, mes_atual, ano_atual, nome_mes, dias_uteis, 
                                      dias_trabalhados, dias_afastamento, horas_trabalhadas, 
                                      carga_horaria_devida, saldo_horas, feriados_dict)
            
            # Retorna o arquivo para download
            return send_file(excel_path, as_attachment=True, download_name=f'relatorio_{usuario.name}_{mes_atual}_{ano_atual}.xlsx')
    
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
                          feriados_dict=feriados_dict,
                          usuarios=usuarios)

@main.route('/exportar-relatorio/<int:user_id>/<int:mes>/<int:ano>/<formato>')
@login_required
def exportar_relatorio(user_id, mes, ano, formato):
    # Verifica se o usuário tem permissão para exportar este relatório
    if user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para exportar o relatório de outros usuários.', 'danger')
        return redirect(url_for('main.relatorio_mensal'))
    
    # Redireciona para a página de relatório com os parâmetros de exportação
    return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano, formato=formato))
