# -*- coding: utf-8 -*-
# Importações básicas e de bibliotecas padrão
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
# Removido: import calendar (usado em _get_relatorio_mensal_data)
import logging
import os
# Removido: import tempfile (não usado aqui)
# Removido: import pandas as pd (não usado aqui)
from datetime import datetime, date, timedelta, time
# Removido: from sqlalchemy import desc, extract, func, case (usado em _get_relatorio_mensal_data)
# Removido: from calendar import monthrange (usado em _get_relatorio_mensal_data)
from io import BytesIO # Para exportação Excel/PDF

# --- Definição do Blueprint 'main' ---
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# --- FIM DA DEFINIÇÃO ---

# Importações de módulos da aplicação
from app import db, csrf
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.models.relatorio_completo import RelatorioMensalCompleto
from app.forms.ponto import RegistroPontoForm, EditarPontoForm, RegistroAfastamentoForm, AtividadeForm, MultiploPontoForm
from app.forms.relatorio import RelatorioCompletoForm
# Importa funções de exportação
from app.utils.export import generate_pdf, generate_excel
# --- Importa funções auxiliares do novo módulo ---
from app.utils.helpers import calcular_horas, _get_relatorio_mensal_data
# -------------------------------------------------

# --- ROTA RAIZ ---
@main.route('/')
@login_required
def index():
    """Redireciona para o dashboard."""
    return redirect(url_for('main.dashboard'))

# --- ROTA DASHBOARD ---
@main.route('/dashboard')
@login_required
def dashboard():
    """Exibe o dashboard principal do usuário."""
    try:
        user_id_para_visualizar = request.args.get('user_id', default=current_user.id, type=int)

        # Verifica permissão de admin se user_id for diferente do logado
        if user_id_para_visualizar != current_user.id and not current_user.is_admin:
            flash('Você não tem permissão para visualizar o dashboard de outro usuário.', 'danger')
            return redirect(url_for('main.dashboard', user_id=current_user.id))

        hoje = date.today()
        mes = request.args.get('mes', default=hoje.month, type=int)
        ano = request.args.get('ano', default=hoje.year, type=int)

        # --- Usa a função auxiliar importada ---
        dados_relatorio = _get_relatorio_mensal_data(user_id_para_visualizar, mes, ano)
        # ---------------------------------------

        # Lista de usuários para o seletor do admin
        usuarios_para_seletor = None
        if current_user.is_admin:
            usuarios_para_seletor = User.query.order_by(User.name).all()

        # Renderiza o template do dashboard passando todos os dados necessários
        return render_template(
            'main/dashboard.html',
            **dados_relatorio, # Desempacota o dicionário de dados
            usuarios=usuarios_para_seletor # Passa a lista de usuários para o admin
        )
    except ValueError as ve:
        logger.error(f"Erro ao carregar dashboard: {ve}", exc_info=True)
        flash(f"Erro ao carregar dados do dashboard: {ve}", 'danger')
        return redirect(url_for('main.index')) # Redireciona para a raiz em caso de erro
    except Exception as e:
        logger.error(f"Erro inesperado no dashboard: {e}", exc_info=True)
        flash("Ocorreu um erro inesperado ao carregar o dashboard.", 'danger')
        return redirect(url_for('main.index'))

# --- ROTAS DE REGISTRO DE PONTO ---
@main.route('/registrar-ponto', methods=['GET', 'POST'])
@login_required
def registrar_ponto():
    """Registra um ponto único para uma data específica."""
    form = RegistroPontoForm()
    hoje = date.today()

    # Preenche a data no GET se vier da URL (ex: calendário)
    if request.method == 'GET':
        data_url = request.args.get('data')
        if data_url:
            try:
                form.data.data = date.fromisoformat(data_url)
            except ValueError:
                flash('Data inválida fornecida na URL.', 'warning')
                form.data.data = hoje

    if form.validate_on_submit():
        data_selecionada = form.data.data
        # Verifica se já existe registro para esta data
        registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
        if registro_existente:
            flash(f'Já existe um registro para {data_selecionada.strftime("%d/%m/%Y")}. Use a opção "Editar" no calendário ou relatório.', 'warning')
            return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")

        try:
            # --- Usa a função auxiliar importada ---
            horas_calc = calcular_horas(
                data_selecionada, form.entrada.data, form.saida.data,
                form.saida_almoco.data, form.retorno_almoco.data
            )
            # ---------------------------------------
            novo_registro = Ponto(
                user_id=current_user.id,
                data=data_selecionada,
                entrada=form.entrada.data,
                saida_almoco=form.saida_almoco.data,
                retorno_almoco=form.retorno_almoco.data,
                saida=form.saida.data,
                horas_trabalhadas=horas_calc,
                observacoes=form.observacoes.data,
                resultados_produtos=form.resultados_produtos.data, # Salva novo campo
                afastamento=False # Registro normal não é afastamento
            )
            db.session.add(novo_registro)
            db.session.flush() # Garante que o ID seja gerado para a atividade

            # Salva atividade se houver descrição
            if form.atividades.data and form.atividades.data.strip():
                nova_atividade = Atividade(ponto_id=novo_registro.id, descricao=form.atividades.data.strip())
                db.session.add(nova_atividade)

            db.session.commit()
            flash('Ponto registrado com sucesso!', 'success')
            return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar ponto para {current_user.email} em {data_selecionada}: {e}", exc_info=True)
            flash('Ocorreu um erro ao registrar o ponto. Tente novamente.', 'danger')

    return render_template('main/registrar_ponto.html', form=form, title="Registrar Ponto")

@main.route('/registrar-multiplo-ponto', methods=['GET', 'POST'])
@login_required
def registrar_multiplo_ponto():
    """Registra múltiplos pontos de uma vez."""
    form = MultiploPontoForm() # Usa o form vazio para CSRF
    hoje = date.today()

    if request.method == 'POST':
        datas = request.form.getlist('datas[]')
        entradas = request.form.getlist('entradas[]')
        saidas_almoco = request.form.getlist('saidas_almoco[]')
        retornos_almoco = request.form.getlist('retornos_almoco[]')
        saidas = request.form.getlist('saidas[]')
        atividades_list = request.form.getlist('atividades[]')
        resultados_list = request.form.getlist('resultados_produtos[]')
        observacoes_list = request.form.getlist('observacoes[]')

        registros_adicionados = 0
        registros_ignorados = 0
        erros = []

        # Garante que todas as listas tenham o mesmo tamanho (preenchendo com None ou string vazia)
        max_len = len(datas)
        entradas.extend([None] * (max_len - len(entradas)))
        saidas_almoco.extend([None] * (max_len - len(saidas_almoco)))
        retornos_almoco.extend([None] * (max_len - len(retornos_almoco)))
        saidas.extend([None] * (max_len - len(saidas)))
        atividades_list.extend([''] * (max_len - len(atividades_list)))
        resultados_list.extend([''] * (max_len - len(resultados_list)))
        observacoes_list.extend([''] * (max_len - len(observacoes_list)))


        for i, data_str in enumerate(datas):
            if not data_str: continue # Pula linhas sem data

            try:
                data_obj = date.fromisoformat(data_str)

                # Verifica se já existe registro
                registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_obj).first()
                if registro_existente:
                    registros_ignorados += 1
                    logger.warning(f"Registro ignorado para {data_obj.strftime('%d/%m/%Y')}: já existe.")
                    continue

                # Converte strings de tempo para objetos time ou None
                entrada_t = time.fromisoformat(entradas[i]) if entradas[i] else None
                saida_almoco_t = time.fromisoformat(saidas_almoco[i]) if saidas_almoco[i] else None
                retorno_almoco_t = time.fromisoformat(retornos_almoco[i]) if retornos_almoco[i] else None
                saida_t = time.fromisoformat(saidas[i]) if saidas[i] else None

                # --- Usa a função auxiliar importada ---
                horas_calc = calcular_horas(data_obj, entrada_t, saida_t, saida_almoco_t, retorno_almoco_t)
                # ---------------------------------------

                novo_registro = Ponto(
                    user_id=current_user.id, data=data_obj,
                    entrada=entrada_t, saida_almoco=saida_almoco_t,
                    retorno_almoco=retorno_almoco_t, saida=saida_t,
                    horas_trabalhadas=horas_calc,
                    atividades_texto=atividades_list[i].strip() if atividades_list[i] else None, # Campo temporário
                    resultados_produtos=resultados_list[i].strip() if resultados_list[i] else None,
                    observacoes=observacoes_list[i].strip() if observacoes_list[i] else None,
                    afastamento=False
                )
                db.session.add(novo_registro)
                db.session.flush() # Para obter o ID

                # Adiciona atividade se existir
                if hasattr(novo_registro, 'atividades_texto') and novo_registro.atividades_texto:
                    nova_atividade = Atividade(ponto_id=novo_registro.id, descricao=novo_registro.atividades_texto)
                    db.session.add(nova_atividade)
                    delattr(novo_registro, 'atividades_texto') # Remove atributo temporário

                registros_adicionados += 1

            except ValueError as ve:
                 erros.append(f"Data ou hora inválida na linha {i+1}: {data_str} / {entradas[i]} / ... ({ve})")
                 logger.error(f"Erro de valor ao processar linha {i+1} do registro múltiplo: {ve}")
            except Exception as e:
                erros.append(f"Erro inesperado ao processar linha {i+1} ({data_str}): {e}")
                logger.error(f"Erro inesperado ao processar linha {i+1} do registro múltiplo: {e}", exc_info=True)
                db.session.rollback() # Desfaz a transação atual em caso de erro grave

        try:
            db.session.commit()
            if registros_adicionados > 0:
                flash(f'{registros_adicionados} registro(s) adicionado(s) com sucesso!', 'success')
            if registros_ignorados > 0:
                flash(f'{registros_ignorados} registro(s) ignorado(s) pois já existiam.', 'info')
            if erros:
                for erro in erros: flash(erro, 'danger')
                return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos", hoje=hoje) # Re-renderiza com erros

            return redirect(url_for('main.dashboard')) # Redireciona se tudo ok ou apenas ignorados

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro final ao commitar registros múltiplos: {e}", exc_info=True)
            flash('Ocorreu um erro crítico ao salvar os registros. Tente novamente.', 'danger')

    # Se for GET, apenas renderiza o formulário
    return render_template('main/registrar_multiplo_ponto.html', form=form, title="Registrar Múltiplos Pontos", hoje=hoje)


@main.route('/registrar-afastamento', methods=['GET', 'POST'])
@login_required
def registrar_afastamento():
    """Registra um dia como afastamento (férias, licença, etc.)."""
    form = RegistroAfastamentoForm()
    hoje = date.today()

    # Preenche a data no GET se vier da URL
    if request.method == 'GET':
        data_url = request.args.get('data')
        if data_url:
            try:
                form.data.data = date.fromisoformat(data_url)
            except ValueError:
                flash('Data inválida fornecida na URL.', 'warning')
                form.data.data = hoje

    if form.validate_on_submit():
        data_selecionada = form.data.data
        tipo_afastamento = form.tipo_afastamento.data

        # Verifica se já existe registro para esta data
        registro_existente = Ponto.query.filter_by(user_id=current_user.id, data=data_selecionada).first()
        if registro_existente:
            # Se já existe, ATUALIZA para afastamento
            try:
                registro_existente.afastamento = True
                registro_existente.tipo_afastamento = tipo_afastamento
                # Limpa horários e horas trabalhadas
                registro_existente.entrada = None
                registro_existente.saida_almoco = None
                registro_existente.retorno_almoco = None
                registro_existente.saida = None
                registro_existente.horas_trabalhadas = None
                # Remove atividades associadas (opcional, mas recomendado para consistência)
                Atividade.query.filter_by(ponto_id=registro_existente.id).delete()
                db.session.commit()
                flash(f'Registro de {data_selecionada.strftime("%d/%m/%Y")} atualizado para {tipo_afastamento} com sucesso!', 'success')
                return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao ATUALIZAR registro para afastamento {data_selecionada}: {e}", exc_info=True)
                flash('Erro ao atualizar registro existente para afastamento.', 'danger')
        else:
            # Se não existe, CRIA um novo registro de afastamento
            try:
                novo_afastamento = Ponto(
                    user_id=current_user.id,
                    data=data_selecionada,
                    afastamento=True,
                    tipo_afastamento=tipo_afastamento
                    # Horários e horas ficam como None por padrão
                )
                db.session.add(novo_afastamento)
                db.session.commit()
                flash(f'Afastamento ({tipo_afastamento}) registrado para {data_selecionada.strftime("%d/%m/%Y")} com sucesso!', 'success')
                return redirect(url_for('main.dashboard', mes=data_selecionada.month, ano=data_selecionada.year))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao CRIAR registro de afastamento para {data_selecionada}: {e}", exc_info=True)
                flash('Erro ao registrar novo afastamento.', 'danger')

    return render_template('main/registrar_afastamento.html', form=form, title="Registrar Afastamento")


# --- ROTAS DE VISUALIZAÇÃO E EDIÇÃO ---
@main.route('/visualizar-ponto/<int:ponto_id>')
@login_required
def visualizar_ponto(ponto_id):
    """Exibe os detalhes de um registro de ponto específico."""
    registro = Ponto.query.get_or_404(ponto_id)
    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para visualizar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    atividades = Atividade.query.filter_by(ponto_id=ponto_id).all()
    usuario = User.query.get(registro.user_id) # Busca o usuário dono do ponto

    return render_template('main/visualizar_ponto.html',
                           registro=registro,
                           atividades=atividades,
                           usuario=usuario, # Passa o usuário para o template
                           title="Visualizar Registro")

@main.route('/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def editar_ponto(ponto_id):
    """Edita um registro de ponto existente."""
    registro = Ponto.query.get_or_404(ponto_id)
    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = EditarPontoForm(obj=registro) # Preenche o form com dados existentes

    # Busca atividade existente para preencher o campo no GET
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    if request.method == 'GET' and atividade_existente:
        form.atividades.data = atividade_existente.descricao

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            # Atualiza os campos do registro
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            registro.resultados_produtos = form.resultados_produtos.data # Salva novo campo

            if is_afastamento:
                # Limpa horários se for afastamento
                registro.entrada = None
                registro.saida_almoco = None
                registro.retorno_almoco = None
                registro.saida = None
                registro.horas_trabalhadas = None
                # Remove atividades se virou afastamento
                if atividade_existente:
                    db.session.delete(atividade_existente)
            else:
                # Atualiza horários e recalcula horas se não for afastamento
                registro.entrada = form.entrada.data
                registro.saida_almoco = form.saida_almoco.data
                registro.retorno_almoco = form.retorno_almoco.data
                registro.saida = form.saida.data
                # --- Usa a função auxiliar importada ---
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada, form.entrada.data, form.saida.data,
                    form.saida_almoco.data, form.retorno_almoco.data
                )
                # ---------------------------------------
                # Atualiza ou cria atividade
                descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
                if descricao_atividade:
                    if atividade_existente:
                        atividade_existente.descricao = descricao_atividade
                    else:
                        nova_atividade = Atividade(ponto_id=ponto_id, descricao=descricao_atividade)
                        db.session.add(nova_atividade)
                elif atividade_existente:
                    # Remove atividade se o campo ficou vazio
                    db.session.delete(atividade_existente)

            db.session.commit()
            flash('Registro atualizado com sucesso!', 'success')
            # Redireciona para visualização ou calendário/dashboard
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao atualizar o registro.', 'danger')

    # Se GET ou validação falhar, renderiza o form de edição
    return render_template('main/editar_ponto.html', form=form, registro=registro, title="Editar Registro")


@main.route('/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
def excluir_ponto(ponto_id):
    """Exclui um registro de ponto."""
    registro = Ponto.query.get_or_404(ponto_id)
    # Verifica permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir este registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    data_registro = registro.data # Guarda a data para redirecionar

    try:
        # Excluir atividades associadas primeiro (se houver cascade="all, delete-orphan" no modelo, isso é automático)
        # Atividade.query.filter_by(ponto_id=ponto_id).delete() # Descomente se não houver cascade

        db.session.delete(registro)
        db.session.commit()
        flash('Registro de ponto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
        flash('Ocorreu um erro ao excluir o registro.', 'danger')

    # Redireciona para o dashboard do mês correspondente
    return redirect(url_for('main.dashboard', mes=data_registro.month, ano=data_registro.year))

# --- ROTAS DE ATIVIDADES ---
@main.route('/registrar-atividade/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
def registrar_atividade(ponto_id):
    """Registra ou edita a atividade de um registro de ponto."""
    ponto = Ponto.query.get_or_404(ponto_id)
    # Verifica permissão
    if ponto.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar atividades deste registro.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Não permite adicionar atividade se for afastamento
    if ponto.afastamento:
        flash('Não é possível adicionar atividades a um registro de afastamento.', 'warning')
        return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))

    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()
    form = AtividadeForm(obj=atividade_existente) # Preenche com dados existentes se houver

    if form.validate_on_submit():
        try:
            if atividade_existente:
                atividade_existente.descricao = form.descricao.data
            else:
                nova_atividade = Atividade(ponto_id=ponto_id, descricao=form.descricao.data)
                db.session.add(nova_atividade)
            db.session.commit()
            flash('Atividade salva com sucesso!', 'success')
            return redirect(url_for('main.visualizar_ponto', ponto_id=ponto_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar atividade para ponto {ponto_id}: {e}", exc_info=True)
            flash('Erro ao salvar atividade.', 'danger')

    title = "Editar Atividade" if atividade_existente else "Registrar Atividade"
    return render_template('main/registrar_atividade.html', form=form, ponto=ponto, title=title)

# --- ROTAS DE CALENDÁRIO E RELATÓRIO ---
@main.route('/calendario')
@login_required
def calendario():
    """Exibe o calendário mensal com os registros de ponto."""
    try:
        user_id_para_visualizar = request.args.get('user_id', default=current_user.id, type=int)

        # Verifica permissão de admin
        if user_id_para_visualizar != current_user.id and not current_user.is_admin:
            flash('Você não tem permissão para visualizar o calendário de outro usuário.', 'danger')
            return redirect(url_for('main.calendario', user_id=current_user.id))

        hoje = date.today()
        mes = request.args.get('mes', default=hoje.month, type=int)
        ano = request.args.get('ano', default=hoje.year, type=int)

        # Validação básica de mês e ano
        if not (1 <= mes <= 12):
            flash("Mês inválido.", 'warning')
            mes = hoje.month
        # Adicione validação de ano se necessário (ex: range razoável)

        # --- Usa a função auxiliar importada ---
        dados_relatorio = _get_relatorio_mensal_data(user_id_para_visualizar, mes, ano)
        # ---------------------------------------

        # Lista de usuários para o seletor do admin
        usuarios_para_seletor = None
        if current_user.is_admin:
            usuarios_para_seletor = User.query.order_by(User.name).all()

        # --- Lógica para gerar a estrutura do calendário ---
        primeiro_dia_mes = date(ano, mes, 1)
        ultimo_dia_mes = dados_relatorio['ultimo_dia']
        # Dia da semana do primeiro dia (0=Seg, 6=Dom) -> Ajustado para iniciar no Domingo (0)
        dia_semana_inicio = (primeiro_dia_mes.weekday() + 1) % 7
        num_dias_mes = ultimo_dia_mes.day

        calendario_data = []
        dia_atual = 1
        for semana in range(6): # Gera no máximo 6 semanas
            linha_semana = []
            for dia_semana in range(7):
                dia_info = {'dia': 0, 'is_mes_atual': False, 'is_hoje': False, 'is_fim_semana': False, 'feriado': None, 'registro': None, 'data': None}
                if semana == 0 and dia_semana < dia_semana_inicio:
                    # Dias do mês anterior (células vazias ou preencher com data anterior)
                    pass # Mantém célula vazia por padrão
                elif dia_atual <= num_dias_mes:
                    # Dia do mês atual
                    data_corrente = date(ano, mes, dia_atual)
                    dia_info['dia'] = dia_atual
                    dia_info['is_mes_atual'] = True
                    dia_info['data'] = data_corrente
                    dia_info['is_hoje'] = (data_corrente == hoje)
                    dia_info['is_fim_semana'] = (data_corrente.weekday() >= 5)
                    dia_info['feriado'] = dados_relatorio['feriados_dict'].get(data_corrente)
                    dia_info['registro'] = dados_relatorio['registros_por_data'].get(data_corrente)
                    dia_atual += 1
                else:
                    # Dias do próximo mês (células vazias)
                    pass # Mantém célula vazia

                linha_semana.append(dia_info)

            calendario_data.append(linha_semana)
            if dia_atual > num_dias_mes: # Para de gerar semanas se já passou o último dia
                break
        # --- Fim da lógica do calendário ---

        return render_template(
            'main/calendario.html',
            **dados_relatorio, # Desempacota o dicionário de dados base
            calendario_data=calendario_data, # Passa a estrutura do calendário
            usuarios=usuarios_para_seletor # Passa a lista de usuários para o admin
        )
    except ValueError as ve:
        logger.error(f"Erro ao carregar calendário: {ve}", exc_info=True)
        flash(f"Erro ao carregar dados do calendário: {ve}", 'danger')
        return redirect(url_for('main.dashboard')) # Redireciona para o dashboard
    except Exception as e:
        logger.error(f"Erro inesperado no calendário: {e}", exc_info=True)
        flash("Ocorreu um erro inesperado ao carregar o calendário.", 'danger')
        return redirect(url_for('main.dashboard'))


@main.route('/relatorio-mensal')
@login_required
def relatorio_mensal():
    """Exibe o relatório mensal detalhado."""
    try:
        user_id_para_visualizar = request.args.get('user_id', default=current_user.id, type=int)

        # Verifica permissão de admin
        if user_id_para_visualizar != current_user.id and not current_user.is_admin:
            flash('Você não tem permissão para visualizar o relatório de outro usuário.', 'danger')
            return redirect(url_for('main.relatorio_mensal', user_id=current_user.id))

        hoje = date.today()
        mes = request.args.get('mes', default=hoje.month, type=int)
        ano = request.args.get('ano', default=hoje.year, type=int)

        # Validação básica de mês e ano
        if not (1 <= mes <= 12):
            flash("Mês inválido.", 'warning')
            mes = hoje.month

        # --- Usa a função auxiliar importada ---
        dados_relatorio = _get_relatorio_mensal_data(user_id_para_visualizar, mes, ano, order_desc=False) # Ordena por data ascendente
        # ---------------------------------------

        # Lista de usuários para o seletor do admin
        usuarios_para_seletor = None
        if current_user.is_admin:
            usuarios_para_seletor = User.query.order_by(User.name).all()

        # --- Lógica para o Formulário de Relatório Completo ---
        form_completo = RelatorioCompletoForm()
        relatorio_completo_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=user_id_para_visualizar, ano=ano, mes=mes
        ).first()

        if relatorio_completo_salvo and request.method == 'GET':
            # Preenche o formulário com dados salvos se existirem (apenas no GET)
            form_completo.autoavaliacao.data = relatorio_completo_salvo.autoavaliacao
            form_completo.dificuldades.data = relatorio_completo_salvo.dificuldades
            form_completo.sugestoes.data = relatorio_completo_salvo.sugestoes
            form_completo.declaracao.data = relatorio_completo_salvo.declaracao_marcada
        elif request.method == 'GET':
             # Preenche campos ocultos no GET para garantir que sejam enviados no POST
             form_completo.user_id.data = user_id_para_visualizar
             form_completo.mes.data = mes
             form_completo.ano.data = ano

        # Renderiza o template do relatório passando todos os dados
        return render_template(
            'main/relatorio_mensal.html',
            **dados_relatorio, # Desempacota o dicionário de dados base
            usuarios=usuarios_para_seletor, # Passa a lista de usuários para o admin
            form_completo=form_completo, # Passa o formulário de autoavaliação
            relatorio_completo_salvo=relatorio_completo_salvo # Indica se já existe relatório salvo
        )
    except ValueError as ve:
        logger.error(f"Erro ao carregar relatório mensal: {ve}", exc_info=True)
        flash(f"Erro ao carregar dados do relatório: {ve}", 'danger')
        return redirect(url_for('main.dashboard')) # Redireciona para o dashboard
    except Exception as e:
        logger.error(f"Erro inesperado no relatório mensal: {e}", exc_info=True)
        flash("Ocorreu um erro inesperado ao carregar o relatório mensal.", 'danger')
        return redirect(url_for('main.dashboard'))

# --- ROTA PARA SALVAR RELATÓRIO COMPLETO ---
@main.route('/salvar-relatorio-completo', methods=['POST'])
@login_required
def salvar_relatorio_completo():
    """Salva ou atualiza os dados da autoavaliação do relatório completo."""
    form = RelatorioCompletoForm() # Cria instância para validar

    # Obtém IDs do formulário (campos ocultos)
    try:
        user_id = int(form.user_id.data)
        mes = int(form.mes.data)
        ano = int(form.ano.data)
    except (TypeError, ValueError):
        flash("Dados inválidos recebidos no formulário.", 'danger')
        # Tenta redirecionar de volta com os parâmetros originais se possível
        user_id_fb = request.args.get('user_id', current_user.id)
        mes_fb = request.args.get('mes', date.today().month)
        ano_fb = request.args.get('ano', date.today().year)
        return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))

    # Verifica permissão
    if user_id != current_user.id and not current_user.is_admin:
        flash("Você não tem permissão para salvar este relatório.", 'danger')
        return redirect(url_for('main.dashboard'))

    if form.validate_on_submit():
        try:
            # Verifica se já existe um relatório salvo para este usuário/mês/ano
            relatorio_existente = RelatorioMensalCompleto.query.filter_by(
                user_id=user_id, ano=ano, mes=mes
            ).first()

            if relatorio_existente:
                # Atualiza o relatório existente
                relatorio_existente.autoavaliacao = form.autoavaliacao.data
                relatorio_existente.dificuldades = form.dificuldades.data
                relatorio_existente.sugestoes = form.sugestoes.data
                relatorio_existente.declaracao_marcada = form.declaracao.data
                flash('Relatório completo atualizado com sucesso!', 'success')
            else:
                # Cria um novo relatório
                novo_relatorio = RelatorioMensalCompleto(
                    user_id=user_id,
                    ano=ano,
                    mes=mes,
                    autoavaliacao=form.autoavaliacao.data,
                    dificuldades=form.dificuldades.data,
                    sugestoes=form.sugestoes.data,
                    declaracao_marcada=form.declaracao.data
                )
                db.session.add(novo_relatorio)
                flash('Relatório completo salvo com sucesso!', 'success')

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar/atualizar relatório completo para user {user_id}, {mes}/{ano}: {e}", exc_info=True)
            flash('Ocorreu um erro ao salvar o relatório completo.', 'danger')
    else:
        # Se a validação falhar, exibe os erros
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    # Redireciona de volta para a página do relatório mensal
    return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

# --- ROTA PARA VISUALIZAR RELATÓRIO COMPLETO SALVO ---
@main.route('/visualizar-relatorio-completo')
@login_required
def visualizar_relatorio_completo():
    """Exibe o relatório completo salvo (com autoavaliação) em formato HTML."""
    try:
        user_id = request.args.get('user_id', type=int)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not user_id or not mes or not ano:
            flash("Informações insuficientes para visualizar o relatório (usuário, mês ou ano ausente).", 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        # Verifica permissão
        if user_id != current_user.id and not current_user.is_admin:
            flash("Você não tem permissão para visualizar este relatório.", 'danger')
            return redirect(url_for('main.dashboard'))

        # Busca o relatório completo salvo
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(user_id=user_id, ano=ano, mes=mes).first()

        if not relatorio_salvo:
            flash("Relatório completo ainda não foi salvo para este período.", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        # --- Usa a função auxiliar importada ---
        dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)
        # ---------------------------------------

        # Cria o contexto completo para o template
        contexto_completo = {
            **dados_relatorio_base,
            'autoavaliacao_data': relatorio_salvo.autoavaliacao,
            'dificuldades_data': relatorio_salvo.dificuldades,
            'sugestoes_data': relatorio_salvo.sugestoes,
            'declaracao_marcada': relatorio_salvo.declaracao_marcada,
            'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y %H:%M:%S'), # Usa data de atualização
            'date_obj': date # Passa o construtor date
        }

        return render_template('main/visualizar_relatorio_completo.html', **contexto_completo)

    except ValueError as ve:
        logger.error(f"ValueError ao visualizar relatório completo: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para visualizar relatório: {ve}.", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao visualizar relatório completo: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao visualizar o relatório completo.', 'danger')

    # Redireciona de volta para a página do relatório mensal em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))


# --- ROTAS DE EXPORTAÇÃO ---
@main.route('/relatorio-pdf')
@login_required
def relatorio_mensal_pdf():
    """Gera e baixa o relatório mensal em PDF."""
    try:
        user_id = request.args.get('user_id', default=current_user.id, type=int)
        mes = request.args.get('mes', default=date.today().month, type=int)
        ano = request.args.get('ano', default=date.today().year, type=int)

        # Verifica permissão
        if user_id != current_user.id and not current_user.is_admin:
            flash('Você não tem permissão para gerar este relatório.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Verifica se existe relatório completo salvo para incluir autoavaliação
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(user_id=user_id, ano=ano, mes=mes).first()
        contexto_completo = None
        if relatorio_salvo:
             # --- Usa a função auxiliar importada ---
             dados_base = _get_relatorio_mensal_data(user_id, mes, ano)
             # ---------------------------------------
             contexto_completo = {
                 **dados_base,
                 'autoavaliacao_data': relatorio_salvo.autoavaliacao,
                 'dificuldades_data': relatorio_salvo.dificuldades,
                 'sugestoes_data': relatorio_salvo.sugestoes,
                 'declaracao_marcada': relatorio_salvo.declaracao_marcada,
                 'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y %H:%M:%S'),
                 'titulo': f'Relatório Completo - {dados_base["nome_mes"]}/{ano}'
             }

        # Gera o PDF (com ou sem autoavaliação)
        pdf_path_relativo = generate_pdf(user_id, mes, ano, context_completo=contexto_completo)

        if pdf_path_relativo:
            # Constrói o caminho absoluto e envia o arquivo
            pdf_path_abs = os.path.join(current_app.static_folder, pdf_path_relativo)
            if os.path.exists(pdf_path_abs):
                 return send_file(pdf_path_abs, as_attachment=True)
            else:
                 logger.error(f"Arquivo PDF não encontrado após geração: {pdf_path_abs}")
                 flash('Erro ao encontrar o arquivo PDF gerado.', 'danger')
        else:
            flash('Erro ao gerar o relatório PDF.', 'danger')

    except ValueError as ve:
        logger.error(f"Erro de valor ao gerar PDF: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para PDF: {ve}", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar PDF: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o PDF.', 'danger')

    # Redireciona de volta em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))

@main.route('/relatorio-excel')
@login_required
def relatorio_mensal_excel():
    """Gera e baixa o relatório mensal em Excel."""
    try:
        user_id = request.args.get('user_id', default=current_user.id, type=int)
        mes = request.args.get('mes', default=date.today().month, type=int)
        ano = request.args.get('ano', default=date.today().year, type=int)

        # Verifica permissão
        if user_id != current_user.id and not current_user.is_admin:
            flash('Você não tem permissão para gerar este relatório.', 'danger')
            return redirect(url_for('main.dashboard'))

        excel_path_relativo = generate_excel(user_id, mes, ano)

        if excel_path_relativo:
            excel_path_abs = os.path.join(current_app.static_folder, excel_path_relativo)
            if os.path.exists(excel_path_abs):
                 return send_file(excel_path_abs, as_attachment=True)
            else:
                 logger.error(f"Arquivo Excel não encontrado após geração: {excel_path_abs}")
                 flash('Erro ao encontrar o arquivo Excel gerado.', 'danger')
        else:
            flash('Erro ao gerar o relatório Excel.', 'danger')

    except ValueError as ve:
        logger.error(f"Erro de valor ao gerar Excel: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para Excel: {ve}", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar Excel: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o Excel.', 'danger')

    # Redireciona de volta em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))


# --- ROTA DE PERFIL ---
@main.route('/perfil')
@login_required
def perfil():
    """Exibe a página de perfil do usuário logado."""
    # A variável current_user já contém o usuário logado
    return render_template('main/perfil.html', usuario=current_user, title="Meu Perfil")

# --- ROTA Gerar HTML SEI ---
@main.route('/relatorio-sei-html')
@login_required
def gerar_html_sei():
    """Gera uma página HTML simplificada do relatório completo para o SEI."""
    try:
        # Tenta obter user_id, mes e ano da URL
        user_id = request.args.get('user_id', type=int)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not user_id or not mes or not ano:
            flash("Informações insuficientes para gerar o HTML (usuário, mês ou ano ausente).", 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        # Verifica permissão
        if user_id != current_user.id and not current_user.is_admin:
            flash("Você não tem permissão para gerar este relatório.", 'danger')
            return redirect(url_for('main.dashboard'))

        # Busca o relatório completo salvo no banco
        relatorio_salvo = RelatorioMensalCompleto.query.filter_by(
            user_id=user_id, ano=ano, mes=mes
        ).first()

        if not relatorio_salvo:
            flash("É necessário salvar o Relatório Completo antes de gerar o HTML para o SEI.", 'warning')
            return redirect(url_for('main.relatorio_mensal', user_id=user_id, mes=mes, ano=ano))

        # --- Usa a função auxiliar importada ---
        dados_relatorio_base = _get_relatorio_mensal_data(user_id, mes, ano)
        # ---------------------------------------

        # Cria o contexto completo para o template HTML SEI
        contexto_completo = {
            **dados_relatorio_base,
            'autoavaliacao_data': relatorio_salvo.autoavaliacao,
            'dificuldades_data': relatorio_salvo.dificuldades,
            'sugestoes_data': relatorio_salvo.sugestoes,
            'declaracao_marcada': relatorio_salvo.declaracao_marcada,
            'data_geracao': relatorio_salvo.updated_at.strftime('%d/%m/%Y'), # Apenas data para SEI
        }

        # Renderiza o novo template HTML SEI
        return render_template('main/relatorio_sei_html.html', **contexto_completo)

    except ValueError as ve:
        logger.error(f"ValueError ao gerar HTML SEI: {ve}", exc_info=True)
        flash(f"Erro ao processar dados para gerar HTML: {ve}.", 'danger')
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar HTML SEI: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado ao gerar o HTML para o SEI.', 'danger')

    # Redireciona de volta para a página do relatório mensal em caso de erro
    user_id_fb = request.args.get('user_id', default=current_user.id, type=int)
    mes_fb = request.args.get('mes', default=date.today().month, type=int)
    ano_fb = request.args.get('ano', default=date.today().year, type=int)
    return redirect(url_for('main.relatorio_mensal', user_id=user_id_fb, mes=mes_fb, ano=ano_fb))
# --- FIM DA NOVA ROTA ---
