from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
# Importar DeleteForm
from app.forms.admin import NovoFeriadoForm, EditarFeriadoForm, NovoUsuarioForm, EditarUsuarioForm, DeleteForm
from app import db
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging
import os

admin = Blueprint('admin', __name__)

logger = logging.getLogger(__name__)

# Função helper para verificar se o usuário é admin
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return decorated_view

@admin.route('/admin')
@login_required
@admin_required
def index():
    """Rota para a página inicial do admin."""
    return render_template('admin/index.html')

@admin.route('/admin/feriados')
@login_required
@admin_required
def listar_feriados():
    """Rota para listar os feriados."""
    ano = request.args.get('ano', default=date.today().year, type=int)
    # Instanciar DeleteForm
    delete_form = DeleteForm()
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
        feriados = Feriado.query.filter(
            db.extract('year', Feriado.data) == ano
        ).order_by(Feriado.data).all()
    except Exception as e:
        logger.error(f"Erro ao buscar feriados para o ano {ano}: {e}", exc_info=True)
        flash('Erro ao carregar feriados. Tente novamente.', 'danger')
        feriados = []
        ano = date.today().year

    anos_disponiveis = range(date.today().year - 5, date.today().year + 6)

    # Passar delete_form para o template
    return render_template('admin/feriados.html',
                           feriados=feriados,
                           ano_selecionado=ano,
                           anos_disponiveis=anos_disponiveis,
                           delete_form=delete_form) # Passa o formulário

@admin.route('/admin/feriados/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_feriado():
    """Rota para criar um novo feriado."""
    form = NovoFeriadoForm()
    if form.validate_on_submit():
        try:
            data_feriado = form.data.data
            descricao = form.descricao.data
            feriado_existente = Feriado.query.filter_by(data=data_feriado).first()
            if feriado_existente:
                flash(f'Já existe feriado para {data_feriado.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                novo_feriado = Feriado(data=data_feriado, descricao=descricao)
                db.session.add(novo_feriado)
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
    """Rota para editar um feriado."""
    feriado = Feriado.query.get_or_404(feriado_id)
    form = EditarFeriadoForm(obj=feriado)
    if form.validate_on_submit():
        try:
            nova_data = form.data.data
            nova_descricao = form.descricao.data
            feriado_existente = Feriado.query.filter(
                Feriado.data == nova_data,
                Feriado.id != feriado_id
            ).first()
            if feriado_existente:
                flash(f'Já existe outro feriado para {nova_data.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                feriado.data = nova_data
                feriado.descricao = nova_descricao
                db.session.commit()
                flash('Feriado atualizado com sucesso!', 'success')
                return redirect(url_for('admin.listar_feriados', ano=nova_data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar feriado {feriado_id}: {e}", exc_info=True)
            flash('Erro ao atualizar feriado. Tente novamente.', 'danger')
    return render_template('admin/editar_feriado.html', form=form, feriado=feriado, title="Editar Feriado")

@admin.route('/admin/feriados/excluir/<int:feriado_id>', methods=['POST'])
@login_required
@admin_required
def excluir_feriado(feriado_id):
    """Rota para excluir um feriado."""
    # Validar CSRF usando o DeleteForm
    delete_form = DeleteForm()
    if delete_form.validate_on_submit(): # Valida o token CSRF enviado pelo form no template
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
        ano_redirect = request.args.get('ano', date.today().year) # Pega ano do GET se possível
        return redirect(url_for('admin.listar_feriados', ano=ano_redirect))

# --- Rotas de Usuários ---
@admin.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """Rota para listar os usuários."""
    # --- CORREÇÃO: Instanciar DeleteForm para exclusão na lista ---
    delete_form = DeleteForm()
    # -----------------------------------------------------------
    try: usuarios = User.query.order_by(User.name).all()
    except Exception as e: logger.error(f"Erro buscar usuários: {e}", exc_info=True); flash('Erro ao carregar usuários.', 'danger'); usuarios = []
    # --- CORREÇÃO: Passar delete_form para o template ---
    return render_template('admin/usuarios.html', usuarios=usuarios, delete_form=delete_form)
    # ----------------------------------------------------

@admin.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_usuario():
    """Rota para criar um novo usuário."""
    form = NovoUsuarioForm()
    if form.validate_on_submit():
        try:
            novo_usuario = User(name=form.name.data, email=form.email.data, matricula=form.matricula.data, vinculo=form.vinculo.data, is_admin=form.is_admin.data, is_active_db=form.is_active.data)
            novo_usuario.set_password(form.password.data); db.session.add(novo_usuario); db.session.commit()
            flash('Usuário criado!', 'success'); return redirect(url_for('admin.listar_usuarios'))
        except Exception as e: db.session.rollback(); logger.error(f"Erro criar usuário: {e}", exc_info=True); flash('Erro ao criar usuário.', 'danger')
    return render_template('admin/novo_usuario.html', form=form, title="Novo Usuário")

@admin.route('/admin/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(usuario_id):
    """Rota para editar um usuário."""
    usuario = User.query.get_or_404(usuario_id); form = EditarUsuarioForm(obj=usuario); form.user_id.data = usuario_id # Passa ID para validação
    if form.validate_on_submit():
        try:
            usuario.name=form.name.data; usuario.email=form.email.data; usuario.matricula=form.matricula.data; usuario.vinculo=form.vinculo.data; usuario.is_admin=form.is_admin.data; usuario.is_active_db=form.is_active.data
            if form.password.data: usuario.set_password(form.password.data)
            db.session.commit(); flash('Usuário atualizado!', 'success'); return redirect(url_for('admin.listar_usuarios'))
        except Exception as e: db.session.rollback(); logger.error(f"Erro edit usuário {usuario_id}: {e}", exc_info=True); flash('Erro ao atualizar.', 'danger')
    return render_template('admin/editar_usuario.html', form=form, usuario=usuario, title="Editar Usuário")

@admin.route('/admin/usuarios/visualizar/<int:usuario_id>')
@login_required
@admin_required
def visualizar_usuario(usuario_id):
    """Rota para visualizar um usuário."""
    # --- CORREÇÃO: Instanciar DeleteForm para modal de exclusão ---
    delete_form = DeleteForm()
    # -----------------------------------------------------------
    usuario = User.query.get_or_404(usuario_id)
    try: registros = Ponto.query.filter_by(user_id=usuario.id).order_by(Ponto.data.desc()).limit(10).all()
    except Exception as e: logger.error(f"Erro buscar registros {usuario_id}: {e}", exc_info=True); flash('Erro ao carregar registros.', 'danger'); registros = []
    # --- CORREÇÃO: Passar delete_form para o template ---
    return render_template('admin/visualizar_usuario.html', usuario=usuario, registros=registros, delete_form=delete_form)
    # ----------------------------------------------------

@admin.route('/admin/usuarios/excluir/<int:usuario_id>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(usuario_id):
    """Rota para excluir um usuário."""
    # Usar DeleteForm para validar CSRF
    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        if usuario_id == current_user.id:
            flash('Você não pode excluir sua própria conta.', 'danger')
            return redirect(url_for('admin.listar_usuarios'))
        usuario = User.query.get_or_404(usuario_id); nome_usuario = usuario.name
        try:
            db.session.delete(usuario); db.session.commit()
            flash(f'Usuário "{nome_usuario}" excluído!', 'success')
        except Exception as e:
            db.session.rollback(); logger.error(f"Erro excluir usuário {usuario_id}: {e}", exc_info=True)
            flash(f'Erro ao excluir "{nome_usuario}".', 'danger')
    else:
        flash('Falha na validação CSRF. Tente novamente.', 'danger')
    return redirect(url_for('admin.listar_usuarios'))

# --- Rotas de Relatórios ---
@admin.route('/admin/relatorios')
@login_required
@admin_required
def relatorios():
    """Rota para a página de seleção de relatórios."""
    try: usuarios = User.query.filter_by(is_active_db=True).order_by(User.name).all()
    except Exception as e: logger.error(f"Erro buscar usuários relatórios: {e}", exc_info=True); flash('Erro carregar usuários.', 'danger'); usuarios = []
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/admin/relatorio/<int:usuario_id>')
@login_required
@admin_required
def relatorio_usuario(usuario_id):
    """Rota para o relatório mensal detalhado de um usuário (Admin)."""
    # --- CORREÇÃO: Instanciar DeleteForm para modal de exclusão no relatório ---
    delete_form = DeleteForm()
    # -----------------------------------------------------------------------
    usuario = User.query.get_or_404(usuario_id); hoje = date.today(); mes = request.args.get('mes', default=hoje.month, type=int); ano = request.args.get('ano', default=hoje.year, type=int)
    try:
        # ... (lógica de busca e cálculo mantida) ...
        if not (1 <= mes <= 12): mes = hoje.month; flash('Mês inválido.', 'warning')
        primeiro_dia = date(ano, mes, 1); ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
        registros = Ponto.query.filter(Ponto.user_id == usuario.id, Ponto.data >= primeiro_dia, Ponto.data <= ultimo_dia).order_by(Ponto.data).all()
        feriados = Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all(); feriados_dict = {f.data: f.descricao for f in feriados}; feriados_datas = set(feriados_dict.keys())
        registros_por_data = {r.data: r for r in registros}; ponto_ids = [r.id for r in registros]; atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all(); atividades_por_ponto = {}
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto: atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)
        dias_uteis, dias_trabalhados, dias_afastamento, horas_trabalhadas = 0, 0, 0, 0.0
        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano, mes, dia_num)
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                 registro_dia = registros_por_data.get(data_atual)
                 if registro_dia and registro_dia.afastamento: dias_afastamento += 1
                 else: dias_uteis += 1
        for r in registros:
            if not r.afastamento and r.horas_trabalhadas is not None: dias_trabalhados += 1; horas_trabalhadas += r.horas_trabalhadas
        carga_horaria_devida = dias_uteis * 8.0; saldo_horas = horas_trabalhadas - carga_horaria_devida; media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0
        nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']; nome_mes = nomes_meses[mes]
        mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano); proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)

        # --- CORREÇÃO: Passar delete_form para o template ---
        return render_template('admin/relatorio_usuario.html', usuario=usuario, registros=registros, registros_por_data=registros_por_data, mes_atual=mes, ano_atual=ano, nome_mes=nome_mes, dias_uteis=dias_uteis, dias_trabalhados=dias_trabalhados, dias_afastamento=dias_afastamento, horas_trabalhadas=horas_trabalhadas, carga_horaria_devida=carga_horaria_devida, saldo_horas=saldo_horas, media_diaria=media_diaria, feriados_dict=feriados_dict, feriados_datas=feriados_datas, atividades_por_ponto=atividades_por_ponto, ultimo_dia=ultimo_dia, mes_anterior=mes_anterior, ano_anterior=ano_anterior, proximo_mes=proximo_mes, proximo_ano=proximo_ano, date=date, delete_form=delete_form)
        # ----------------------------------------------------
    except ValueError: flash('Data inválida.', 'danger'); return redirect(url_for('admin.relatorios'))
    except Exception as e: logger.error(f"Erro relatório usuário {usuario_id} ({mes}/{ano}): {e}", exc_info=True); flash('Erro ao gerar relatório.', 'danger'); return redirect(url_for('admin.relatorios'))

# Rota de exemplo não implementada
@admin.route('/admin/registrar-ponto/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_registrar_ponto(user_id):
    usuario_alvo = User.query.get_or_404(user_id)
    flash(f'Funcionalidade não implementada: registrar ponto para {usuario_alvo.name}.', 'info')
    return redirect(url_for('admin.visualizar_usuario', usuario_id=user_id))
