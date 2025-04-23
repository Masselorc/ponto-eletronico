from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.ponto import Ponto, Atividade, Feriado
from app.models.user import User
from app import db
from app.forms.ponto import RegistroPontoForm, AtividadeForm, RegistroMultiploPontoForm
from datetime import datetime, timedelta, date
import logging

# Configurar logging
logger = logging.getLogger(__name__)

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
    
    # Obtém registros do mês atual
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Obtém o primeiro e último dia do mês
    primeiro_dia = date(ano_atual, mes_atual, 1)
    if mes_atual == 12:
        ultimo_dia = date(ano_atual + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano_atual, mes_atual + 1, 1) - timedelta(days=1)
    
    registros_mes = Ponto.query.filter(
        Ponto.user_id == current_user.id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).order_by(Ponto.data.desc()).all()
    
    # Nomes dos meses em português
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('main/dashboard.html', 
                          registro_hoje=registro_hoje,
                          registros_mes=registros_mes,
                          hoje=hoje,
                          nome_mes=nome_mes,
                          ano_atual=ano_atual)

@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    # Redireciona para a nova rota de registro de ponto
    return redirect(url_for('main.registrar_multiplo_ponto'))

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    form = RegistroMultiploPontoForm()
    hoje = datetime.now().date()
    
    if request.method == 'POST':
        data_selecionada = request.form.get('data')
        if not data_selecionada:
            flash('A data é obrigatória.', 'danger')
            return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
        
        try:
            data_selecionada = datetime.strptime(data_selecionada, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de data inválido.', 'danger')
            return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
        
        # Verifica se já existe registro para a data selecionada
        registro = Ponto.query.filter_by(
            user_id=current_user.id,
            data=data_selecionada
        ).first()
        
        if not registro:
            registro = Ponto(user_id=current_user.id, data=data_selecionada)
        
        # Log para debug
        logger.info(f"Processando registro para {data_selecionada} - Usuário: {current_user.id}")
        
        # Verifica se é um registro de afastamento - VERIFICAÇÃO RIGOROSA
        afastamento_checkbox = request.form.get('afastamento')
        is_afastamento = afastamento_checkbox is not None and afastamento_checkbox.lower() in ['on', 'true', '1', 'yes']
        
        logger.info(f"Valor do checkbox afastamento: '{afastamento_checkbox}', interpretado como: {is_afastamento}")
        
        if is_afastamento:
            tipo_afastamento = request.form.get('tipo_afastamento')
            
            if not tipo_afastamento:
                flash('O tipo de afastamento é obrigatório quando a opção de afastamento está marcada.', 'danger')
                return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
            
            # Validação rigorosa do tipo de afastamento
            tipos_validos = ['ferias', 'licenca_medica', 'licenca_maternidade', 'abono', 'outro']
            if tipo_afastamento not in tipos_validos:
                flash('Tipo de afastamento inválido.', 'danger')
                return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
            
            # Definição explícita dos campos
            registro.afastamento = True
            registro.tipo_afastamento = tipo_afastamento
            
            # Limpeza explícita dos campos de horário
            registro.entrada = None
            registro.saida_almoco = None
            registro.retorno_almoco = None
            registro.saida = None
            registro.horas_trabalhadas = None
            
            # Log para debug
            logger.info(f"Salvando afastamento: tipo={tipo_afastamento}")
            
            try:
                if not registro.id:
                    db.session.add(registro)
                
                db.session.commit()
                
                # Verificação pós-commit para garantir que os dados foram salvos corretamente
                db.session.refresh(registro)
                if not registro.afastamento or registro.tipo_afastamento != tipo_afastamento:
                    logger.error(f"Verificação pós-commit falhou: afastamento={registro.afastamento}, tipo={registro.tipo_afastamento}")
                    flash('Erro ao salvar afastamento. Por favor, tente novamente.', 'danger')
                    return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
                
                flash(f'Registro de afastamento realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao salvar afastamento: {str(e)}")
                flash(f'Erro ao registrar afastamento: {str(e)}', 'danger')
                return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
        
        # Se não for afastamento, processa como registro normal de ponto
        # Marca explicitamente como não sendo um afastamento
        registro.afastamento = False
        registro.tipo_afastamento = None
        
        campos_atualizados = []
        
        # Processamento dos campos de horário com validação rigorosa
        hora_entrada = request.form.get('hora_entrada')
        hora_saida_almoco = request.form.get('hora_saida_almoco')
        hora_retorno_almoco = request.form.get('hora_retorno_almoco')
        hora_saida = request.form.get('hora_saida')
        
        # Função para validar e converter horário
        def validar_horario(horario_str):
            if not horario_str:
                return None
            try:
                return datetime.strptime(horario_str, '%H:%M').time()
            except ValueError:
                return None
        
        # Validação e atribuição dos horários
        entrada_time = validar_horario(hora_entrada)
        if entrada_time:
            registro.entrada = entrada_time
            campos_atualizados.append('entrada')
        else:
            registro.entrada = None
            
        saida_almoco_time = validar_horario(hora_saida_almoco)
        if saida_almoco_time:
            registro.saida_almoco = saida_almoco_time
            campos_atualizados.append('saída para almoço')
        else:
            registro.saida_almoco = None
            
        retorno_almoco_time = validar_horario(hora_retorno_almoco)
        if retorno_almoco_time:
            registro.retorno_almoco = retorno_almoco_time
            campos_atualizados.append('retorno do almoço')
        else:
            registro.retorno_almoco = None
            
        saida_time = validar_horario(hora_saida)
        if saida_time:
            registro.saida = saida_time
            campos_atualizados.append('saída')
        else:
            registro.saida = None
            
        # Calcula horas trabalhadas com base nos registros disponíveis
        if registro.entrada and registro.saida:
            # Caso 1: Todos os campos preenchidos (com almoço)
            if registro.saida_almoco and registro.retorno_almoco:
                # Tempo antes do almoço
                t1 = datetime.combine(data_selecionada, registro.saida_almoco) - datetime.combine(data_selecionada, registro.entrada)
                
                # Tempo depois do almoço
                t2 = datetime.combine(data_selecionada, registro.saida) - datetime.combine(data_selecionada, registro.retorno_almoco)
                
                # Total de horas trabalhadas
                total_segundos = t1.total_seconds() + t2.total_seconds()
                registro.horas_trabalhadas = total_segundos / 3600  # Converte para horas
            
            # Caso 2: Apenas entrada e saída (sem almoço)
            else:
                # Calcula diretamente da entrada até a saída
                total_segundos = (datetime.combine(data_selecionada, registro.saida) - 
                                 datetime.combine(data_selecionada, registro.entrada)).total_seconds()
                registro.horas_trabalhadas = total_segundos / 3600  # Converte para horas
        else:
            registro.horas_trabalhadas = None
        
        try:
            if not registro.id:
                db.session.add(registro)
            
            db.session.commit()
            
            # Verificação pós-commit para garantir que os dados foram salvos corretamente
            db.session.refresh(registro)
            if registro.afastamento:
                logger.error(f"Verificação pós-commit falhou: registro marcado como afastamento quando deveria ser normal")
                flash('Erro ao salvar registro. Por favor, tente novamente.', 'danger')
                return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
            
            if campos_atualizados:
                flash(f'Registros de {", ".join(campos_atualizados)} realizados com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
            else:
                flash('Nenhum horário foi preenchido. Por favor, informe pelo menos um horário.', 'warning')
                return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
                
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar registro normal: {str(e)}")
            flash(f'Erro ao registrar pontos: {str(e)}', 'danger')
            return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)
    
    return render_template('main/registrar_multiplo_ponto.html', form=form, hoje=hoje)

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Verifica se é um registro de afastamento - VERIFICAÇÃO RIGOROSA
        afastamento_checkbox = request.form.get('afastamento')
        is_afastamento = afastamento_checkbox is not None and afastamento_checkbox.lower() in ['on', 'true', '1', 'yes']
        
        logger.info(f"Edição - Valor do checkbox afastamento: '{afastamento_checkbox}', interpretado como: {is_afastamento}")
        
        if is_afastamento:
            tipo_afastamento = request.form.get('tipo_afastamento')
            
            if not tipo_afastamento:
                flash('O tipo de afastamento é obrigatório quando a opção de afastamento está marcada.', 'danger')
                return render_template('main/editar_ponto.html', ponto=ponto)
            
            # Validação rigorosa do tipo de afastamento
            tipos_validos = ['ferias', 'licenca_medica', 'licenca_maternidade', 'abono', 'outro']
            if tipo_afastamento not in tipos_validos:
                flash('Tipo de afastamento inválido.', 'danger')
                return render_template('main/editar_ponto.html', ponto=ponto)
            
            # Definição explícita dos campos
            ponto.afastamento = True
            ponto.tipo_afastamento = tipo_afastamento
            
            # Limpeza explícita dos campos de horário
            ponto.entrada = None
            ponto.saida_almoco = None
            ponto.retorno_almoco = None
            ponto.saida = None
            ponto.horas_trabalhadas = None
            
            try:
                db.session.commit()
                
                # Verificação pós-commit para garantir que os dados foram salvos corretamente
                db.session.refresh(ponto)
                if not ponto.afastamento or ponto.tipo_afastamento != tipo_afastamento:
                    logger.error(f"Edição - Verificação pós-commit falhou: afastamento={ponto.afastamento}, tipo={ponto.tipo_afastamento}")
                    flash('Erro ao salvar afastamento. Por favor, tente novamente.', 'danger')
                    return render_template('main/editar_ponto.html', ponto=ponto)
                
                flash('Registro de afastamento atualizado com sucesso!', 'success')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Edição - Erro ao salvar afastamento: {str(e)}")
                flash(f'Erro ao atualizar afastamento: {str(e)}', 'danger')
                return render_template('main/editar_ponto.html', ponto=ponto)
        else:
            # Marca explicitamente como não sendo um afastamento
            ponto.afastamento = False
            ponto.tipo_afastamento = None
            
            # Função para validar e converter horário
            def validar_horario(horario_str):
                if not horario_str:
                    return None
                try:
                    return datetime.strptime(horario_str, '%H:%M').time()
                except ValueError:
                    return None
            
            # Processamento dos campos de horário com validação rigorosa
            entrada = request.form.get('entrada')
            saida_almoco = request.form.get('saida_almoco')
            retorno_almoco = request.form.get('retorno_almoco')
            saida = request.form.get('saida')
            
            # Validação e atribuição dos horários
            ponto.entrada = validar_horario(entrada)
            ponto.saida_almoco = validar_horario(saida_almoco)
            ponto.retorno_almoco = validar_horario(retorno_almoco)
            ponto.saida = validar_horario(saida)
            
            # Calcula horas trabalhadas com base nos registros disponíveis
            if ponto.entrada and ponto.saida:
                # Caso 1: Todos os campos preenchidos (com almoço)
                if ponto.saida_almoco and ponto.retorno_almoco:
                    # Tempo antes do almoço
                    t1 = datetime.combine(ponto.data, ponto.saida_almoco) - datetime.combine(ponto.data, ponto.entrada)
                    
                    # Tempo depois do almoço
                    t2 = datetime.combine(ponto.data, ponto.saida) - datetime.combine(ponto.data, ponto.retorno_almoco)
                    
                    # Total de horas trabalhadas
                    total_segundos = t1.total_seconds() + t2.total_seconds()
                    ponto.horas_trabalhadas = total_segundos / 3600  # Converte para horas
                
                # Caso 2: Apenas entrada e saída (sem almoço)
                else:
                    # Calcula diretamente da entrada até a saída
                    total_segundos = (datetime.combine(ponto.data, ponto.saida) - 
                                     datetime.combine(ponto.data, ponto.entrada)).total_seconds()
                    ponto.horas_trabalhadas = total_segundos / 3600  # Converte para horas
            else:
                ponto.horas_trabalhadas = None
            
            try:
                db.session.commit()
                
                # Verificação pós-commit para garantir que os dados foram salvos corretamente
                db.session.refresh(ponto)
                if ponto.afastamento:
                    logger.error(f"Edição - Verificação pós-commit falhou: registro marcado como afastamento quando deveria ser normal")
                    flash('Erro ao salvar registro. Por favor, tente novamente.', 'danger')
                    return render_template('main/editar_ponto.html', ponto=ponto)
                
                flash('Registro de ponto atualizado com sucesso!', 'success')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Edição - Erro ao salvar registro normal: {str(e)}")
                flash(f'Erro ao atualizar registro: {str(e)}', 'danger')
                return render_template('main/editar_ponto.html', ponto=ponto)
    
    return render_template('main/editar_ponto.html', ponto=ponto)

@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        db.session.delete(ponto)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto: {str(e)}")
        flash(f'Erro ao excluir registro: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

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
                          date=date)

@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Verifica se o ponto pertence ao usuário atual ou se é admin
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para acessar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém as atividades relacionadas a este ponto
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    
    return render_template('main/visualizar_ponto.html', ponto=ponto, atividades=atividades)

# Rota para verificar o status de um registro (para debug)
@main.route('/debug/verificar-registro/<int:ponto_id>')
@login_required
def verificar_registro(ponto_id):
    if not current_user.is_admin:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    ponto = Ponto.query.get_or_404(ponto_id)
    
    return jsonify({
        'id': ponto.id,
        'user_id': ponto.user_id,
        'data': ponto.data.strftime('%Y-%m-%d'),
        'afastamento': ponto.afastamento,
        'tipo_afastamento': ponto.tipo_afastamento,
        'entrada': ponto.entrada.strftime('%H:%M') if ponto.entrada else None,
        'saida_almoco': ponto.saida_almoco.strftime('%H:%M') if ponto.saida_almoco else None,
        'retorno_almoco': ponto.retorno_almoco.strftime('%H:%M') if ponto.retorno_almoco else None,
        'saida': ponto.saida.strftime('%H:%M') if ponto.saida else None,
        'horas_trabalhadas': ponto.horas_trabalhadas
    })

# Rota para forçar a atualização de um registro de afastamento (para correção)
@main.route('/admin/corrigir-afastamento/<int:ponto_id>', methods=['GET'])
@login_required
def corrigir_afastamento(ponto_id):
    if not current_user.is_admin:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    ponto = Ponto.query.get_or_404(ponto_id)
    
    # Força a atualização do registro como afastamento
    ponto.afastamento = True
    
    # Garante que o tipo de afastamento seja válido
    if not ponto.tipo_afastamento or ponto.tipo_afastamento not in ['ferias', 'licenca_medica', 'licenca_maternidade', 'abono', 'outro']:
        ponto.tipo_afastamento = 'outro'
    
    # Limpa os campos de horário
    ponto.entrada = None
    ponto.saida_almoco = None
    ponto.retorno_almoco = None
    ponto.saida = None
    ponto.horas_trabalhadas = None
    
    try:
        db.session.commit()
        flash(f'Registro ID {ponto_id} corrigido com sucesso como afastamento.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao corrigir registro: {str(e)}', 'danger')
    
    return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
