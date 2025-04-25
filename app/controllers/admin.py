from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto, Atividade # Adicionada importação de Atividade
from app.models.feriado import Feriado
from app.forms.admin import NovoFeriadoForm, EditarFeriadoForm, NovoUsuarioForm, EditarUsuarioForm
from app import db # Importar db diretamente
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging
import os

admin = Blueprint('admin', __name__)

logger = logging.getLogger(__name__)

# Função helper para verificar se o usuário é admin
def admin_required(func):
    @wraps(func) # Preserva metadados da função original
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return decorated_view

@admin.route('/admin')
@login_required
@admin_required # Usando o decorator
def index():
    """Rota para a página inicial do admin."""
    # A verificação de admin já é feita pelo decorator
    return render_template('admin/index.html')

@admin.route('/admin/feriados')
@login_required
@admin_required
def listar_feriados():
    """Rota para listar os feriados."""
    # Obtém o ano da query string, default para o ano atual
    ano = request.args.get('ano', default=date.today().year, type=int)

    try:
        # Obtém os feriados do ano selecionado
        primeiro_dia_ano = date(ano, 1, 1)
        ultimo_dia_ano = date(ano, 12, 31)

        feriados = Feriado.query.filter(
            Feriado.data >= primeiro_dia_ano,
            Feriado.data <= ultimo_dia_ano
        ).order_by(Feriado.data).all()

    except ValueError:
        # Lidar com ano inválido (ex: fora do range suportado por date)
        flash('Ano inválido selecionado.', 'danger')
        ano = date.today().year # Resetar para o ano atual
        feriados = Feriado.query.filter(
            db.extract('year', Feriado.data) == ano
        ).order_by(Feriado.data).all()
    except Exception as e:
        logger.error(f"Erro ao buscar feriados para o ano {ano}: {e}", exc_info=True)
        flash('Erro ao carregar feriados. Tente novamente.', 'danger')
        feriados = []
        ano = date.today().year # Resetar para o ano atual

    # Anos disponíveis para seleção (ex: ano atual +/- 5 anos)
    anos_disponiveis = range(date.today().year - 5, date.today().year + 6)

    return render_template('admin/feriados.html', feriados=feriados, ano_selecionado=ano, anos_disponiveis=anos_disponiveis)

# Alias para a rota listar_feriados para compatibilidade (se necessário)
# @admin.route('/admin/feriados') # Comentado pois a rota acima já existe
# @login_required
# @admin_required
# def feriados():
#     """Alias para a rota listar_feriados."""
#     return listar_feriados()

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

            # Verificar se já existe um feriado com a mesma data
            feriado_existente = Feriado.query.filter_by(data=data_feriado).first()
            if feriado_existente:
                flash(f'Já existe um feriado cadastrado para a data {data_feriado.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                # Cria um novo feriado
                novo_feriado = Feriado(
                    data=data_feriado,
                    descricao=descricao # Usando o atributo correto do modelo
                )
                db.session.add(novo_feriado)
                db.session.commit()
                flash('Feriado criado com sucesso!', 'success')
                return redirect(url_for('admin.listar_feriados', ano=data_feriado.year)) # Redireciona para o ano do feriado criado
        except Exception as e:
            db.session.rollback() # Desfaz alterações em caso de erro
            logger.error(f"Erro ao criar novo feriado: {e}", exc_info=True)
            flash('Erro ao criar feriado. Tente novamente.', 'danger')

    return render_template('admin/novo_feriado.html', form=form, title="Novo Feriado") # Adicionado title

@admin.route('/admin/feriados/editar/<int:feriado_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_feriado(feriado_id):
    """Rota para editar um feriado."""
    feriado = Feriado.query.get_or_404(feriado_id)
    # Passa o objeto feriado para o formulário para preencher os campos
    form = EditarFeriadoForm(obj=feriado)

    if form.validate_on_submit():
        try:
            nova_data = form.data.data
            nova_descricao = form.descricao.data

            # Verificar se já existe outro feriado com a nova data
            feriado_existente = Feriado.query.filter(
                Feriado.data == nova_data,
                Feriado.id != feriado_id # Exclui o próprio feriado da verificação
            ).first()

            if feriado_existente:
                flash(f'Já existe outro feriado cadastrado para a data {nova_data.strftime("%d/%m/%Y")}: {feriado_existente.descricao}', 'danger')
            else:
                # Atualiza os dados do feriado
                feriado.data = nova_data
                # Usa o setter da propriedade 'nome' que atualiza '_nome' (coluna 'descricao')
                feriado.descricao = nova_descricao
                db.session.commit()
                flash('Feriado atualizado com sucesso!', 'success')
                return redirect(url_for('admin.listar_feriados', ano=nova_data.year))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar feriado {feriado_id}: {e}", exc_info=True)
            flash('Erro ao atualizar feriado. Tente novamente.', 'danger')

    # Preenche o formulário com os dados atuais se for GET
    # (obj=feriado no construtor já faz isso, mas pode ser feito explicitamente aqui também se necessário)
    # form.data.data = feriado.data
    # form.descricao.data = feriado.descricao

    return render_template('admin/editar_feriado.html', form=form, feriado=feriado, title="Editar Feriado") # Adicionado title

@admin.route('/admin/feriados/excluir/<int:feriado_id>', methods=['POST']) # Apenas POST para exclusão
@login_required
@admin_required
def excluir_feriado(feriado_id):
    """Rota para excluir um feriado."""
    feriado = Feriado.query.get_or_404(feriado_id)
    ano_feriado = feriado.data.year # Guarda o ano antes de excluir

    try:
        db.session.delete(feriado)
        db.session.commit()
        flash('Feriado excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir feriado {feriado_id}: {e}", exc_info=True)
        flash('Erro ao excluir feriado. Tente novamente.', 'danger')

    return redirect(url_for('admin.listar_feriados', ano=ano_feriado))

# --- Rotas de Usuários ---

@admin.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """Rota para listar os usuários."""
    try:
        # Obtém todos os usuários ordenados por nome
        usuarios = User.query.order_by(User.name).all()
    except Exception as e:
        logger.error(f"Erro ao buscar usuários: {e}", exc_info=True)
        flash('Erro ao carregar lista de usuários.', 'danger')
        usuarios = []

    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_usuario():
    """Rota para criar um novo usuário."""
    form = NovoUsuarioForm()

    if form.validate_on_submit():
        try:
            # Verifica se o email já está em uso
            usuario_existente_email = User.query.filter_by(email=form.email.data).first()
            if usuario_existente_email:
                flash('Este email já está em uso.', 'danger')
                # Retorna o template com o formulário preenchido e a mensagem de erro
                return render_template('admin/novo_usuario.html', form=form, title="Novo Usuário")

            # Verifica se a matrícula já está em uso
            usuario_existente_matricula = User.query.filter_by(matricula=form.matricula.data).first()
            if usuario_existente_matricula:
                flash('Esta matrícula já está em uso.', 'danger')
                return render_template('admin/novo_usuario.html', form=form, title="Novo Usuário")

            # Cria um novo usuário
            novo_usuario = User(
                name=form.name.data,
                email=form.email.data,
                matricula=form.matricula.data,
                vinculo=form.vinculo.data,
                is_admin=form.is_admin.data,
                # --- CORREÇÃO: Usar a nova coluna is_active_db ---
                is_active_db=form.is_active.data
                # -------------------------------------------------
                # Campos adicionais do modelo User que podem estar no form (ajustar form se necessário)
                # cargo=form.cargo.data,
                # uf=form.uf.data,
                # telefone=form.telefone.data,
                # foto_path=... # Lógica para salvar foto aqui
            )

            # Define a senha
            novo_usuario.set_password(form.password.data)

            db.session.add(novo_usuario)
            db.session.commit()

            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar novo usuário: {e}", exc_info=True)
            flash('Erro ao criar usuário. Verifique os dados e tente novamente.', 'danger')

    return render_template('admin/novo_usuario.html', form=form, title="Novo Usuário")

@admin.route('/admin/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(usuario_id):
    """Rota para editar um usuário."""
    usuario = User.query.get_or_404(usuario_id)
    # Passa o objeto usuario para o formulário preencher os campos no GET
    form = EditarUsuarioForm(obj=usuario)

    if form.validate_on_submit():
        try:
            # Verifica se o email já está em uso por outro usuário
            usuario_existente_email = User.query.filter(
                User.email == form.email.data,
                User.id != usuario_id
            ).first()
            if usuario_existente_email:
                flash('Este email já está em uso por outro usuário.', 'danger')
                # Retorna o template com o formulário preenchido e a mensagem de erro
                return render_template('admin/editar_usuario.html', form=form, usuario=usuario, title="Editar Usuário")

             # Verifica se a matrícula já está em uso por outro usuário
            usuario_existente_matricula = User.query.filter(
                User.matricula == form.matricula.data,
                User.id != usuario_id
            ).first()
            if usuario_existente_matricula:
                flash('Esta matrícula já está em uso por outro usuário.', 'danger')
                return render_template('admin/editar_usuario.html', form=form, usuario=usuario, title="Editar Usuário")

            # Atualiza os dados do usuário
            usuario.name = form.name.data
            usuario.email = form.email.data
            usuario.matricula = form.matricula.data
            usuario.vinculo = form.vinculo.data
            usuario.is_admin = form.is_admin.data
            # --- CORREÇÃO: Usar a nova coluna is_active_db ---
            usuario.is_active_db = form.is_active.data
            # -------------------------------------------------
            # Atualizar outros campos se existirem no formulário
            # usuario.cargo = form.cargo.data
            # usuario.uf = form.uf.data
            # usuario.telefone = form.telefone.data
            # Lógica para atualizar foto aqui, se aplicável

            # Atualiza a senha apenas se fornecida no formulário
            if form.password.data:
                usuario.set_password(form.password.data)

            db.session.commit()

            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin.listar_usuarios'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar usuário {usuario_id}: {e}", exc_info=True)
            flash('Erro ao atualizar usuário. Verifique os dados e tente novamente.', 'danger')

    # No método GET, o formulário já foi preenchido com obj=usuario
    # Se precisar preencher manualmente (geralmente não necessário com obj=):
    # form.name.data = usuario.name
    # form.email.data = usuario.email
    # ... e assim por diante

    return render_template('admin/editar_usuario.html', form=form, usuario=usuario, title="Editar Usuário")

@admin.route('/admin/usuarios/visualizar/<int:usuario_id>')
@login_required
@admin_required
def visualizar_usuario(usuario_id):
    """Rota para visualizar um usuário."""
    usuario = User.query.get_or_404(usuario_id)

    try:
        # Obtém os últimos 10 registros de ponto do usuário para exibição rápida
        registros = Ponto.query.filter_by(user_id=usuario.id).order_by(Ponto.data.desc()).limit(10).all()
    except Exception as e:
        logger.error(f"Erro ao buscar registros para usuário {usuario_id}: {e}", exc_info=True)
        flash('Erro ao carregar registros recentes do usuário.', 'danger')
        registros = []

    return render_template('admin/visualizar_usuario.html', usuario=usuario, registros=registros)

# --- Rota de Exclusão de Usuário ---
@admin.route('/admin/usuarios/excluir/<int:usuario_id>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(usuario_id):
    """Rota para excluir um usuário."""
    # Evitar auto-exclusão
    if usuario_id == current_user.id:
        flash('Você não pode excluir sua própria conta de administrador.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))

    usuario = User.query.get_or_404(usuario_id)
    nome_usuario = usuario.name # Guarda o nome para a mensagem flash

    try:
        # Exclui o usuário (e seus pontos/atividades devido ao cascade)
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuário "{nome_usuario}" excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir usuário {usuario_id}: {e}", exc_info=True)
        flash(f'Erro ao excluir o usuário "{nome_usuario}". Tente novamente.', 'danger')

    return redirect(url_for('admin.listar_usuarios'))


# --- Rotas de Relatórios ---

@admin.route('/admin/relatorios')
@login_required
@admin_required
def relatorios():
    """Rota para a página de seleção de relatórios."""
    try:
        # Obtém todos os usuários ativos ordenados por nome
        usuarios = User.query.filter_by(is_active_db=True).order_by(User.name).all() # CORREÇÃO: usar is_active_db
    except Exception as e:
        logger.error(f"Erro ao buscar usuários para relatórios: {e}", exc_info=True)
        flash('Erro ao carregar lista de usuários para relatórios.', 'danger')
        usuarios = []

    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/admin/relatorio/<int:usuario_id>')
@login_required
@admin_required
def relatorio_usuario(usuario_id):
    """Rota para o relatório mensal detalhado de um usuário."""
    usuario = User.query.get_or_404(usuario_id)

    # Obtém o mês e ano da query string, default para o mês/ano atual
    hoje = date.today()
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    try:
        # Valida mês e ano
        if not (1 <= mes <= 12):
            mes = hoje.month
            flash('Mês inválido. Exibindo mês atual.', 'warning')
        # Adicionar validação de ano se necessário

        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])

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
        feriados_dict = {feriado.data: feriado.descricao for feriado in feriados}
        feriados_datas = set(feriados_dict.keys()) # Usar set para busca mais rápida

        # Cria dicionário de registros por data para acesso fácil no template
        registros_por_data = {registro.data: registro for registro in registros}

        # Calcula estatísticas (dias úteis, trabalhados, afastamento, horas, etc.)
        dias_uteis = 0
        dias_trabalhados = 0
        dias_afastamento = 0
        horas_trabalhadas = 0.0

        for dia_num in range(1, ultimo_dia.day + 1):
            data_atual = date(ano, mes, dia_num)
            registro_dia = registros_por_data.get(data_atual)

            # Verifica se é dia útil (seg-sex) e não é feriado
            if data_atual.weekday() < 5 and data_atual not in feriados_datas:
                if registro_dia and registro_dia.afastamento:
                    dias_afastamento += 1
                else:
                    # Só conta como dia útil se não for afastamento
                    dias_uteis += 1
                    if registro_dia and registro_dia.horas_trabalhadas is not None:
                        dias_trabalhados += 1
                        horas_trabalhadas += registro_dia.horas_trabalhadas
            # Se não for dia útil ou for feriado, mas houve registro (ex: trabalho no feriado)
            elif registro_dia and not registro_dia.afastamento and registro_dia.horas_trabalhadas is not None:
                 dias_trabalhados += 1 # Conta como trabalhado
                 horas_trabalhadas += registro_dia.horas_trabalhadas # Adiciona as horas

        # Carga horária devida (considera apenas dias úteis que não foram de afastamento)
        carga_horaria_devida = dias_uteis * 8.0 # 8 horas por dia útil não afastado
        saldo_horas = horas_trabalhadas - carga_horaria_devida
        media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

        # Nomes dos meses
        nomes_meses = [
            '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        nome_mes = nomes_meses[mes]

        # Mês/Ano anterior e próximo para navegação
        mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano)
        proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)

        return render_template('admin/relatorio_usuario.html',
                              usuario=usuario,
                              registros=registros, # Passa a lista ordenada
                              registros_por_data=registros_por_data, # Passa o dicionário
                              mes_atual=mes,
                              ano_atual=ano,
                              nome_mes=nome_mes,
                              dias_uteis=dias_uteis,
                              dias_trabalhados=dias_trabalhados,
                              dias_afastamento=dias_afastamento,
                              horas_trabalhadas=horas_trabalhadas,
                              carga_horaria_devida=carga_horaria_devida,
                              saldo_horas=saldo_horas,
                              media_diaria=media_diaria,
                              feriados_dict=feriados_dict,
                              feriados_datas=feriados_datas, # Passa o set de datas
                              ultimo_dia=ultimo_dia, # Passa o objeto date
                              mes_anterior=mes_anterior,
                              ano_anterior=ano_anterior,
                              proximo_mes=proximo_mes,
                              proximo_ano=proximo_ano,
                              date=date # Passa a classe date para o template
                              )

    except ValueError:
        flash('Data inválida selecionada.', 'danger')
        return redirect(url_for('admin.relatorios'))
    except Exception as e:
        logger.error(f"Erro ao gerar relatório para usuário {usuario_id} ({mes}/{ano}): {e}", exc_info=True)
        flash('Erro ao gerar relatório. Tente novamente.', 'danger')
        return redirect(url_for('admin.relatorios'))

# --- Rotas de Exportação (PDF/Excel) ---
# Estas rotas foram movidas para main.py e admin.py chama as rotas de main
# com o user_id correto. Isso evita duplicação de código.

# @admin.route('/admin/relatorio/<int:usuario_id>/pdf')
# @login_required
# @admin_required
# def relatorio_usuario_pdf(usuario_id):
#     """Rota para gerar o relatório em PDF."""
#     # ... (lógica similar a main.relatorio_mensal_pdf, mas para admin)
#     # Idealmente, chamar uma função utilitária ou redirecionar para a rota principal
#     mes = request.args.get('mes', type=int, default=date.today().month)
#     ano = request.args.get('ano', type=int, default=date.today().year)
#     return redirect(url_for('main.relatorio_mensal_pdf', user_id=usuario_id, mes=mes, ano=ano))


# @admin.route('/admin/relatorio/<int:usuario_id>/excel')
# @login_required
# @admin_required
# def relatorio_usuario_excel(usuario_id):
#     """Rota para gerar o relatório em Excel."""
#     # ... (lógica similar a main.relatorio_mensal_excel, mas para admin)
#     # Idealmente, chamar uma função utilitária ou redirecionar para a rota principal
#     mes = request.args.get('mes', type=int, default=date.today().month)
#     ano = request.args.get('ano', type=int, default=date.today().year)
#     return redirect(url_for('main.relatorio_mensal_excel', user_id=usuario_id, mes=mes, ano=ano))

# --- Rota para adicionar ponto para outro usuário (Admin) ---
# Exemplo de como poderia ser, mas não estava nos arquivos originais
@admin.route('/admin/registrar-ponto/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_registrar_ponto(user_id):
    """Permite ao admin registrar ponto para outro usuário."""
    usuario_alvo = User.query.get_or_404(user_id)
    # Usar um formulário similar ao RegistroPontoForm, mas talvez sem validação de usuário atual
    # A lógica seria muito parecida com main.registrar_ponto, mas usando usuario_alvo.id
    # ... (Implementar lógica de formulário e salvamento)
    flash(f'Funcionalidade de registrar ponto para {usuario_alvo.name} ainda não implementada.', 'info')
    return redirect(url_for('admin.visualizar_usuario', usuario_id=user_id))

