# -*- coding: utf-8 -*-
# Importações necessárias
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import calendar
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app import db
from datetime import datetime, date, timedelta, time
import logging
import os
import tempfile
import pandas as pd

# Criação do Blueprint 'main'
main = Blueprint('main', __name__)
# Configuração do logger
logger = logging.getLogger(__name__)

# Função auxiliar para calcular horas trabalhadas
def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    """Calcula as horas trabalhadas em um dia, considerando o almoço."""
    if not entrada or not saida:
        return None  # Retorna None se entrada ou saída não forem fornecidas
    try:
        # Combina a data de referência com os horários para criar datetimes
        entrada_dt = datetime.combine(data_ref, entrada)
        saida_dt = datetime.combine(data_ref, saida)

        # Ajusta a data de saída se ela for no dia seguinte (trabalho noturno)
        if saida_dt < entrada_dt:
            saida_dt += timedelta(days=1)

        # Calcula a diferença total em segundos e converte para horas
        diff_total = saida_dt - entrada_dt
        horas_trabalhadas = diff_total.total_seconds() / 3600

        # Se houver registro de almoço, calcula a duração e subtrai das horas totais
        if saida_almoco and retorno_almoco:
            saida_almoco_dt = datetime.combine(data_ref, saida_almoco)
            retorno_almoco_dt = datetime.combine(data_ref, retorno_almoco)
            # Ajusta a data de retorno do almoço se for no dia seguinte
            if retorno_almoco_dt < saida_almoco_dt:
                retorno_almoco_dt += timedelta(days=1)
            diff_almoco = retorno_almoco_dt - saida_almoco_dt
            horas_trabalhadas -= diff_almoco.total_seconds() / 3600

        # Garante que as horas trabalhadas não sejam negativas
        return max(0, horas_trabalhadas)
    except Exception as e:
        # Loga qualquer erro durante o cálculo
        logger.error(f"Erro ao calcular horas para {data_ref}: {e}", exc_info=True)
        return None # Retorna None em caso de erro

# Função auxiliar para obter o contexto do usuário (usuário logado ou selecionado pelo admin)
def get_usuario_contexto():
    """Obtém o usuário cujo contexto (dashboard, calendário, etc.) está sendo visualizado."""
    user_id_req = request.args.get('user_id', type=int) # Pega user_id da URL, se houver
    usuario_selecionado = current_user # Por padrão, é o usuário logado

    # Se o usuário logado for admin e um user_id foi passado na URL
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req) # Busca o usuário pelo ID
        if usuario_req:
            usuario_selecionado = usuario_req # Define o usuário selecionado como o da URL
        else:
            flash(f"Usuário com ID {user_id_req} não encontrado.", "warning") # Avisa se não encontrar

    # Obtém todos os usuários se o usuário logado for admin (para o seletor)
    usuarios_para_admin = User.query.order_by(User.name).all() if current_user.is_admin else None
    return usuario_selecionado, usuarios_para_admin

# Rota principal, redireciona para o dashboard
@main.route('/')
@login_required # Requer login
def index():
    """Redireciona para o dashboard."""
    return redirect(url_for('main.dashboard'))

# Rota do Dashboard
@main.route('/dashboard')
@login_required # Requer login
def dashboard():
    """Exibe o dashboard com o resumo mensal e registros recentes."""
    try:
        # Obtém o usuário e a lista de usuários (se admin)
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        # Obtém mês e ano da URL, ou usa o mês/ano atual como padrão
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Validação básica de mês
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        # Define o primeiro e último dia do mês solicitado
        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        # Busca os registros de ponto do usuário para o mês/ano selecionado
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data.desc()).all() # Ordena do mais recente para o mais antigo

        # Busca os feriados do mês/ano selecionado
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        # Cria um dicionário e um conjunto para acesso rápido aos feriados
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # Inicializa contadores para as estatísticas do mês
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        # Cria um dicionário de registros para acesso rápido por data
        registros_dict = {r.data: r for r in registros}

        # Calcula dias úteis e dias de afastamento
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            # Verifica se é dia da semana (seg-sex) e não é feriado
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                registro_dia = registros_dict.get(data_atual)
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1 # Conta como afastamento
                else:
                    dias_uteis += 1 # Conta como dia útil

        # Calcula dias trabalhados e horas totais
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None:
                dias_trabalhados += 1
                horas_trabalhadas += r.horas_trabalhadas

        # Calcula carga horária devida e saldo de horas
        carga_horaria_devida = dias_uteis * 8.0 # 8h por dia útil
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        # Calcula média diária de horas
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

        # Obtém nome do mês e calcula mês/ano anterior e próximo para navegação
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        # Renderiza o template do dashboard com os dados calculados
        return render_template(
            'main/dashboard.html',
            registros=registros,
            mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas, media_diaria=media_diaria,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano
        )
    except ValueError:
        # Trata erro se a data for inválida
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        # Loga e trata outros erros
        logger.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
        flash('Erro ao carregar o dashboard. Tente novamente.', 'danger')
        hoje = date.today()
        # Renderiza o template com valores padrão em caso de erro grave
        return render_template(
            'main/dashboard.html',
            registros=[], mes_atual=hoje.month, ano_atual=hoje.year, nome_mes="Mês Atual",
            dias_uteis=0, dias_trabalhados=0, dias_afastamento=0, horas_trabalhadas=0,
            carga_horaria_devida=0, saldo_horas=0, media_diaria=0,
            usuario=current_user, usuarios=None
        )

# Rota para registrar um novo ponto
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required # Requer login
def registrar_ponto():
    """Registra um novo ponto para um dia específico."""
    form = RegistroPontoForm() # Instancia o formulário

    # Se for GET e houver 'data' na URL, pré-preenche o campo data
    if request.method == 'GET':
        data_query = request.args.get('data')
        # --- CORREÇÃO DA SINTAXE ---
        if data_query:
            try:
                # Tenta converter a data da URL e definir no formulário
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                # Avisa se a data da URL for inválida
                flash('Data na URL inválida.', 'warning')
        # --- FIM DA CORREÇÃO ---

    # Se o formulário for enviado e validado
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            # Verifica se já existe um registro para o mesmo usuário e data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                # Se existir, avisa e redireciona para edição
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Calcula as horas trabalhadas com base nos horários fornecidos
            horas_calculadas = calcular_horas(
                data_selecionada,
                form.entrada.data,
                form.saida.data,
                form.saida_almoco.data,
                form.retorno_almoco.data
            )

            # Cria um novo objeto Ponto
            novo_registro = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data,
                retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data,
                horas_trabalhadas=horas_calculadas,
                observacoes=form.observacoes.data,
                resultados_produtos=form.resultados_produtos.data, # Salva o novo campo
                afastamento=False, # Não é um afastamento
                tipo_afastamento=None
            )
            db.session.add(novo_registro)
            db.session.flush() # Garante que o ID seja gerado antes de criar a atividade

            # Se houver descrição de atividades, cria um registro Atividade
            if form.atividades.data and form.atividades.data.strip():
                atividade = Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip())
                db.session.add(atividade)

            db.session.commit() # Salva as alterações no banco
            flash('Registro de ponto criado com sucesso!', 'success')
            # Redireciona para o dashboard do mês/ano do registro criado
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            # Em caso de erro, desfaz as alterações e loga o erro
            db.session.rollback()
            logger.error(f"Erro ao registrar ponto: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o ponto. Tente novamente.', 'danger')

    # Renderiza o template do formulário de registro
    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")


# Rota para editar um ponto existente
@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required # Requer login
def editar_ponto(ponto_id):
    """Edita um registro de ponto existente."""
    registro = Ponto.query.get_or_404(ponto_id) # Busca o registro ou retorna 404

    # Verifica se o usuário logado é dono do registro ou é admin
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Instancia o formulário, preenchendo com os dados do registro existente
    form = EditarPontoForm(obj=registro)
    # Busca a atividade associada, se existir
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    # Se for GET, preenche o campo de atividades se existir e não houver erro anterior
    if request.method == 'GET':
        if atividade_existente and not form.atividades.data:
            form.atividades.data = atividade_existente.descricao
        # Os campos 'resultados_produtos' e 'observacoes' são preenchidos automaticamente pelo obj=registro

    # Se o formulário for enviado e validado
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data # Verifica se o checkbox de afastamento está marcado
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            # Validação: Se for afastamento, o tipo é obrigatório
            if is_afastamento and not tipo_afastamento:
                 flash('Selecione o Tipo de Afastamento quando marcar como afastamento.', 'danger')
                 return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

            # Atualiza os dados do registro principal
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            registro.resultados_produtos = form.resultados_produtos.data # Atualiza o novo campo

            # Se for afastamento, limpa os campos de horário
            if is_afastamento:
                registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else:
                # Se não for afastamento, atualiza os horários e recalcula as horas
                registro.entrada=form.entrada.data
                registro.saida_almoco=form.saida_almoco.data
                registro.retorno_almoco=form.retorno_almoco.data
                registro.saida=form.saida.data
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada,
                    form.entrada.data,
                    form.saida.data,
                    form.saida_almoco.data,
                    form.retorno_almoco.data
                )

            # Atualiza, cria ou deleta a atividade associada
            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                # Se há descrição e já existe atividade, atualiza
                if atividade_existente:
                    atividade_existente.descricao = descricao_atividade
                # Se há descrição e não existe atividade, cria uma nova
                else:
                    db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade))
            # Se não há descrição e existe atividade, deleta a atividade
            elif atividade_existente:
                 db.session.delete(atividade_existente)

            db.session.commit() # Salva as alterações
            flash('Registro atualizado com sucesso!', 'success')
            # Redireciona para o dashboard do mês/ano do registro editado
            return redirect(url_for('main.dashboard', mes=registro.data.month, ano=registro.data.year))
        except Exception as e:
            # Em caso de erro, desfaz as alterações e loga o erro
            db.session.rollback()
            logger.error(f"Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao atualizar o registro. Tente novamente.', 'danger')

    # Renderiza o template de edição
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")

# Rota para registrar um afastamento
@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required # Requer login
def registrar_afastamento():
    """Registra um afastamento (férias, licença, etc.) para um dia."""
    form = RegistroAfastamentoForm() # Instancia o formulário

    # Se for GET e houver 'data' na URL, pré-preenche o campo data
    if request.method == 'GET':
        data_query = request.args.get('data')
        if data_query:
            try:
                form.data.data = date.fromisoformat(data_query)
            except ValueError:
                flash('Data na URL inválida.', 'warning')

    # Se o formulário for enviado e validado
    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            tipo_afastamento = form.tipo_afastamento.data
            # Verifica se já existe um registro para o mesmo usuário e data
            registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
            if registro_existente:
                # Se existir, avisa e redireciona para edição
                flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Você pode editá-lo.', 'danger')
                return redirect(url_for('main.editar_ponto', ponto_id=registro_existente.id))

            # Cria um novo registro Ponto marcado como afastamento
            novo_afastamento = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                afastamento=True, # Marca como afastamento
                tipo_afastamento=tipo_afastamento,
                entrada=None, saida_almoco=None, retorno_almoco=None, saida=None, # Horários nulos
                horas_trabalhadas=None, observacoes=None, resultados_produtos=None # Campos extras nulos
            )
            db.session.add(novo_afastamento)
            db.session.commit() # Salva no banco
            flash('Afastamento registrado com sucesso!', 'success')
            # Redireciona para o dashboard do mês/ano do afastamento
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            # Em caso de erro, desfaz as alterações e loga o erro
            db.session.rollback()
            logger.error(f"Erro ao registrar afastamento: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o afastamento. Tente novamente.', 'danger')

    # Renderiza o template do formulário de afastamento
    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")

# Rota para registrar férias (redireciona para afastamento)
@main.route('/registrar-ferias', methods=['GET', 'POST'])
@login_required # Requer login
def registrar_ferias():
    """Redireciona para a rota de registrar afastamento."""
    flash('Use a opção "Registrar Afastamento" para registrar férias.', 'info')
    # Mantém os parâmetros da URL (como 'data') ao redirecionar
    return redirect(url_for('main.registrar_afastamento', **request.args))

# Rota do Calendário
@main.route('/calendario')
@login_required # Requer login
def calendario():
    """Exibe o calendário mensal com os registros de ponto."""
    try:
        # Obtém o usuário e a lista de usuários (se admin)
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        # Obtém mês e ano da URL, ou usa o mês/ano atual como padrão
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Validação básica de mês
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        # Define o primeiro e último dia do mês solicitado
        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        # Busca os registros de ponto do usuário para o mês/ano selecionado
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).all()
        registros_dict = {r.data: r for r in registros} # Dicionário para acesso rápido

        # Busca os feriados do mês/ano selecionado
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados} # Dicionário para acesso rápido
        feriados_datas = set(feriados_dict.keys())

        # --- Cálculo das estatísticas do mês (igual ao dashboard) ---
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_dict.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # -------------------------------------------------------------

        # Obtém nome do mês e calcula mês/ano anterior e próximo para navegação
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        # Gera a estrutura de dados para o calendário
        cal = calendar.Calendar(firstweekday=6) # Define domingo como primeiro dia da semana
        semanas_mes = cal.monthdayscalendar(ano_req, mes_req) # Obtém semanas do mês
        calendario_data = [] # Lista para armazenar os dados formatados

        # Processa cada semana e cada dia para montar a estrutura do calendário
        for semana in semanas_mes:
            semana_data = []
            for dia in semana:
                # Cria um dicionário com informações padrão para cada dia
                dia_info = {'dia': dia, 'data': None, 'is_mes_atual': False, 'registro': None, 'feriado': None, 'is_hoje': False, 'is_fim_semana': False}
                if dia != 0: # Se for um dia válido (não 0)
                    data_atual = date(ano_req, mes_req, dia)
                    # Atualiza o dicionário com informações específicas do dia
                    dia_info.update({
                        'data': data_atual,
                        'is_mes_atual': True, # Marca como dia do mês atual
                        'registro': registros_dict.get(data_atual), # Obtém o registro (ou None)
                        'feriado': feriados_dict.get(data_atual), # Obtém o feriado (ou None)
                        'is_hoje': (data_atual == hoje), # Verifica se é o dia atual
                        'is_fim_semana': (data_atual.weekday() >= 5) # Verifica se é fim de semana
                    })
                semana_data.append(dia_info) # Adiciona info do dia à semana
            calendario_data.append(semana_data) # Adiciona semana ao calendário

        # Renderiza o template do calendário com todos os dados
        return render_template(
            'main/calendario.html',
            calendario_data=calendario_data,
            mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas, media_diaria=media_diaria,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano
        )
    except ValueError:
        # Trata erro se a data for inválida
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        # Loga e trata outros erros
        logger.error(f"Erro ao carregar calendário: {e}", exc_info=True)
        flash('Erro ao carregar o calendário. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para o Relatório Mensal detalhado
@main.route('/relatorio-mensal')
@login_required # Requer login
def relatorio_mensal():
    """Exibe o relatório mensal detalhado com todos os registros."""
    try:
        # Obtém o usuário e a lista de usuários (se admin)
        usuario_ctx, usuarios_admin = get_usuario_contexto()
        hoje = date.today()
        # Obtém mês e ano da URL, ou usa o mês/ano atual como padrão
        mes_req = request.args.get('mes', default=hoje.month, type=int)
        ano_req = request.args.get('ano', default=hoje.year, type=int)

        # Validação básica de mês
        if not (1 <= mes_req <= 12):
            mes_req = hoje.month
            flash('Mês inválido.', 'warning')

        # Define o primeiro e último dia do mês solicitado
        primeiro_dia = date(ano_req, mes_req, 1)
        num_dias_mes = calendar.monthrange(ano_req, mes_req)[1]
        ultimo_dia = date(ano_req, mes_req, num_dias_mes)

        # Busca os registros de ponto do usuário para o mês/ano selecionado
        registros = Ponto.query.filter(
            Ponto.user_id == usuario_ctx.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all() # Ordena por data (crescente)

        # Busca os feriados do mês/ano selecionado
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        # Cria um dicionário de registros por data
        registros_por_data = {registro.data: registro for registro in registros}
        # Obtém IDs dos pontos para buscar atividades
        ponto_ids = [r.id for r in registros]
        # Busca todas as atividades relacionadas aos pontos do mês
        atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
        # Cria um dicionário de atividades por ponto_id
        atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto:
                atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)

        # --- Cálculo das estatísticas do mês (igual ao dashboard/calendário) ---
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano_req, mes_req, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_por_data.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # --------------------------------------------------------------------

        # Obtém nome do mês e calcula mês/ano anterior e próximo para navegação
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes_req]
        mes_anterior, ano_anterior = (12, ano_req - 1) if mes_req == 1 else (mes_req - 1, ano_req)
        proximo_mes, proximo_ano = (1, ano_req + 1) if mes_req == 12 else (mes_req + 1, ano_req)

        # Renderiza o template do relatório mensal com todos os dados
        return render_template(
            'main/relatorio_mensal.html',
            registros=registros, mes_atual=mes_req, ano_atual=ano_req, nome_mes=nome_mes,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano,
            dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas, media_diaria=media_diaria,
            feriados_dict=feriados_dict, feriados_datas=feriados_datas,
            registros_por_data=registros_por_data, atividades_por_ponto=atividades_por_ponto,
            usuario=usuario_ctx, usuarios=usuarios_admin,
            date=date, ultimo_dia=ultimo_dia, ano=ano_req, mes=mes_req # Passa 'date' para usar no template
        )
    except ValueError:
        # Trata erro se a data for inválida
        flash('Data inválida.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        # Loga e trata outros erros
        logger.error(f"Erro ao gerar relatório mensal: {e}", exc_info=True)
        flash('Erro ao gerar o relatório mensal. Tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

# Rota para exportar o relatório mensal em PDF
@main.route('/relatorio-mensal/pdf')
@login_required # Requer login
def relatorio_mensal_pdf():
    """Gera e envia o relatório mensal em formato PDF."""
    # Obtém o ID do usuário alvo da URL (se admin estiver visualizando outro usuário)
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user # Por padrão, é o usuário logado
    # Se admin e user_id fornecido, busca o usuário alvo
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req:
            usuario_alvo = usuario_req
        else:
            flash(f"Usuário com ID {user_id_req} não encontrado.", "warning")
            return redirect(request.referrer or url_for('main.dashboard')) # Volta para página anterior

    # Obtém mês e ano da URL
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Importa a função de geração de PDF e chama
        from app.utils.export import generate_pdf
        pdf_rel_path = generate_pdf(usuario_alvo.id, mes, ano) # Gera o PDF

        if pdf_rel_path:
            # Monta o caminho absoluto para o PDF gerado
            pdf_abs_path = os.path.join(current_app.static_folder, pdf_rel_path)
            if os.path.exists(pdf_abs_path):
                # Define o nome do arquivo para download
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.pdf"
                # Envia o arquivo PDF para o navegador
                return send_file(pdf_abs_path, as_attachment=True, download_name=download_name)
            else:
                logger.error(f"Arquivo PDF não encontrado no caminho esperado: {pdf_abs_path}")
                flash('Erro interno: Arquivo PDF gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em PDF.', 'danger')
    except Exception as e:
        # Loga e trata erros durante a geração/envio do PDF
        logger.error(f"Erro ao gerar/enviar PDF: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')

    # Em caso de erro, redireciona de volta para o relatório mensal
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para exportar o relatório mensal em Excel
@main.route('/relatorio-mensal/excel')
@login_required # Requer login
def relatorio_mensal_excel():
    """Gera e envia o relatório mensal em formato Excel."""
    # Lógica para determinar o usuário alvo (igual à rota PDF)
    user_id_req = request.args.get('user_id', type=int)
    usuario_alvo = current_user
    if current_user.is_admin and user_id_req:
        usuario_req = User.query.get(user_id_req)
        if usuario_req: usuario_alvo = usuario_req
        else: flash(f"Usuário ID {user_id_req} não encontrado.", "warning"); return redirect(request.referrer or url_for('main.dashboard'))

    # Obtém mês e ano da URL
    hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Importa a função de geração de Excel e chama
        from app.utils.export import generate_excel
        excel_rel_path = generate_excel(usuario_alvo.id, mes, ano) # Gera o Excel

        if excel_rel_path:
            # Monta o caminho absoluto para o Excel gerado
            excel_abs_path = os.path.join(current_app.static_folder, excel_rel_path)
            if os.path.exists(excel_abs_path):
                # Define o nome do arquivo para download
                nome_mes_str = datetime(ano, mes, 1).strftime('%B').lower()
                download_name = f"relatorio_{usuario_alvo.matricula}_{nome_mes_str}_{ano}.xlsx"
                # Envia o arquivo Excel para o navegador
                return send_file(excel_abs_path, as_attachment=True, download_name=download_name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                logger.error(f"Arquivo Excel não encontrado: {excel_abs_path}")
                flash('Erro interno: Arquivo Excel gerado não foi encontrado.', 'danger')
        else:
            flash('Erro ao gerar o relatório em Excel.', 'danger')
    except Exception as e:
        # Loga e trata erros durante a geração/envio do Excel
        logger.error(f"Erro ao gerar/enviar Excel: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o Excel.', 'danger')

    # Em caso de erro, redireciona de volta para o relatório mensal
    return redirect(request.referrer or url_for('main.relatorio_mensal', user_id=usuario_alvo.id, mes=mes, ano=ano))

# Rota para visualizar detalhes de um ponto específico
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required # Requer login
def visualizar_ponto(ponto_id):
    """Exibe os detalhes de um registro de ponto específico."""
    registro = Ponto.query.get_or_404(ponto_id) # Busca o registro ou retorna 404

    # Verifica permissão (dono do registro ou admin)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Busca as atividades associadas ao ponto
    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    # Busca o usuário dono do registro
    usuario_dono = User.query.get(registro.user_id)
    if not usuario_dono:
        # Trata caso raro onde o usuário do ponto não existe mais
        flash('Usuário associado a este registro não encontrado.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Renderiza o template de visualização
    return render_template('main/visualizar_ponto.html', registro=registro, atividades=atividades, usuario=usuario_dono, title="Visualizar Registro")

# Rota para excluir um ponto (via POST)
@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required # Requer login
def excluir_ponto(ponto_id):
    """Exclui um registro de ponto."""
    registro = Ponto.query.get_or_404(ponto_id) # Busca o registro ou retorna 404
    data_registro = registro.data # Guarda a data para redirecionar corretamente

    # Verifica permissão (dono do registro ou admin)
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # Deleta o registro (atividades associadas são deletadas em cascata pelo 'cascade' no modelo)
        db.session.delete(registro)
        db.session.commit() # Salva a exclusão
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        # Em caso de erro, desfaz e loga
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
        flash('Ocorreu um erro ao excluir o registro.', 'danger')

    # Redireciona para o dashboard do mês/ano do registro excluído
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

# Rota para visualizar o perfil do usuário logado
@main.route('/perfil')
@login_required # Requer login
def perfil():
    """Exibe a página de perfil do usuário logado."""
    # Busca o usuário atualizado no banco (caso informações tenham mudado)
    usuario_atualizado = User.query.get(current_user.id)
    if not usuario_atualizado:
        # Trata caso raro onde o usuário não é encontrado
        flash('Erro ao carregar informações do perfil.', 'danger')
        return redirect(url_for('main.dashboard'))
    # Renderiza o template do perfil
    return render_template('main/perfil.html', usuario=usuario_atualizado, title="Meu Perfil")

# Rota para registrar múltiplos pontos de uma vez
@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required # Requer login
def registrar_multiplo_ponto():
    """Permite registrar múltiplos pontos de uma vez."""
    form = MultiploPontoForm() # Usa um formulário mínimo apenas para o token CSRF

    # Se o formulário for enviado (POST) e o token CSRF for válido
    if form.validate_on_submit():
        try:
            # Obtém listas de dados do formulário (enviados pelo JS)
            datas_str = request.form.getlist('datas[]')
            entradas_str = request.form.getlist('entradas[]')
            saidas_almoco_str = request.form.getlist('saidas_almoco[]')
            retornos_almoco_str = request.form.getlist('retornos_almoco[]')
            saidas_str = request.form.getlist('saidas[]')
            atividades_desc = request.form.getlist('atividades[]')
            resultados_produtos_desc = request.form.getlist('resultados_produtos[]') # Lê novo campo
            observacoes_desc = request.form.getlist('observacoes[]') # Lê novo campo

            registros_criados, registros_ignorados = 0, 0
            datas_processadas = set() # Para evitar processar a mesma data duas vezes

            # Itera sobre as datas enviadas
            for i in range(len(datas_str)):
                data_str = datas_str[i]
                if not data_str: continue # Pula se a data estiver vazia

                try:
                    data = date.fromisoformat(data_str) # Converte string para data
                except ValueError:
                    flash(f'Formato de data inválido ignorado: {data_str}', 'warning')
                    continue # Pula data inválida

                if data in datas_processadas: continue # Pula se a data já foi processada
                datas_processadas.add(data)

                # Verifica se já existe registro para esta data
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data).first()
                if registro_existente:
                    flash(f'Registro para {data.strftime("%d/%m/%Y")} já existe e foi ignorado.', 'info')
                    registros_ignorados += 1
                    continue # Pula se já existe

                # Obtém os dados correspondentes para esta data (com verificação de índice)
                entrada_str = entradas_str[i] if i < len(entradas_str) else None
                saida_almoco_str_i = saidas_almoco_str[i] if i < len(saidas_almoco_str) else None
                retorno_almoco_str_i = retornos_almoco_str[i] if i < len(retornos_almoco_str) else None
                saida_str_i = saidas_str[i] if i < len(saidas_str) else None
                atividade_desc_i = atividades_desc[i].strip() if i < len(atividades_desc) and atividades_desc[i] else None
                resultado_desc_i = resultados_produtos_desc[i].strip() if i < len(resultados_produtos_desc) and resultados_produtos_desc[i] else None # Obtém novo campo
                observacao_i = observacoes_desc[i].strip() if i < len(observacoes_desc) and observacoes_desc[i] else None # Obtém novo campo

                # Tenta converter os horários de string para time
                try:
                    entrada_t = time.fromisoformat(entrada_str) if entrada_str else None
                    saida_almoco_t = time.fromisoformat(saida_almoco_str_i) if saida_almoco_str_i else None
                    retorno_almoco_t = time.fromisoformat(retorno_almoco_str_i) if retorno_almoco_str_i else None
                    saida_t = time.fromisoformat(saida_str_i) if saida_str_i else None
                except ValueError:
                    flash(f'Formato de hora inválido para {data.strftime("%d/%m/%Y")}. Registro ignorado.', 'warning')
                    continue # Pula se o horário for inválido

                # Calcula as horas trabalhadas
                horas_calculadas = calcular_horas(data, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)

                # Cria o novo registro Ponto
                novo_registro = Ponto(
                    user_id=current_user.id, data=data, entrada=entrada_t,
                    saida_almoco=saida_almoco_t, retorno_almoco=retorno_almoco_t,
                    saida=saida_t, horas_trabalhadas=horas_calculadas,
                    afastamento=False, tipo_afastamento=None,
                    resultados_produtos=resultado_desc_i, # Salva novo campo
                    observacoes=observacao_i # Salva novo campo
                )
                db.session.add(novo_registro)

                # Tenta salvar o registro e a atividade (se houver)
                try:
                    db.session.flush() # Gera o ID do novo registro
                    if atividade_desc_i:
                        db.session.add(Atividade(ponto_id=novo_registro.id, descricao=atividade_desc_i))
                    db.session.commit() # Salva no banco
                    registros_criados += 1
                except Exception as commit_err:
                    # Em caso de erro no commit, desfaz e loga
                    db.session.rollback()
                    logger.error(f"Erro ao salvar registro/atividade para {data}: {commit_err}", exc_info=True)
                    flash(f'Erro ao salvar registro para {data.strftime("%d/%m/%Y")}.', 'danger')

            # Mensagens de feedback para o usuário sobre o resultado
            if registros_criados > 0 and registros_ignorados == 0:
                flash(f'{registros_criados} registro(s) criado(s) com sucesso!', 'success')
            elif registros_criados > 0 and registros_ignorados > 0:
                flash(f'{registros_criados} registro(s) criado(s). {registros_ignorados} data(s) ignorada(s) por já existir registro.', 'warning')
            elif registros_ignorados > 0 and registros_criados == 0:
                flash('Nenhum novo registro criado (todas as datas informadas já possuíam registro).', 'info')
            elif len(datas_processadas) == 0:
                flash('Nenhuma data válida foi informada para registro.', 'warning')
            else: # Caso onde houve erros de formato ou commit
                flash('Nenhum registro criado devido a erros nos dados informados.', 'danger')

            return redirect(url_for('main.dashboard')) # Redireciona para o dashboard
        except Exception as e:
            # Trata erros gerais no processamento
            db.session.rollback()
            logger.error(f"Erro inesperado ao processar múltiplos pontos: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao processar os registros. Tente novamente.', 'danger')
            return redirect(url_for('main.registrar_multiplo_ponto'))

    # Se for GET ou a validação CSRF falhar, renderiza o template do formulário
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos")


# Rota para registrar/editar atividade de um ponto existente
@main.route('/ponto/<int:ponto_id>/atividade', methods=['GET', 'POST'])
@login_required # Requer login
def registrar_atividade(ponto_id):
    """Registra ou edita a atividade de um ponto específico."""
    ponto = Ponto.query.get_or_404(ponto_id) # Busca o ponto ou retorna 404

    # Verifica permissão (dono do ponto ou admin)
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar atividades deste registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = AtividadeForm() # Instancia o formulário de atividade
    # Busca a atividade existente, se houver
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    # Se o formulário for enviado e validado
    if form.validate_on_submit():
        try:
            descricao = form.descricao.data.strip() # Obtém a descrição (removendo espaços extras)
            if atividade_existente:
                # Se já existe, atualiza a descrição
                atividade_existente.descricao = descricao
            else:
                # Se não existe, cria uma nova atividade
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao)
                db.session.add(nova_atividade)
            db.session.commit() # Salva as alterações
            flash('Atividade salva com sucesso!', 'success')
            # Redireciona de volta para a visualização do ponto
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e:
            # Em caso de erro, desfaz e loga
            db.session.rollback()
            logger.error(f"Erro ao salvar atividade para ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao salvar a atividade.', 'danger')

    # Se for GET e existir atividade, pré-preenche o formulário
    elif request.method == 'GET':
        if atividade_existente:
            form.descricao.data = atividade_existente.descricao

    # Renderiza o template do formulário de atividade
    return render_template(
        'main/registrar_atividade.html',
        ponto=ponto,
        form=form, # Passa o objeto do formulário para o template
        title="Registrar/Editar Atividade"
    )
