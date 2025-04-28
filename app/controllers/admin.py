from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from app.forms.admin import NovoFeriadoForm, EditarFeriadoForm, NovoUsuarioForm, EditarUsuarioForm, DeleteForm
from app import db
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging
import os

admin = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Decorator para exigir permissão de admin
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return decorated_view

# Rota principal do admin
@admin.route('/admin')
@login_required
@admin_required
def index():
    """Página inicial do painel administrativo."""
    return render_template('admin/index.html')

# Rotas para Feriados
@admin.route('/admin/feriados')
@login_required
@admin_required
def listar_feriados():
    """Lista os feriados cadastrados, permitindo filtrar por ano."""
    ano = request.args.get('ano', default=date.today().year, type=int)
    delete_form = DeleteForm() # Formulário para CSRF na exclusão
    try:
        primeiro_dia_ano = date(ano, 1, 1)
        ultimo_dia_ano = date(ano, 12, 31)
        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia_ano,
            Feriado.data <= ultimo_dia_ano
        ).order_by(Feriado.data).all()
    except ValueError:
        flash('Ano inválido selecionado.', 'danger')
        ano = date.today().year
        # Fallback para consulta por ano se a data falhar (menos eficiente em alguns DBs)
        feriados = Feriado.query.filter(
            db.extract('year', Feriado.data) == ano
        ).order_by(Feriado.data).all()
    except Exception as e:
        logger.error(f"Erro ao buscar feriados para o ano {ano}: {e}", exc_info=True)
        flash('Erro ao carregar feriados. Tente novamente.', 'danger')
        feriados = []
        ano = date.today().year

    anos_disponiveis = range(date.today().year - 5, date.today().year + 6)
    return render_template('admin/feriados.html',
                           feriados=feriados,
                           ano_selecionado=ano,
                           anos_disponiveis=anos_disponiveis,
                           delete_form=delete_form)

@admin.route('/admin/feriados/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_feriado():
    """Cria um novo feriado."""
    form = NovoFeriadoForm()
    if form.validate_on_submit():
        try:
            data_feriado = form.data.data
            descricao = form.descricao.data
            feriado_existente = Feriado.query.filter_by(data=data_feriado).first()
            if feriado_existente:
                flash(f'Já existe feriado para {data_feriado.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                novo_feriado_obj = Feriado(data=data_feriado, descricao=descricao)
                db.session.add(novo_feriado_obj)
                db.session.commit()
                flash('Feriado criado com sucesso!', 'success')
                return redirect(url_for('admin.listar_feriados', ano=data_feriado.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar novo feriado: {e}", exc_info=True)
            flash('Erro ao criar feriado. Tente novamente.', 'danger')
    return render_template('admin/novo_feriado.html', form=form, title="Novo Feriado")

@admin.route('/admin/feriados/editar/<int:feriado_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_feriado(feriado_id):
    """Edita um feriado existente."""
    feriado = Feriado.query.get_or_404(feriado_id)
    form = EditarFeriadoForm(obj=feriado) # Preenche o form com dados existentes
    if form.validate_on_submit():
        try:
            nova_data = form.data.data
            nova_descricao = form.descricao.data
            # Verifica se já existe *outro* feriado na nova data
            feriado_existente = Feriado.query.filter(
                Feriado.data == nova_data,
                Feriado.id != feriado_id # Exclui o próprio feriado da verificação
            ).first()
            if feriado_existente:
                flash(f'Já existe outro feriado para {nova_data.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                feriado.data = nova_data
                # Acessa o atributo interno '_nome' que mapeia para 'descricao'
                feriado._nome = nova_descricao
                db.session.commit()
                flash('Feriado atualizado com sucesso!', 'success')
                return redirect(url_for('admin.listar_feriados', ano=nova_data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar feriado {feriado_id}: {e}", exc_info=True)
            flash('Erro ao atualizar feriado. Tente novamente.', 'danger')
    # Passa 'descricao' para o template, usando a propriedade 'nome'
    return render_template('admin/editar_feriado.html', form=form, feriado=feriado, descricao_atual=feriado.nome, title="Editar Feriado")


@admin.route('/admin/feriados/excluir/<int:feriado_id>', methods=['POST'])
@login_required
@admin_required
def excluir_feriado(feriado_id):
    """Exclui um feriado."""
    delete_form = DeleteForm()
    if delete_form.validate_on_submit(): # Valida CSRF
        feriado = Feriado.query.get_or_404(feriado_id)
        ano_feriado = feriado.data.year
        try:
            db.session.delete(feriado)
            db.session.commit()
            flash('Feriado excluído com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao excluir feriado {feriado_id}: {e}", exc_info=True)
            flash('Erro ao excluir feriado. Tente novamente.', 'danger')
        return redirect(url_for('admin.listar_feriados', ano=ano_feriado))
    else:
        flash('Falha na validação CSRF. Tente novamente.', 'danger')
        ano_redirect = request.args.get('ano', date.today().year)
        return redirect(url_for('admin.listar_feriados', ano=ano_redirect))

# --- Rotas de Usuários ---
@admin.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """Lista todos os usuários do sistema."""
    delete_form = DeleteForm() # Para CSRF na exclusão via modal (se implementado)
    try:
        usuarios = User.query.order_by(User.name).all()
    except Exception as e:
        logger.error(f"Erro ao buscar usuários: {e}", exc_info=True)
        flash('Erro ao carregar usuários.', 'danger')
        usuarios = []
    return render_template('admin/usuarios.html', usuarios=usuarios, delete_form=delete_form)

@admin.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_usuario():
    """Cria um novo usuário."""
    form = NovoUsuarioForm()
    if form.validate_on_submit():
        try:
            novo_usuario_obj = User(name=form.name.data, email=form.email.data,
                                 matricula=form.matricula.data, vinculo=form.vinculo.data,
                                 is_admin=form.is_admin.data, is_active_db=form.is_active.data)
            novo_usuario_obj.set_password(form.password.data)
            db.session.add(novo_usuario_obj)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar usuário: {e}", exc_info=True)
            flash('Erro ao criar usuário. Tente novamente.', 'danger')
    return render_template('admin/novo_usuario.html', form=form, title="Novo Usuário")

@admin.route('/admin/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(usuario_id):
    """Edita um usuário existente."""
    usuario = User.query.get_or_404(usuario_id)
    form = EditarUsuarioForm(obj=usuario)
    # Define user_id no form para validação unique (ignorar próprio email/matrícula)
    if request.method == 'GET':
         form.user_id.data = usuario_id # Preenche no GET

    if form.validate_on_submit():
         # Garante que o user_id esteja presente para validação correta no POST
        form.user_id.data = usuario_id
        try:
            usuario.name=form.name.data
            usuario.email=form.email.data
            usuario.matricula=form.matricula.data
            usuario.vinculo=form.vinculo.data
            usuario.is_admin=form.is_admin.data
            usuario.is_active_db=form.is_active.data # Atualiza o status ativo
            if form.password.data: # Atualiza senha apenas se fornecida
                usuario.set_password(form.password.data)
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar usuário {usuario_id}: {e}", exc_info=True)
            flash('Erro ao atualizar usuário. Tente novamente.', 'danger')
    return render_template('admin/editar_usuario.html', form=form, usuario=usuario, title="Editar Usuário")


@admin.route('/admin/usuarios/visualizar/<int:usuario_id>')
@login_required
@admin_required
def visualizar_usuario(usuario_id):
    """Exibe detalhes de um usuário específico."""
    delete_form = DeleteForm() # Para modal de exclusão
    usuario = User.query.get_or_404(usuario_id)
    try:
        # Busca os últimos 10 registros para exibição rápida
        registros = Ponto.query.filter_by(user_id=usuario.id).order_by(Ponto.data.desc()).limit(10).all()
    except Exception as e:
        logger.error(f"Erro ao buscar registros para usuário {usuario_id}: {e}", exc_info=True)
        flash('Erro ao carregar registros recentes do usuário.', 'danger')
        registros = []
    return render_template('admin/visualizar_usuario.html', usuario=usuario, registros=registros, delete_form=delete_form)

@admin.route('/admin/usuarios/excluir/<int:usuario_id>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(usuario_id):
    """Exclui um usuário."""
    delete_form = DeleteForm()
    if delete_form.validate_on_submit(): # Valida CSRF
        if usuario_id == current_user.id:
            flash('Você não pode excluir sua própria conta.', 'danger')
            return redirect(url_for('admin.listar_usuarios'))

        usuario = User.query.get_or_404(usuario_id)
        nome_usuario = usuario.name # Guarda o nome para a mensagem
        try:
            # Exclui o usuário (registros de ponto associados devem ser excluídos em cascata se configurado no modelo)
            db.session.delete(usuario)
            db.session.commit()
            flash(f'Usuário "{nome_usuario}" excluído com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao excluir usuário {usuario_id}: {e}", exc_info=True)
            flash(f'Erro ao excluir o usuário "{nome_usuario}". Verifique se há dependências.', 'danger')
    else:
        flash('Falha na validação CSRF ao tentar excluir. Tente novamente.', 'danger')
    return redirect(url_for('admin.listar_usuarios'))

# --- Rotas de Relatórios ---
@admin.route('/admin/relatorios')
@login_required
@admin_required
def relatorios():
    """Página de seleção de relatórios por usuário."""
    try:
        # Lista usuários ativos para seleção
        usuarios = User.query.filter_by(is_active_db=True).order_by(User.name).all()
    except Exception as e:
        logger.error(f"Erro ao buscar usuários para relatórios: {e}", exc_info=True)
        flash('Erro ao carregar lista de usuários.', 'danger')
        usuarios = []
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/admin/relatorio/<int:usuario_id>')
@login_required
@admin_required
def relatorio_usuario(usuario_id):
    """Exibe o relatório mensal detalhado para um usuário específico (visão do admin)."""
    delete_form = DeleteForm() # Para modal de exclusão de ponto dentro do relatório
    usuario = User.query.get_or_404(usuario_id)
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        if not (1 <= mes <= 12):
            mes = hoje.month
            flash('Mês inválido.', 'warning')

        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])

        registros = Ponto.query.filter(
            Ponto.user_id == usuario.id,
            Ponto.data >= primeiro_dia,
            Ponto.data <= ultimo_dia
        ).order_by(Ponto.data).all()

        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia,
            Feriado.data <= ultimo_dia
        ).all()
        feriados_dict = {f.data: f.descricao for f in feriados}
        feriados_datas = set(feriados_dict.keys())

        registros_por_data = {r.data: r for r in registros}
        ponto_ids = [r.id for r in registros]
        atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
        atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto:
                atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)

        # --- Bloco de Cálculo Revisado ---
        dias_uteis_potenciais = 0
        dias_afastamento = 0
        dias_trabalhados = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano, mes, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                dias_uteis_potenciais += 1
                registro_dia = registros_por_data.get(data_atual)
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1

        for r_data, r_obj in registros_por_data.items():
            if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
                 if r_data.weekday() < 5 and r_data not in feriados_datas:
                     dias_trabalhados += 1
                     horas_trabalhadas += r_obj.horas_trabalhadas

        carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        # --- Fim do Bloco Revisado ---

        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        nome_mes = nomes_meses[mes]
        mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano)
        proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)

        return render_template(
            'admin/relatorio_usuario.html', # Usa template específico de admin
            usuario=usuario, # Passa o usuário sendo visualizado
            registros=registros, registros_por_data=registros_por_data,
            mes_atual=mes, ano_atual=ano, nome_mes=nome_mes,
            dias_uteis=dias_uteis_potenciais, # Envia dias úteis *potenciais*
            dias_trabalhados=dias_trabalhados,
            dias_afastamento=dias_afastamento,
            horas_trabalhadas=horas_trabalhadas,
            carga_horaria_devida=carga_horaria_devida,
            saldo_horas=saldo_horas, media_diaria=media_diaria,
            feriados_dict=feriados_dict, feriados_datas=feriados_datas,
            atividades_por_ponto=atividades_por_ponto, ultimo_dia=ultimo_dia,
            mes_anterior=mes_anterior, ano_anterior=ano_anterior,
            proximo_mes=proximo_mes, proximo_ano=proximo_ano,
            date=date, delete_form=delete_form # Passa form de delete para modais
        )
    except ValueError:
        flash('Data inválida para o relatório.', 'danger')
        return redirect(url_for('admin.relatorios'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório para usuário {usuario_id} ({mes}/{ano}): {e}", exc_info=True)
        flash('Erro ao gerar o relatório do usuário.', 'danger')
        return redirect(url_for('admin.relatorios'))

# Rota de exemplo não implementada (Admin registrando ponto para outro usuário)
@admin.route('/admin/registrar-ponto/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_registrar_ponto(user_id):
    """Placeholder para admin registrar ponto para outro usuário (não implementado)."""
    usuario_alvo = User.query.get_or_404(user_id)
    # Aqui viria a lógica com um formulário similar ao de registro normal,
    # mas salvando com o user_id fornecido.
    flash(f'Funcionalidade de registrar ponto para {usuario_alvo.name} não implementada.', 'info')
    return redirect(url_for('admin.visualizar_usuario', usuario_id=user_id))

# --- CORREÇÃO: Adicionada rota para admin editar ponto de outro usuário ---
@admin.route('/admin/editar-ponto/<int:ponto_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_editar_ponto(ponto_id):
    """Permite que o admin edite o registro de ponto de qualquer usuário."""
    registro = Ponto.query.get_or_404(ponto_id)
    usuario_do_ponto = User.query.get(registro.user_id) # Pega o usuário dono do ponto
    if not usuario_do_ponto:
         flash("Usuário associado a este ponto não encontrado.", "danger")
         return redirect(url_for('admin.listar_usuarios')) # Ou outra rota apropriada

    form = EditarPontoForm(obj=registro)
    atividade_existente = Atividade.query.filter_by(ponto_id=ponto_id).first()

    if request.method == 'GET':
        if atividade_existente and not form.atividades.data:
            form.atividades.data = atividade_existente.descricao

    if form.validate_on_submit():
        try:
            data_selecionada = form.data.data
            is_afastamento = form.afastamento.data
            tipo_afastamento = form.tipo_afastamento.data if is_afastamento else None

            if is_afastamento and not tipo_afastamento:
                 flash('Selecione o Tipo de Afastamento.', 'danger')
                 # Passa o usuário do ponto para renderizar o template corretamente
                 return render_template('admin/editar_ponto_admin.html', form=form, registro=registro, usuario=usuario_do_ponto, title="Admin: Editar Registro")

            # Atualiza os dados do registro (semelhante à edição normal)
            registro.data = data_selecionada
            registro.afastamento = is_afastamento
            registro.tipo_afastamento = tipo_afastamento
            registro.observacoes = form.observacoes.data
            registro.resultados_produtos = form.resultados_produtos.data

            if is_afastamento:
                registro.entrada, registro.saida_almoco, registro.retorno_almoco, registro.saida, registro.horas_trabalhadas = None, None, None, None, None
            else:
                registro.entrada=form.entrada.data
                registro.saida_almoco=form.saida_almoco.data
                registro.retorno_almoco=form.retorno_almoco.data
                registro.saida=form.saida.data
                registro.horas_trabalhadas = calcular_horas(
                    data_selecionada, form.entrada.data, form.saida.data,
                    form.saida_almoco.data, form.retorno_almoco.data
                )

            descricao_atividade = form.atividades.data.strip() if form.atividades.data else None
            if descricao_atividade:
                if atividade_existente: atividade_existente.descricao = descricao_atividade
                else: db.session.add(Atividade(ponto_id=ponto_id, descricao=descricao_atividade))
            elif atividade_existente:
                 db.session.delete(atividade_existente)

            db.session.commit()
            flash(f'Registro de {usuario_do_ponto.name} atualizado com sucesso!', 'success')
            # Redireciona para o relatório do usuário cujo ponto foi editado
            return redirect(url_for('admin.relatorio_usuario', usuario_id=registro.user_id, mes=registro.data.month, ano=registro.data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Admin - Erro ao editar ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao atualizar o registro.', 'danger')

    # Renderiza um template específico para edição de admin (ou o mesmo, ajustado)
    # É importante passar 'usuario' (o dono do ponto) para o template, se ele o utilizar
    return render_template('admin/editar_ponto_admin.html', form=form, registro=registro, usuario=usuario_do_ponto, title="Admin: Editar Registro")
# --- Fim da Correção ---


# --- CORREÇÃO: Adicionada rota para admin excluir ponto de outro usuário ---
@admin.route('/admin/excluir-ponto/<int:ponto_id>', methods=['POST'])
@login_required
@admin_required
def admin_excluir_ponto(ponto_id):
    """Permite que o admin exclua o registro de ponto de qualquer usuário."""
    delete_form = DeleteForm() # Usa o form para validar CSRF
    if delete_form.validate_on_submit():
        registro = Ponto.query.get_or_404(ponto_id)
        usuario_id_dono = registro.user_id # Guarda ID do dono para redirecionar
        data_registro = registro.data

        try:
            db.session.delete(registro)
            db.session.commit()
            flash('Registro de ponto excluído com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Admin - Erro ao excluir ponto {ponto_id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao excluir o registro.', 'danger')

        # Tenta redirecionar para o relatório do usuário
        # Usa request.referrer como fallback se a data não estiver disponível
        redirect_url = url_for('admin.relatorio_usuario', usuario_id=usuario_id_dono, mes=data_registro.month, ano=data_registro.year)
        return redirect(request.referrer or redirect_url)
    else:
         flash('Falha na validação CSRF ao tentar excluir. Tente novamente.', 'danger')
         # Tenta redirecionar de volta para a página anterior
         return redirect(request.referrer or url_for('admin.relatorios'))
# --- Fim da Correção ---
