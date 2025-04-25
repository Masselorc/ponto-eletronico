# -*- coding: utf-8 -*-
"""
Controlador para as Funcionalidades de Administração.

Este módulo define as rotas e lógicas relacionadas às tarefas administrativas,
como gerenciamento de usuários, feriados e visualização de relatórios gerais.
Utiliza Flask Blueprints e requer permissão de administrador.
"""

import logging
from datetime import date, timedelta, datetime
import calendar
from io import BytesIO

from flask import (Blueprint, render_template, request, flash, redirect, url_for,
                   send_file, current_app)
from flask_login import login_required, current_user
from sqlalchemy import func, extract, desc # Import desc for ordering

# Importações locais
from app import db
from app.models.user import User
from app.models.ponto import Ponto, Afastamento, Atividade
from app.models.feriado import Feriado
# Importar os formulários de admin
from app.forms.admin import (AdminUserForm, FeriadoForm, RelatorioUsuarioForm,
                             EditarUsuarioForm, EditarFeriadoForm)
from app.utils.helpers import (calcular_saldo_banco_horas, get_feriados_no_mes,
                               get_afastamentos_no_mes, get_atividades_no_mes,
                               calcular_horas_trabalhadas_dia, formatar_timedelta)
from app.utils.export import gerar_relatorio_excel_bytes, gerar_relatorio_pdf_bytes
# CORREÇÃO: Importar admin_required diretamente de app (__init__.py)
from app import admin_required

# Configuração do Blueprint
admin = Blueprint('admin', __name__)

logger = logging.getLogger(__name__)

# --- Rota Principal do Admin (Dashboard) ---

@admin.route('/')
@admin_required
def index():
    """
    Dashboard principal da área administrativa.
    Exibe estatísticas gerais e links para outras seções.
    """
    try:
        total_usuarios = User.query.count()
        total_admins = User.query.filter_by(is_admin=True).count()
        total_feriados = Feriado.query.count()

        # Estatísticas de Ponto (exemplo: registros hoje)
        hoje = date.today()
        registros_hoje = Ponto.query.filter(Ponto.data == hoje).count()

        return render_template('admin/index.html',
                               title="Dashboard Admin",
                               total_usuarios=total_usuarios,
                               total_admins=total_admins,
                               total_feriados=total_feriados,
                               registros_hoje=registros_hoje)
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard admin: {e}", exc_info=True)
        flash("Erro ao carregar o dashboard administrativo.", "danger")
        return redirect(url_for('main.dashboard')) # Redireciona para o dashboard normal em caso de erro

# --- Gerenciamento de Usuários ---

@admin.route('/usuarios')
@admin_required
def listar_usuarios():
    """Lista todos os usuários cadastrados."""
    page = request.args.get('page', 1, type=int)
    per_page = 15 # Usuários por página
    try:
        usuarios_pagination = User.query.order_by(User.nome_completo).paginate(page=page, per_page=per_page, error_out=False)
        usuarios = usuarios_pagination.items
        return render_template('admin/usuarios.html',
                               title="Gerenciar Usuários",
                               usuarios=usuarios,
                               pagination=usuarios_pagination)
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}", exc_info=True)
        flash("Erro ao carregar a lista de usuários.", "danger")
        return redirect(url_for('admin.index'))


@admin.route('/usuarios/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    """Formulário para criar um novo usuário."""
    form = AdminUserForm()
    if form.validate_on_submit():
        try:
            # Validação de duplicidade já está no form (validate_username, validate_email)
            novo_user = User(
                username=form.username.data,
                email=form.email.data,
                nome_completo=form.nome_completo.data,
                cargo=form.cargo.data,
                jornada_diaria=form.jornada_diaria.data,
                is_admin=form.is_admin.data,
                ativo=form.ativo.data # Campo ativo adicionado
            )
            novo_user.set_password(form.password.data)
            db.session.add(novo_user)
            db.session.commit()
            flash(f'Usuário {novo_user.username} criado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar novo usuário: {e}", exc_info=True)
            flash('Erro ao salvar o novo usuário.', 'danger')

    elif request.method == 'POST':
         for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('admin/novo_usuario.html', title="Novo Usuário", form=form)


@admin.route('/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(user_id):
    """Formulário para editar um usuário existente."""
    usuario = User.query.get_or_404(user_id)
    # Passa os dados originais para o formulário para validação de duplicidade
    form = EditarUsuarioForm(original_username=usuario.username, original_email=usuario.email, obj=usuario)

    # Não preenche a senha no GET por segurança
    if request.method == 'GET':
        form.password.data = ""
        form.confirm_password.data = ""

    if form.validate_on_submit():
        try:
            # Validação de duplicidade já está no form (validate_username, validate_email)
            # Atualiza os dados do usuário
            usuario.username = form.username.data
            usuario.email = form.email.data
            usuario.nome_completo = form.nome_completo.data
            usuario.cargo = form.cargo.data
            usuario.jornada_diaria = form.jornada_diaria.data
            usuario.is_admin = form.is_admin.data
            usuario.ativo = form.ativo.data # Atualiza status ativo

            # Atualiza a senha somente se fornecida
            if form.password.data:
                usuario.set_password(form.password.data)
                flash('Senha atualizada.', 'info')

            db.session.commit()
            flash(f'Usuário {usuario.username} atualizado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar usuário {user_id}: {e}", exc_info=True)
            flash('Erro ao salvar as alterações do usuário.', 'danger')

    elif request.method == 'POST':
         for field, errors in form.errors.items():
            # Ignora erro de senha se ela não foi preenchida (é opcional na edição)
            if field == 'password' and 'Este campo é obrigatório.' in errors and not form.password.data:
                continue
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('admin/editar_usuario.html', title="Editar Usuário", form=form, usuario=usuario)


@admin.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
@admin_required
def excluir_usuario(user_id):
    """Exclui um usuário (ou marca como inativo)."""
    # Evitar excluir o próprio usuário logado
    if user_id == current_user.id:
        flash('Você não pode excluir sua própria conta de administrador.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))

    usuario = User.query.get_or_404(user_id)
    try:
        # Opção 1: Exclusão lógica (marcar como inativo) - MAIS SEGURO
        # usuario.ativo = False
        # db.session.commit()
        # flash(f'Usuário {usuario.username} desativado com sucesso.', 'success')

        # Opção 2: Exclusão física (REMOVE DO BANCO) - CUIDADO!
        # Pode causar problemas se houver registros associados (pontos, etc.)
        # É necessário configurar cascade delete ou tratar os registros órfãos.
        # Antes de excluir, verificar/tratar dependências:
        pontos_usuario = Ponto.query.filter_by(user_id=user_id).count()
        afastamentos_usuario = Afastamento.query.filter_by(user_id=user_id).count()
        atividades_usuario = Atividade.query.filter_by(user_id=user_id).count()

        if pontos_usuario > 0 or afastamentos_usuario > 0 or atividades_usuario > 0:
             flash(f'Não é possível excluir {usuario.username}. Existem {pontos_usuario} pontos, {afastamentos_usuario} afastamentos e {atividades_usuario} atividades associados. Considere desativar o usuário.', 'danger')
             return redirect(url_for('admin.listar_usuarios'))

        # Se não houver dependências, prossegue com a exclusão física
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuário {usuario.username} excluído permanentemente com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir/desativar usuário {user_id}: {e}", exc_info=True)
        flash('Erro ao tentar excluir/desativar o usuário.', 'danger')

    return redirect(url_for('admin.listar_usuarios'))

# --- Gerenciamento de Feriados ---

@admin.route('/feriados')
@admin_required
def listar_feriados():
    """Lista todos os feriados cadastrados."""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    try:
        feriados_pagination = Feriado.query.order_by(Feriado.data).paginate(page=page, per_page=per_page, error_out=False)
        feriados = feriados_pagination.items
        return render_template('admin/feriados.html',
                               title="Gerenciar Feriados",
                               feriados=feriados,
                               pagination=feriados_pagination)
    except Exception as e:
        logger.error(f"Erro ao listar feriados: {e}", exc_info=True)
        flash("Erro ao carregar a lista de feriados.", "danger")
        return redirect(url_for('admin.index'))


@admin.route('/feriados/novo', methods=['GET', 'POST'])
@admin_required
def novo_feriado():
    """Formulário para adicionar um novo feriado."""
    form = FeriadoForm() # Usa o FeriadoForm base
    if form.validate_on_submit():
        try:
            # Validação de duplicidade já está no form
            novo_feriado = Feriado(
                data=form.data.data,
                descricao=form.descricao.data
            )
            db.session.add(novo_feriado)
            db.session.commit()
            flash(f'Feriado "{novo_feriado.descricao}" em {novo_feriado.data.strftime("%d/%m/%Y")} adicionado com sucesso!', 'success')
            return redirect(url_for('admin.listar_feriados'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar novo feriado: {e}", exc_info=True)
            flash('Erro ao salvar o novo feriado.', 'danger')

    elif request.method == 'POST':
         for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('admin/novo_feriado.html', title="Novo Feriado", form=form)


@admin.route('/feriados/editar/<int:feriado_id>', methods=['GET', 'POST'])
@admin_required
def editar_feriado(feriado_id):
    """Formulário para editar um feriado existente."""
    feriado = Feriado.query.get_or_404(feriado_id)
    # Passa a data original para o formulário para validação
    form = EditarFeriadoForm(original_data=feriado.data, obj=feriado)

    if form.validate_on_submit():
        try:
            # Validação de duplicidade já está no form
            feriado.data = form.data.data
            feriado.descricao = form.descricao.data
            db.session.commit()
            flash(f'Feriado "{feriado.descricao}" atualizado com sucesso!', 'success')
            return redirect(url_for('admin.listar_feriados'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar feriado {feriado_id}: {e}", exc_info=True)
            flash('Erro ao salvar as alterações do feriado.', 'danger')

    elif request.method == 'POST':
         for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('admin/editar_feriado.html', title="Editar Feriado", form=form, feriado=feriado)


@admin.route('/feriados/excluir/<int:feriado_id>', methods=['POST'])
@admin_required
def excluir_feriado(feriado_id):
    """Exclui um feriado."""
    feriado = Feriado.query.get_or_404(feriado_id)
    try:
        db.session.delete(feriado)
        db.session.commit()
        flash(f'Feriado "{feriado.descricao}" ({feriado.data.strftime("%d/%m/%Y")}) excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir feriado {feriado_id}: {e}", exc_info=True)
        flash('Erro ao tentar excluir o feriado.', 'danger')

    return redirect(url_for('admin.listar_feriados'))

# --- Relatórios Administrativos ---

@admin.route('/relatorios', methods=['GET', 'POST'])
@admin_required
def relatorios_admin():
    """Página para seleção de relatórios administrativos."""
    form = RelatorioUsuarioForm()
    # Preenche choices dinamicamente
    form.usuario.choices = [(0, 'Selecione um usuário...')] + [(u.id, u.nome_completo) for u in User.query.filter_by(ativo=True).order_by(User.nome_completo).all()]

    if form.validate_on_submit():
        user_id = form.usuario.data
        mes = form.mes.data
        ano = form.ano.data
        formato = form.formato.data

        if user_id == 0: # Verifica se um usuário válido foi selecionado
            flash("Por favor, selecione um usuário.", "warning")
        else:
            # Redireciona para a rota que gera o relatório específico
            return redirect(url_for('admin.gerar_relatorio_usuario',
                                    user_id=user_id, mes=mes, ano=ano, formato=formato))

    # Gera lista de anos para o formulário
    ano_atual = datetime.now().year
    anos_disponiveis = list(range(ano_atual - 5, ano_atual + 2)) # Ex: últimos 5 anos + próximo ano
    form.ano.choices = [(a, str(a)) for a in reversed(anos_disponiveis)]
    # Define o ano atual como padrão se for a primeira vez
    if request.method == 'GET':
        form.ano.data = ano_atual
        form.mes.data = datetime.now().month

    return render_template('admin/relatorios.html', title="Relatórios", form=form)


@admin.route('/relatorios/usuario/<int:user_id>')
@admin_required
def gerar_relatorio_usuario(user_id):
    """Gera e retorna o relatório de ponto mensal para um usuário específico."""
    usuario = User.query.get_or_404(user_id)
    ano = request.args.get('ano', default=datetime.now().year, type=int)
    mes = request.args.get('mes', default=datetime.now().month, type=int)
    formato = request.args.get('formato', default='pdf', type=str).lower()

    try:
        # Lógica de cálculo do relatório (similar à rota main.exportar_relatorio)
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
        pontos_mes = Ponto.query.filter(
            Ponto.user_id == user_id,
            Ponto.data >= inicio_mes,
            Ponto.data <= fim_mes
        ).order_by(Ponto.data, Ponto.hora).all()

        feriados_mes = get_feriados_no_mes(ano, mes)
        afastamentos_mes = get_afastamentos_no_mes(user_id, ano, mes)
        atividades_mes = get_atividades_no_mes(user_id, ano, mes)

        pontos_por_dia = {}
        for ponto in pontos_mes:
            if ponto.data not in pontos_por_dia:
                pontos_por_dia[ponto.data] = []
            pontos_por_dia[ponto.data].append(ponto)

        relatorio_dias = []
        jornada_diaria = timedelta(hours=usuario.jornada_diaria)
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
                horas_trabalhadas = jornada_diaria # Considera como jornada cumprida para fins de relatório
            elif atividade_dia:
                 saldo_dia = timedelta(0)
                 status_dia = f"Atividade Ext./HO ({atividade_dia.descricao})" # Ajuste na descrição
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
                if not pontos_dia: # Apenas marca falta se não houver ponto E for dia útil sem outras ocorrências
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

        # Calcula saldo total (pode ser diferente do saldo do mês)
        saldo_banco_horas_total = calcular_saldo_banco_horas(user_id) # Calcula para o usuário específico

        # Dados para passar para as funções de exportação
        dados_relatorio = {
            'usuario': usuario, # Passa o objeto User completo
            'ano': ano,
            'mes': mes,
            'nome_mes': calendar.month_name[mes].capitalize(),
            'relatorio_dias': relatorio_dias,
            'saldo_mes': saldo_acumulado,
            'saldo_total': saldo_banco_horas_total,
            'jornada_diaria': jornada_diaria
        }

        # Gera o arquivo no formato solicitado
        if formato == 'pdf':
            html_content = render_template('exports/relatorio_ponto_pdf.html', **dados_relatorio)
            pdf_bytes = gerar_relatorio_pdf_bytes(html_content)
            if pdf_bytes:
                filename = f"relatorio_{usuario.username}_{ano}_{mes:02d}.pdf"
                return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=filename)
            else:
                flash('Erro ao gerar o relatório PDF.', 'danger')
        elif formato == 'excel':
            excel_bytes = gerar_relatorio_excel_bytes(dados_relatorio)
            if excel_bytes:
                filename = f"relatorio_{usuario.username}_{ano}_{mes:02d}.xlsx"
                return send_file(BytesIO(excel_bytes), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=filename)
            else:
                flash('Erro ao gerar o relatório Excel.', 'danger')
        else:
            flash('Formato de relatório inválido.', 'warning')

    except ValueError:
        flash('Data inválida fornecida para o relatório.', 'danger')
    except Exception as e:
        logger.error(f"Erro ao gerar relatório ({formato}) para usuário {user_id}, {mes}/{ano}: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao gerar o relatório em {formato.upper()}.', 'danger')

    # Redireciona de volta para a página de seleção de relatórios em caso de erro
    return redirect(url_for('admin.relatorios_admin'))


@admin.route('/usuarios/visualizar/<int:user_id>')
@admin_required
def visualizar_usuario(user_id):
    """Exibe detalhes de um usuário específico."""
    usuario = User.query.get_or_404(user_id)
    try:
        # Calcula saldo de banco de horas total para exibir
        saldo_total = calcular_saldo_banco_horas(user_id)

        # Busca últimos registros de ponto (exemplo: últimos 10)
        ultimos_pontos = Ponto.query.filter_by(user_id=user_id).order_by(Ponto.timestamp.desc()).limit(10).all()

        return render_template('admin/visualizar_usuario.html',
                               title=f"Detalhes de {usuario.username}",
                               usuario=usuario,
                               saldo_total=saldo_total,
                               ultimos_pontos=ultimos_pontos)
    except Exception as e:
        logger.error(f"Erro ao visualizar usuário {user_id}: {e}", exc_info=True)
        flash("Erro ao carregar detalhes do usuário.", "danger")
        return redirect(url_for('admin.listar_usuarios'))

