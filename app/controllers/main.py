# -*- coding: utf-8 -*-
"""
Controlador Principal da Aplicação Flask

Este módulo define as rotas principais da aplicação, incluindo o dashboard,
registro de ponto, visualização de relatórios e perfil do usuário.
Utiliza Flask Blueprints para organizar as rotas.

Imports:
    - datetime, timedelta, date: Manipulação de datas e horas.
    - calendar: Funções relacionadas a calendário.
    - os: Interação com o sistema operacional (para variáveis de ambiente).
    - logging: Registro de eventos e erros.
    - io.BytesIO: Manipulação de dados em memória como arquivos binários.
    - flask: Framework web (Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file).
    - flask_login: Gerenciamento de sessão de usuário (login_required, current_user).
    - sqlalchemy: ORM para interação com banco de dados (desc).
    - werkzeug.utils: Utilitários (secure_filename).
    - app: Módulo da aplicação (db).
    - app.models: Modelos de dados (User, Ponto, Feriado, Afastamento, Atividade).
    - app.forms: Formulários WTForms (RegistroPontoForm, DateForm, AfastamentoForm, AtividadeForm, MultiRegistroPontoForm, EditarPontoForm).
    - app.utils.export: Funções para exportar dados (gerar_relatorio_pdf_bytes, gerar_relatorio_excel_bytes).
    - app.utils.helpers: Funções auxiliares (calcular_horas_trabalhadas_dia, calcular_saldo_banco_horas, get_dias_uteis_no_mes, get_feriados_no_mes, get_afastamentos_no_mes, get_atividades_no_mes).
"""

# Imports de bibliotecas padrão
import calendar
import logging
import os
from datetime import date, datetime, time, timedelta
from io import BytesIO

# Imports de terceiros
from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, url_for)
from flask_login import current_user, login_required
from sqlalchemy import desc

# Imports locais
from app import db
from app.forms.ponto import (AfastamentoForm, AtividadeForm, DateForm,
                             EditarPontoForm, MultiRegistroPontoForm,
                             RegistroPontoForm)
from app.models.feriado import Feriado
from app.models.ponto import Afastamento, Atividade, Ponto
from app.models.user import User
from app.utils.export import (gerar_relatorio_excel_bytes,
                              gerar_relatorio_pdf_bytes)
from app.utils.helpers import (calcular_horas_trabalhadas_dia,
                               calcular_saldo_banco_horas,
                               get_afastamentos_no_mes, get_atividades_no_mes,
                               get_dias_uteis_no_mes, get_feriados_no_mes)

# Configuração do Blueprint
main = Blueprint('main', __name__)

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Rotas Principais ---

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    """
    Rota para o dashboard principal do usuário.

    Exibe os registros de ponto do dia atual e um resumo do mês.
    """
    hoje = date.today()
    pontos_hoje = Ponto.query.filter_by(user_id=current_user.id, data=hoje).order_by(Ponto.hora).all()
    horas_trabalhadas_hoje, _ = calcular_horas_trabalhadas_dia(pontos_hoje)

    # Calcula o saldo de banco de horas do mês atual
    saldo_mes_atual = calcular_saldo_banco_horas(current_user.id, hoje.year, hoje.month)

    # Busca o último registro de ponto para determinar o próximo tipo (Entrada/Saída)
    ultimo_ponto = Ponto.query.filter_by(user_id=current_user.id).order_by(Ponto.timestamp.desc()).first()
    proximo_tipo = 'Saída' if ultimo_ponto and ultimo_ponto.tipo == 'Entrada' else 'Entrada'

    # Verifica se há um afastamento ativo hoje
    afastamento_hoje = Afastamento.query.filter(
        Afastamento.user_id == current_user.id,
        Afastamento.data_inicio <= hoje,
        Afastamento.data_fim >= hoje
    ).first()

    # Verifica se há uma atividade registrada hoje
    atividade_hoje = Atividade.query.filter(
        Atividade.user_id == current_user.id,
        Atividade.data == hoje
    ).first()

    return render_template('main/dashboard.html',
                           title='Dashboard',
                           pontos_hoje=pontos_hoje,
                           horas_trabalhadas_hoje=horas_trabalhadas_hoje,
                           saldo_mes_atual=saldo_mes_atual,
                           proximo_tipo=proximo_tipo,
                           afastamento_hoje=afastamento_hoje,
                           atividade_hoje=atividade_hoje)

@main.route('/registrar_ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """
    Rota para registrar um novo ponto (entrada ou saída).

    Permite ao usuário registrar manualmente a hora ou usar a hora atual.
    """
    form = RegistroPontoForm()
    hoje = date.today()

    # Busca o último ponto registrado para sugerir o próximo tipo
    ultimo_ponto = Ponto.query.filter_by(user_id=current_user.id).order_by(Ponto.timestamp.desc()).first()
    tipo_sugerido = 'Saída' if ultimo_ponto and ultimo_ponto.tipo == 'Entrada' else 'Entrada'

    # Preenche o formulário com a data atual e o tipo sugerido por padrão
    if request.method == 'GET':
        form.data.data = hoje
        form.tipo.data = tipo_sugerido

    if form.validate_on_submit():
        data_registro = form.data.data
        hora_registro = form.hora.data
        tipo = form.tipo.data
        observacao = form.observacao.data

        # Combina data e hora para criar o timestamp
        if data_registro and hora_registro:
            timestamp_registro = datetime.combine(data_registro, hora_registro)
        else:
            # Se hora não for fornecida, usa a hora atual
            agora = datetime.now()
            timestamp_registro = datetime.combine(data_registro or hoje, agora.time())
            hora_registro = timestamp_registro.time() # Atualiza a hora para salvar

        # Verifica se já existe um registro muito próximo (evitar duplicidade acidental)
        limite_inferior = timestamp_registro - timedelta(minutes=1)
        limite_superior = timestamp_registro + timedelta(minutes=1)
        ponto_existente = Ponto.query.filter(
            Ponto.user_id == current_user.id,
            Ponto.timestamp >= limite_inferior,
            Ponto.timestamp <= limite_superior,
            Ponto.tipo == tipo
        ).first()

        if ponto_existente:
            flash(f'Já existe um registro de {tipo.lower()} próximo a este horário.', 'warning')
            return redirect(url_for('main.registrar_ponto'))

        # Verifica se há um afastamento ativo na data do registro
        afastamento_ativo = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_inicio <= data_registro,
            Afastamento.data_fim >= data_registro
        ).first()

        if afastamento_ativo:
            flash(f'Não é possível registrar ponto em {data_registro.strftime("%d/%m/%Y")}, pois há um afastamento registrado ({afastamento_ativo.motivo}).', 'warning')
            return redirect(url_for('main.registrar_ponto'))

        # Verifica se há uma atividade registrada na data do registro
        atividade_registrada = Atividade.query.filter(
            Atividade.user_id == current_user.id,
            Atividade.data == data_registro
        ).first()

        if atividade_registrada:
            flash(f'Não é possível registrar ponto em {data_registro.strftime("%d/%m/%Y")}, pois há uma atividade externa/home office registrada ({atividade_registrada.descricao}).', 'warning')
            return redirect(url_for('main.registrar_ponto'))

        novo_ponto = Ponto(
            user_id=current_user.id,
            timestamp=timestamp_registro,
            data=data_registro,
            hora=hora_registro,
            tipo=tipo,
            observacao=observacao
        )
        db.session.add(novo_ponto)
        db.session.commit()
        flash(f'Ponto de {tipo.lower()} registrado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    elif request.method == 'POST':
        # Se a validação falhar, exibe mensagens de erro
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('main/registrar_ponto.html', title='Registrar Ponto', form=form, tipo_sugerido=tipo_sugerido)


@main.route('/visualizar_ponto', methods=['GET', 'POST'])
@login_required
def visualizar_ponto():
    """
    Rota para visualizar os registros de ponto de um dia específico.

    Permite ao usuário selecionar uma data e ver os pontos registrados,
    horas trabalhadas e saldo do dia.
    """
    form = DateForm()
    data_selecionada = date.today()
    pontos = []
    horas_trabalhadas = timedelta(0)
    saldo_dia = timedelta(0)
    jornada_esperada = timedelta(hours=current_user.jornada_diaria)
    afastamento_dia = None
    atividade_dia = None

    # Processa a data da query string se presente (para links diretos do calendário)
    data_query = request.args.get('data')
    if request.method == 'GET' and data_query:
        try:
            # CORREÇÃO: Bloco try/except movido para linhas separadas e indentado corretamente
            form.data.data = date.fromisoformat(data_query)
        except ValueError:
            flash('Data URL inválida.', 'warning')
            # Mantém a data de hoje se a URL for inválida
            form.data.data = date.today()
        data_selecionada = form.data.data # Atualiza data_selecionada com a data da URL (ou hoje)

    if form.validate_on_submit():
        data_selecionada = form.data.data
    # Se não for POST e não houver data na query, preenche com hoje
    elif request.method == 'GET' and not data_query:
        form.data.data = data_selecionada

    if data_selecionada:
        # Verifica se há afastamento ou atividade para o dia selecionado
        afastamento_dia = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_inicio <= data_selecionada,
            Afastamento.data_fim >= data_selecionada
        ).first()

        atividade_dia = Atividade.query.filter(
            Atividade.user_id == current_user.id,
            Atividade.data == data_selecionada
        ).first()

        # Se não houver afastamento ou atividade, busca os pontos
        if not afastamento_dia and not atividade_dia:
            pontos = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).order_by(Ponto.hora).all()
            horas_trabalhadas, _ = calcular_horas_trabalhadas_dia(pontos)
            # Verifica se é feriado
            feriado = Feriado.query.filter_by(data=data_selecionada).first()
            # Verifica se é fim de semana
            dia_semana = data_selecionada.weekday() # Segunda é 0, Domingo é 6

            if feriado or dia_semana >= 5: # 5 é Sábado, 6 é Domingo
                # Em feriados e fins de semana, a jornada esperada é 0, saldo é o total trabalhado
                saldo_dia = horas_trabalhadas
            else:
                saldo_dia = horas_trabalhadas - jornada_esperada
        else:
            # Se houver afastamento ou atividade, não há pontos ou saldo a calcular (ou lógica específica pode ser adicionada)
            horas_trabalhadas = timedelta(0)
            saldo_dia = timedelta(0) # Ou pode ser definido como "N/A" ou similar no template

    return render_template('main/visualizar_ponto.html',
                           title='Visualizar Ponto',
                           form=form,
                           pontos=pontos,
                           data_selecionada=data_selecionada,
                           horas_trabalhadas=horas_trabalhadas,
                           saldo_dia=saldo_dia,
                           afastamento_dia=afastamento_dia,
                           atividade_dia=atividade_dia)

@main.route('/editar_ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """
    Rota para editar um registro de ponto existente.
    """
    ponto = Ponto.query.get_or_404(ponto_id)
    # Garante que o usuário só possa editar seus próprios pontos
    if ponto.user_id != current_user.id:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.visualizar_ponto', data=ponto.data.isoformat()))

    form = EditarPontoForm(obj=ponto)
    # Preenche os campos de data e hora separadamente
    if request.method == 'GET':
        form.data.data = ponto.data
        form.hora.data = ponto.hora

    if form.validate_on_submit():
        # Verifica se há afastamento ou atividade na nova data
        nova_data = form.data.data
        afastamento_ativo = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_inicio <= nova_data,
            Afastamento.data_fim >= nova_data
        ).first()
        atividade_registrada = Atividade.query.filter(
            Atividade.user_id == current_user.id,
            Atividade.data == nova_data
        ).first()

        if afastamento_ativo and afastamento_ativo.id != getattr(ponto, 'afastamento_id', None): # Permite editar se for ponto de afastamento? (a definir)
             flash(f'Não é possível mover o ponto para {nova_data.strftime("%d/%m/%Y")}, pois há um afastamento registrado ({afastamento_ativo.motivo}).', 'warning')
        elif atividade_registrada and atividade_registrada.id != getattr(ponto, 'atividade_id', None): # Permite editar se for ponto de atividade? (a definir)
            flash(f'Não é possível mover o ponto para {nova_data.strftime("%d/%m/%Y")}, pois há uma atividade externa/home office registrada ({atividade_registrada.descricao}).', 'warning')
        else:
            try:
                # Atualiza os dados do ponto
                ponto.data = form.data.data
                ponto.hora = form.hora.data
                ponto.timestamp = datetime.combine(ponto.data, ponto.hora)
                ponto.tipo = form.tipo.data
                ponto.observacao = form.observacao.data
                db.session.commit()
                flash('Registro de ponto atualizado com sucesso!', 'success')
                return redirect(url_for('main.visualizar_ponto', data=ponto.data.isoformat()))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar ponto {ponto_id}: {e}")
                flash('Erro ao atualizar o registro de ponto.', 'danger')

    elif request.method == 'POST':
        # Se a validação falhar, exibe mensagens de erro
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('main/editar_ponto.html', title='Editar Ponto', form=form, ponto=ponto)


@main.route('/excluir_ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """
    Rota para excluir um registro de ponto.
    """
    ponto = Ponto.query.get_or_404(ponto_id)
    # Garante que o usuário só possa excluir seus próprios pontos
    if ponto.user_id != current_user.id:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.visualizar_ponto')) # Redireciona para a visualização geral

    data_ponto = ponto.data.isoformat() # Guarda a data para redirecionar

    try:
        db.session.delete(ponto)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}")
        flash('Erro ao excluir o registro de ponto.', 'danger')

    # Redireciona para a visualização do dia do ponto excluído
    return redirect(url_for('main.visualizar_ponto', data=data_ponto))


@main.route('/registrar_multiplo_ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """
    Rota para registrar múltiplos pontos (entradas e saídas) para um dia específico.
    Útil para corrigir ou adicionar registros de um dia inteiro.
    """
    form = MultiRegistroPontoForm()
    data_selecionada = date.today()

    if request.method == 'GET':
        form.data.data = data_selecionada
        # Carrega pontos existentes para o dia, se houver, para edição
        pontos_existentes = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).order_by(Ponto.hora).all()
        # Limpa entradas existentes no formulário antes de popular
        while len(form.pontos) > 0:
            form.pontos.pop_entry()
        # Popula o formulário com os pontos existentes
        for ponto in pontos_existentes:
            form.pontos.append_entry({'hora': ponto.hora, 'tipo': ponto.tipo, 'observacao': ponto.observacao})
        # Adiciona uma entrada extra em branco se não houver pontos ou se o último for saída
        if not pontos_existentes or (pontos_existentes and pontos_existentes[-1].tipo == 'Saída'):
             form.pontos.append_entry()


    if form.validate_on_submit():
        data_registro = form.data.data

        # Verifica afastamento ou atividade na data
        afastamento_ativo = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_inicio <= data_registro,
            Afastamento.data_fim >= data_registro
        ).first()
        atividade_registrada = Atividade.query.filter(
            Atividade.user_id == current_user.id,
            Atividade.data == data_registro
        ).first()

        if afastamento_ativo:
            flash(f'Não é possível registrar pontos em {data_registro.strftime("%d/%m/%Y")}, pois há um afastamento registrado ({afastamento_ativo.motivo}).', 'warning')
            return redirect(url_for('main.registrar_multiplo_ponto'))
        if atividade_registrada:
             flash(f'Não é possível registrar pontos em {data_registro.strftime("%d/%m/%Y")}, pois há uma atividade externa/home office registrada ({atividade_registrada.descricao}).', 'warning')
             return redirect(url_for('main.registrar_multiplo_ponto'))

        try:
            # 1. Exclui todos os pontos existentes para este dia e usuário
            Ponto.query.filter_by(user_id=current_user.id, data=data_registro).delete()
            # Não commita ainda, faz tudo em uma transação

            # 2. Adiciona os novos pontos do formulário
            novos_pontos = []
            for entry in form.pontos.entries:
                hora_registro = entry.hora.data
                tipo = entry.tipo.data
                observacao = entry.observacao.data

                # Ignora entradas sem hora preenchida
                if hora_registro:
                    timestamp_registro = datetime.combine(data_registro, hora_registro)
                    novo_ponto = Ponto(
                        user_id=current_user.id,
                        timestamp=timestamp_registro,
                        data=data_registro,
                        hora=hora_registro,
                        tipo=tipo,
                        observacao=observacao
                    )
                    novos_pontos.append(novo_ponto)

            # Ordena os novos pontos pela hora antes de salvar
            novos_pontos.sort(key=lambda p: p.hora)

            db.session.add_all(novos_pontos)
            db.session.commit()
            flash(f'Registros de ponto para {data_registro.strftime("%d/%m/%Y")} atualizados com sucesso!', 'success')
            return redirect(url_for('main.visualizar_ponto', data=data_registro.isoformat()))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar múltiplos pontos para {data_registro}: {e}")
            flash('Erro ao salvar os registros de ponto.', 'danger')

    elif request.method == 'POST':
        # Se a validação falhar, exibe mensagens de erro
         for field, errors in form.errors.items():
            if field == 'pontos': # Erros dentro do FieldList
                for i, entry_errors in enumerate(errors):
                    for sub_field, sub_errors in entry_errors.items():
                        for error in sub_errors:
                            # Tenta obter o label do subcampo
                            try:
                                label = getattr(form.pontos.entries[i], sub_field).label.text
                            except AttributeError:
                                label = sub_field # Fallback para o nome do campo
                            flash(f"Erro na Entrada {i+1}, Campo '{label}': {error}", 'danger')
            else: # Erros nos campos principais (como data)
                for error in errors:
                    flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')


    return render_template('main/registrar_multiplo_ponto.html', title='Registrar Múltiplos Pontos', form=form)


@main.route('/relatorio_mensal', methods=['GET'])
@login_required
def relatorio_mensal():
    """
    Rota para visualizar o relatório mensal de ponto do usuário.

    Permite selecionar o mês e ano e exibe um resumo diário,
    incluindo horas trabalhadas, saldo e ocorrências (faltas, atrasos, etc.).
    """
    try:
        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        # Obtém ano e mês dos argumentos da requisição, com fallback para o atual
        ano = request.args.get('ano', default=ano_atual, type=int)
        mes = request.args.get('mes', default=mes_atual, type=int)

        # Validação básica para ano e mês
        if not (1 <= mes <= 12):
            flash('Mês inválido.', 'warning')
            mes = mes_atual
        if ano < 2000 or ano > ano_atual + 1: # Define um range razoável para o ano
             flash('Ano inválido.', 'warning')
             ano = ano_atual

        # Busca os dias úteis, feriados, afastamentos e atividades no mês/ano selecionado
        dias_uteis = get_dias_uteis_no_mes(ano, mes)
        feriados_mes = get_feriados_no_mes(ano, mes)
        afastamentos_mes = get_afastamentos_no_mes(current_user.id, ano, mes)
        atividades_mes = get_atividades_no_mes(current_user.id, ano, mes)


        # Busca todos os registros de ponto do usuário para o mês/ano selecionado
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
        pontos_mes = Ponto.query.filter(
            Ponto.user_id == current_user.id,
            Ponto.data >= inicio_mes,
            Ponto.data <= fim_mes
        ).order_by(Ponto.data, Ponto.hora).all()

        # Agrupa os pontos por dia
        pontos_por_dia = {}
        for ponto in pontos_mes:
            if ponto.data not in pontos_por_dia:
                pontos_por_dia[ponto.data] = []
            pontos_por_dia[ponto.data].append(ponto)

        # Calcula os dados para cada dia do mês
        relatorio_dias = []
        jornada_diaria = timedelta(hours=current_user.jornada_diaria)
        saldo_acumulado = timedelta(0) # Inicia o saldo acumulado do mês

        for dia_num in range(1, fim_mes.day + 1):
            data_dia = date(ano, mes, dia_num)
            dia_semana = data_dia.weekday() # Segunda=0, Domingo=6
            pontos_dia = pontos_por_dia.get(data_dia, [])
            horas_trabalhadas, comentarios = calcular_horas_trabalhadas_dia(pontos_dia)

            # Verifica feriado, afastamento e atividade
            e_feriado = data_dia in feriados_mes
            afastamento_dia = next((a for a in afastamentos_mes if a.data_inicio <= data_dia <= a.data_fim), None)
            atividade_dia = next((at for at in atividades_mes if at.data == data_dia), None)
            e_fim_semana = dia_semana >= 5 # Sábado ou Domingo

            # Determina a jornada esperada e calcula o saldo do dia
            jornada_esperada_dia = timedelta(0)
            status_dia = "" # Descrição do dia (Feriado, Fim de Semana, Afastamento, etc.)

            if afastamento_dia:
                saldo_dia = timedelta(0) # Abona o dia
                status_dia = f"Afastamento ({afastamento_dia.motivo})"
                horas_trabalhadas = jornada_diaria # Considera como jornada cumprida para fins de relatório
            elif atividade_dia:
                 saldo_dia = timedelta(0) # Abona o dia
                 status_dia = f"Atividade Externa/Home Office ({atividade_dia.descricao})"
                 horas_trabalhadas = jornada_diaria # Considera como jornada cumprida
            elif e_feriado:
                saldo_dia = horas_trabalhadas # Saldo é o que foi trabalhado
                status_dia = f"Feriado ({feriados_mes[data_dia]})"
            elif e_fim_semana:
                saldo_dia = horas_trabalhadas # Saldo é o que foi trabalhado
                status_dia = "Fim de Semana"
            else: # Dia útil normal
                jornada_esperada_dia = jornada_diaria
                saldo_dia = horas_trabalhadas - jornada_esperada_dia
                if not pontos_dia:
                    status_dia = "Falta" # Marca como falta se não houver pontos e for dia útil sem afastamento/atividade
                    saldo_dia = -jornada_esperada_dia # Saldo negativo da jornada

            saldo_acumulado += saldo_dia

            relatorio_dias.append({
                'data': data_dia,
                'dia_semana': calendar.day_abbr[dia_semana].capitalize(),
                'pontos': pontos_dia,
                'horas_trabalhadas': horas_trabalhadas,
                'saldo_dia': saldo_dia,
                'saldo_acumulado': saldo_acumulado,
                'jornada_esperada': jornada_esperada_dia,
                'status': status_dia,
                'comentarios': comentarios,
                'e_feriado': e_feriado,
                'e_fim_semana': e_fim_semana,
                'afastamento': afastamento_dia,
                'atividade': atividade_dia
            })

        # Calcula o saldo total do banco de horas (pode ser diferente do saldo do mês)
        saldo_banco_horas_total = calcular_saldo_banco_horas(current_user.id)

        # Gera lista de anos e meses para o seletor
        anos_disponiveis = sorted(list(set(p.data.year for p in Ponto.query.with_entities(Ponto.data).distinct())), reverse=True)
        if not anos_disponiveis or ano_atual not in anos_disponiveis:
            anos_disponiveis.insert(0, ano_atual) # Garante que o ano atual esteja na lista

        meses_disponiveis = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]

        return render_template('main/relatorio_mensal.html',
                               title='Relatório Mensal',
                               relatorio_dias=relatorio_dias,
                               ano_selecionado=ano,
                               mes_selecionado=mes,
                               anos_disponiveis=anos_disponiveis,
                               meses_disponiveis=meses_disponiveis,
                               saldo_banco_horas_total=saldo_banco_horas_total,
                               saldo_mes=saldo_acumulado, # Saldo acumulado no final do mês
                               nome_mes=calendar.month_name[mes].capitalize())
    except ValueError:
        flash('Data inválida fornecida.', 'danger')
        return redirect(url_for('main.relatorio_mensal'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal para usuário {current_user.id}, {mes}/{ano}: {e}", exc_info=True)
        flash('Ocorreu um erro ao gerar o relatório mensal.', 'danger')
        # Redireciona para o mês/ano atual em caso de erro inesperado
        return redirect(url_for('main.relatorio_mensal', ano=datetime.now().year, mes=datetime.now().month))


@main.route('/exportar_relatorio', methods=['GET'])
@login_required
def exportar_relatorio():
    """
    Rota para exportar o relatório mensal em PDF ou Excel.
    """
    ano = request.args.get('ano', default=datetime.now().year, type=int)
    mes = request.args.get('mes', default=datetime.now().month, type=int)
    formato = request.args.get('formato', default='pdf', type=str).lower()

    try:
        # Reutiliza a lógica de cálculo do relatório mensal
        # (Idealmente, refatorar para uma função separada no futuro)
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
        pontos_mes = Ponto.query.filter(
            Ponto.user_id == current_user.id,
            Ponto.data >= inicio_mes,
            Ponto.data <= fim_mes
        ).order_by(Ponto.data, Ponto.hora).all()

        feriados_mes = get_feriados_no_mes(ano, mes)
        afastamentos_mes = get_afastamentos_no_mes(current_user.id, ano, mes)
        atividades_mes = get_atividades_no_mes(current_user.id, ano, mes)

        pontos_por_dia = {}
        for ponto in pontos_mes:
            if ponto.data not in pontos_por_dia:
                pontos_por_dia[ponto.data] = []
            pontos_por_dia[ponto.data].append(ponto)

        relatorio_dias = []
        jornada_diaria = timedelta(hours=current_user.jornada_diaria)
        saldo_acumulado = timedelta(0)

        for dia_num in range(1, fim_mes.day + 1):
            data_dia = date(ano, mes, dia_num)
            dia_semana = data_dia.weekday()
            pontos_dia = pontos_por_dia.get(data_dia, [])
            horas_trabalhadas, comentarios = calcular_horas_trabalhadas_dia(pontos_dia)

            e_feriado = data_dia in feriados_mes
            afastamento_dia = next((a for a in afastamentos_mes if a.data_inicio <= data_dia <= a.data_fim), None)
            atividade_dia = next((at for at in atividades_mes if at.data == data_dia), None)
            e_fim_semana = dia_semana >= 5

            jornada_esperada_dia = timedelta(0)
            status_dia = ""

            if afastamento_dia:
                saldo_dia = timedelta(0)
                status_dia = f"Afastamento ({afastamento_dia.motivo})"
                horas_trabalhadas = jornada_diaria
            elif atividade_dia:
                 saldo_dia = timedelta(0)
                 status_dia = f"Atividade Externa/Home Office ({atividade_dia.descricao})"
                 horas_trabalhadas = jornada_diaria
            elif e_feriado:
                saldo_dia = horas_trabalhadas
                status_dia = f"Feriado ({feriados_mes[data_dia]})"
            elif e_fim_semana:
                saldo_dia = horas_trabalhadas
                status_dia = "Fim de Semana"
            else:
                jornada_esperada_dia = jornada_diaria
                saldo_dia = horas_trabalhadas - jornada_esperada_dia
                if not pontos_dia:
                    status_dia = "Falta"
                    saldo_dia = -jornada_esperada_dia

            saldo_acumulado += saldo_dia

            relatorio_dias.append({
                'data': data_dia,
                'dia_semana': calendar.day_abbr[dia_semana].capitalize(),
                'pontos': pontos_dia,
                'horas_trabalhadas': horas_trabalhadas,
                'saldo_dia': saldo_dia,
                'saldo_acumulado': saldo_acumulado,
                'jornada_esperada': jornada_esperada_dia,
                'status': status_dia,
                'comentarios': comentarios,
                'e_feriado': e_feriado,
                'e_fim_semana': e_fim_semana,
                'afastamento': afastamento_dia,
                'atividade': atividade_dia
            })

        # Calcula saldo total
        saldo_banco_horas_total = calcular_saldo_banco_horas(current_user.id)

        # Dados para passar para as funções de exportação
        dados_relatorio = {
            'usuario': current_user,
            'ano': ano,
            'mes': mes,
            'nome_mes': calendar.month_name[mes].capitalize(),
            'relatorio_dias': relatorio_dias,
            'saldo_mes': saldo_acumulado,
            'saldo_total': saldo_banco_horas_total,
            'jornada_diaria': jornada_diaria
        }

        if formato == 'pdf':
            # Renderiza o template HTML para o PDF
            html_content = render_template('exports/relatorio_ponto_pdf.html', **dados_relatorio)
            pdf_bytes = gerar_relatorio_pdf_bytes(html_content)
            if pdf_bytes:
                filename = f"relatorio_ponto_{current_user.username}_{ano}_{mes:02d}.pdf"
                return send_file(
                    BytesIO(pdf_bytes),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                flash('Erro ao gerar o relatório PDF.', 'danger')
        elif formato == 'excel':
            excel_bytes = gerar_relatorio_excel_bytes(dados_relatorio)
            if excel_bytes:
                filename = f"relatorio_ponto_{current_user.username}_{ano}_{mes:02d}.xlsx"
                return send_file(
                    BytesIO(excel_bytes),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                flash('Erro ao gerar o relatório Excel.', 'danger')
        else:
            flash('Formato de exportação inválido.', 'warning')

    except ValueError:
        flash('Data inválida fornecida para exportação.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao exportar relatório ({formato}) para usuário {current_user.id}, {mes}/{ano}: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao exportar o relatório em {formato.upper()}.', 'danger')

    # Redireciona de volta para a página do relatório em caso de erro ou formato inválido
    return redirect(url_for('main.relatorio_mensal', ano=ano, mes=mes))


@main.route('/perfil', methods=['GET'])
@login_required
def perfil():
    """
    Rota para visualizar o perfil do usuário.
    """
    # Os dados do usuário já estão disponíveis em `current_user`
    return render_template('main/perfil.html', title='Meu Perfil')


@main.route('/calendario', methods=['GET'])
@login_required
def calendario():
    """
    Rota para exibir um calendário mensal visual.

    Mostra os dias do mês, destacando feriados, fins de semana,
    dias com ponto registrado, afastamentos e atividades.
    Permite navegar entre os meses/anos.
    """
    try:
        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        # Obtém ano e mês dos argumentos da requisição, com fallback para o atual
        ano = request.args.get('ano', default=ano_atual, type=int)
        mes = request.args.get('mes', default=mes_atual, type=int)

        # Validação básica para ano e mês
        if not (1 <= mes <= 12):
            flash('Mês inválido.', 'warning')
            mes = mes_atual
        if ano < 2000 or ano > ano_atual + 5: # Define um range razoável para o ano
             flash('Ano inválido.', 'warning')
             ano = ano_atual

        # Busca dados relevantes para o mês/ano
        feriados_mes = get_feriados_no_mes(ano, mes)
        afastamentos_mes = get_afastamentos_no_mes(current_user.id, ano, mes)
        atividades_mes = get_atividades_no_mes(current_user.id, ano, mes)

        # Busca dias com ponto registrado no mês
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
        dias_com_ponto = db.session.query(Ponto.data).filter(
            Ponto.user_id == current_user.id,
            Ponto.data >= inicio_mes,
            Ponto.data <= fim_mes
        ).distinct().all()
        dias_com_ponto_set = {d[0] for d in dias_com_ponto} # Converte para set para busca rápida

        # Gera a matriz do calendário
        cal = calendar.Calendar(firstweekday=6) # Domingo como primeiro dia
        dias_do_mes = cal.monthdatescalendar(ano, mes)

        # Calcula mês/ano anterior e próximo para navegação
        data_atual = date(ano, mes, 1)
        mes_anterior = (data_atual - timedelta(days=1)).replace(day=1)
        # Para calcular o próximo mês, adiciona dias suficientes para passar do fim do mês atual
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        mes_proximo = (data_atual + timedelta(days=dias_no_mes)).replace(day=1)


        return render_template('main/calendario.html',
                               title='Calendário',
                               ano=ano,
                               mes=mes,
                               nome_mes=calendar.month_name[mes].capitalize(),
                               dias_do_mes=dias_do_mes,
                               feriados=feriados_mes,
                               afastamentos=afastamentos_mes,
                               atividades=atividades_mes,
                               dias_com_ponto=dias_com_ponto_set,
                               mes_anterior=mes_anterior,
                               mes_proximo=mes_proximo)
    except ValueError:
        flash('Data inválida fornecida para o calendário.', 'danger')
        return redirect(url_for('main.calendario'))
    except Exception as e:
        logger.error(f"Erro ao gerar calendário para usuário {current_user.id}, {mes}/{ano}: {e}", exc_info=True)
        flash('Ocorreu um erro ao gerar o calendário.', 'danger')
        return redirect(url_for('main.calendario', ano=datetime.now().year, mes=datetime.now().month))


@main.route('/registrar_afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    """
    Rota para registrar um período de afastamento (férias, licença, etc.).
    """
    form = AfastamentoForm()
    if form.validate_on_submit():
        data_inicio = form.data_inicio.data
        data_fim = form.data_fim.data
        motivo = form.motivo.data

        # Validação adicional: data fim não pode ser anterior à data início
        if data_fim < data_inicio:
            flash('A data final não pode ser anterior à data inicial.', 'danger')
            return render_template('main/registrar_afastamento.html', title='Registrar Afastamento', form=form)

        # Validação: Verificar conflito com pontos existentes no período
        pontos_conflitantes = Ponto.query.filter(
            Ponto.user_id == current_user.id,
            Ponto.data >= data_inicio,
            Ponto.data <= data_fim
        ).all()

        if pontos_conflitantes:
            datas_conflito = sorted(list(set(p.data.strftime('%d/%m/%Y') for p in pontos_conflitantes)))
            flash(f'Não é possível registrar afastamento. Existem pontos registrados nas seguintes datas: {", ".join(datas_conflito)}. Exclua ou mova esses pontos primeiro.', 'danger')
            return render_template('main/registrar_afastamento.html', title='Registrar Afastamento', form=form)

        # Validação: Verificar conflito com outros afastamentos
        afastamentos_conflitantes = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_fim >= data_inicio, # Fim do existente >= Início do novo
            Afastamento.data_inicio <= data_fim   # Início do existente <= Fim do novo
        ).all()

        if afastamentos_conflitantes:
            periodos_conflito = [f"{a.data_inicio.strftime('%d/%m/%Y')} a {a.data_fim.strftime('%d/%m/%Y')} ({a.motivo})" for a in afastamentos_conflitantes]
            flash(f'Conflito de datas com afastamentos existentes: {"; ".join(periodos_conflito)}.', 'danger')
            return render_template('main/registrar_afastamento.html', title='Registrar Afastamento', form=form)

        # Validação: Verificar conflito com atividades externas/home office
        atividades_conflitantes = Atividade.query.filter(
             Atividade.user_id == current_user.id,
             Atividade.data >= data_inicio,
             Atividade.data <= data_fim
         ).all()

        if atividades_conflitantes:
            datas_conflito = sorted(list(set(a.data.strftime('%d/%m/%Y') for a in atividades_conflitantes)))
            flash(f'Não é possível registrar afastamento. Existem atividades externas/home office registradas nas seguintes datas: {", ".join(datas_conflito)}. Exclua essas atividades primeiro.', 'danger')
            return render_template('main/registrar_afastamento.html', title='Registrar Afastamento', form=form)


        try:
            novo_afastamento = Afastamento(
                user_id=current_user.id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                motivo=motivo
            )
            db.session.add(novo_afastamento)
            db.session.commit()
            flash('Afastamento registrado com sucesso!', 'success')
            # Redireciona para o calendário do mês de início do afastamento
            return redirect(url_for('main.calendario', ano=data_inicio.year, mes=data_inicio.month))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar afastamento para usuário {current_user.id}: {e}", exc_info=True)
            flash('Erro ao registrar o afastamento.', 'danger')

    elif request.method == 'POST':
         # Se a validação falhar, exibe mensagens de erro
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    # Busca afastamentos existentes para exibir na página
    afastamentos_usuario = Afastamento.query.filter_by(user_id=current_user.id).order_by(Afastamento.data_inicio.desc()).all()

    return render_template('main/registrar_afastamento.html',
                           title='Registrar Afastamento',
                           form=form,
                           afastamentos=afastamentos_usuario)


@main.route('/excluir_afastamento/<int:afastamento_id>', methods=['POST'])
@login_required
def excluir_afastamento(afastamento_id):
    """
    Rota para excluir um registro de afastamento.
    """
    afastamento = Afastamento.query.get_or_404(afastamento_id)
    # Garante que o usuário só possa excluir seus próprios afastamentos
    if afastamento.user_id != current_user.id:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.registrar_afastamento'))

    try:
        db.session.delete(afastamento)
        db.session.commit()
        flash('Registro de afastamento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir afastamento {afastamento_id}: {e}", exc_info=True)
        flash('Erro ao excluir o registro de afastamento.', 'danger')

    return redirect(url_for('main.registrar_afastamento'))


@main.route('/registrar_atividade', methods=['GET', 'POST'])
@login_required
def registrar_atividade():
    """
    Rota para registrar uma atividade externa ou home office em um dia específico.
    """
    form = AtividadeForm()
    if form.validate_on_submit():
        data_atividade = form.data.data
        descricao = form.descricao.data

        # Validação: Verificar conflito com pontos existentes no dia
        pontos_conflitantes = Ponto.query.filter_by(user_id=current_user.id, data=data_atividade).all()
        if pontos_conflitantes:
            flash(f'Não é possível registrar atividade em {data_atividade.strftime("%d/%m/%Y")}. Existem pontos registrados neste dia. Exclua ou mova esses pontos primeiro.', 'danger')
            return render_template('main/registrar_atividade.html', title='Registrar Atividade Externa/Home Office', form=form)

        # Validação: Verificar conflito com afastamentos
        afastamento_conflitante = Afastamento.query.filter(
            Afastamento.user_id == current_user.id,
            Afastamento.data_inicio <= data_atividade,
            Afastamento.data_fim >= data_atividade
        ).first()
        if afastamento_conflitante:
            flash(f'Não é possível registrar atividade em {data_atividade.strftime("%d/%m/%Y")}. Existe um afastamento registrado ({afastamento_conflitante.motivo}) neste período.', 'danger')
            return render_template('main/registrar_atividade.html', title='Registrar Atividade Externa/Home Office', form=form)

        # Validação: Verificar se já existe atividade para este dia
        atividade_existente = Atividade.query.filter_by(user_id=current_user.id, data=data_atividade).first()
        if atividade_existente:
             flash(f'Já existe uma atividade registrada para {data_atividade.strftime("%d/%m/%Y")}. Exclua a atividade existente antes de registrar uma nova.', 'danger')
             return render_template('main/registrar_atividade.html', title='Registrar Atividade Externa/Home Office', form=form)

        try:
            nova_atividade = Atividade(
                user_id=current_user.id,
                data=data_atividade,
                descricao=descricao
            )
            db.session.add(nova_atividade)
            db.session.commit()
            flash('Atividade externa/home office registrada com sucesso!', 'success')
            # Redireciona para o calendário do mês da atividade
            return redirect(url_for('main.calendario', ano=data_atividade.year, mes=data_atividade.month))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar atividade para usuário {current_user.id}: {e}", exc_info=True)
            flash('Erro ao registrar a atividade.', 'danger')

    elif request.method == 'POST':
        # Se a validação falhar, exibe mensagens de erro
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    # Busca atividades existentes para exibir na página
    atividades_usuario = Atividade.query.filter_by(user_id=current_user.id).order_by(Atividade.data.desc()).all()

    return render_template('main/registrar_atividade.html',
                           title='Registrar Atividade Externa/Home Office',
                           form=form,
                           atividades=atividades_usuario)


@main.route('/excluir_atividade/<int:atividade_id>', methods=['POST'])
@login_required
def excluir_atividade(atividade_id):
    """
    Rota para excluir um registro de atividade externa/home office.
    """
    atividade = Atividade.query.get_or_404(atividade_id)
    # Garante que o usuário só possa excluir suas próprias atividades
    if atividade.user_id != current_user.id:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.registrar_atividade'))

    try:
        db.session.delete(atividade)
        db.session.commit()
        flash('Registro de atividade excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir atividade {atividade_id}: {e}", exc_info=True)
        flash('Erro ao excluir o registro de atividade.', 'danger')

    return redirect(url_for('main.registrar_atividade'))
