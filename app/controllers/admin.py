from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto
from app.models.feriado import Feriado
from app.forms.admin import NovoFeriadoForm, EditarFeriadoForm, NovoUsuarioForm, EditarUsuarioForm
from datetime import datetime, date, timedelta
from calendar import monthrange
import logging
import os

admin = Blueprint('admin', __name__)

logger = logging.getLogger(__name__)

@admin.route('/admin')
@login_required
def index():
    """Rota para a página inicial do admin."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('admin/index.html')

@admin.route('/admin/feriados')
@login_required
def listar_feriados():
    """Rota para listar os feriados."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o ano da query string
    ano = request.args.get('ano', type=int)
    
    # Se não for especificado ano, usa o ano atual
    if not ano:
        ano = date.today().year
    
    # Obtém os feriados do ano
    feriados = Feriado.query.filter(
        Feriado.data >= date(ano, 1, 1),
        Feriado.data <= date(ano, 12, 31)
    ).order_by(Feriado.data).all()
    
    return render_template('admin/feriados.html', feriados=feriados, ano=ano)

@admin.route('/admin/feriados/novo', methods=['GET', 'POST'])
@login_required
def novo_feriado():
    """Rota para criar um novo feriado."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = NovoFeriadoForm()
    
    if form.validate_on_submit():
        # Cria um novo feriado
        feriado = Feriado(
            data=form.data.data,
            descricao=form.descricao.data
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(feriado)
        db.session.commit()
        
        flash('Feriado criado com sucesso!', 'success')
        return redirect(url_for('admin.listar_feriados'))
    
    return render_template('admin/novo_feriado.html', form=form)

@admin.route('/admin/feriados/editar/<int:feriado_id>', methods=['GET', 'POST'])
@login_required
def editar_feriado(feriado_id):
    """Rota para editar um feriado."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o feriado
    feriado = Feriado.query.get_or_404(feriado_id)
    
    # Cria o formulário e preenche com os dados do feriado
    form = EditarFeriadoForm(obj=feriado)
    
    if form.validate_on_submit():
        # Atualiza os dados do feriado
        feriado.data = form.data.data
        feriado.descricao = form.descricao.data
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash('Feriado atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_feriados'))
    
    return render_template('admin/editar_feriado.html', form=form, feriado=feriado)

@admin.route('/admin/feriados/excluir/<int:feriado_id>', methods=['POST'])
@login_required
def excluir_feriado(feriado_id):
    """Rota para excluir um feriado."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o feriado
    feriado = Feriado.query.get_or_404(feriado_id)
    
    # Exclui o feriado
    from app import db
    db.session.delete(feriado)
    db.session.commit()
    
    flash('Feriado excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_feriados'))

# CORREÇÃO: Adicionando a rota listar_usuarios que estava faltando
@admin.route('/admin/usuarios')
@login_required
def listar_usuarios():
    """Rota para listar os usuários."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém todos os usuários
    usuarios = User.query.order_by(User.name).all()
    
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    """Rota para criar um novo usuário."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = NovoUsuarioForm()
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso
        usuario_existente = User.query.filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este email já está em uso.', 'danger')
            return render_template('admin/novo_usuario.html', form=form)
        
        # Cria um novo usuário
        usuario = User(
            name=form.name.data,
            email=form.email.data,
            matricula=form.matricula.data,
            vinculo=form.vinculo.data,
            is_admin=form.is_admin.data,
            is_active=form.is_active.data
        )
        
        # Define a senha
        usuario.set_password(form.password.data)
        
        # Salva no banco de dados
        from app import db
        db.session.add(usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/novo_usuario.html', form=form)

@admin.route('/admin/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(usuario_id):
    """Rota para editar um usuário."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    usuario = User.query.get_or_404(usuario_id)
    
    # Cria o formulário e preenche com os dados do usuário
    form = EditarUsuarioForm(obj=usuario)
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso por outro usuário
        usuario_existente = User.query.filter_by(email=form.email.data).first()
        if usuario_existente and usuario_existente.id != usuario.id:
            flash('Este email já está em uso.', 'danger')
            return render_template('admin/editar_usuario.html', form=form, usuario=usuario)
        
        # Atualiza os dados do usuário
        usuario.name = form.name.data
        usuario.email = form.email.data
        usuario.matricula = form.matricula.data
        usuario.vinculo = form.vinculo.data
        usuario.is_admin = form.is_admin.data
        usuario.is_active = form.is_active.data
        
        # Atualiza a senha se fornecida
        if form.password.data:
            usuario.set_password(form.password.data)
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/editar_usuario.html', form=form, usuario=usuario)

@admin.route('/admin/usuarios/visualizar/<int:usuario_id>')
@login_required
def visualizar_usuario(usuario_id):
    """Rota para visualizar um usuário."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    usuario = User.query.get_or_404(usuario_id)
    
    # Obtém os registros de ponto do usuário
    registros = Ponto.query.filter_by(user_id=usuario.id).order_by(Ponto.data.desc()).limit(10).all()
    
    return render_template('admin/visualizar_usuario.html', usuario=usuario, registros=registros)

@admin.route('/admin/relatorios')
@login_required
def relatorios():
    """Rota para a página de relatórios."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém todos os usuários ativos
    usuarios = User.query.filter_by(is_active=True).order_by(User.name).all()
    
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/admin/relatorio/<int:usuario_id>')
@login_required
def relatorio_usuario(usuario_id):
    """Rota para o relatório de um usuário."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    usuario = User.query.get_or_404(usuario_id)
    
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
    
    return render_template('admin/relatorio_usuario.html',
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
                          media_diaria=media_diaria,
                          feriados_dict=feriados_dict)

# CORREÇÃO: Adicionando as rotas para relatórios em PDF e Excel que estavam faltando
@admin.route('/admin/relatorio/<int:usuario_id>/pdf')
@login_required
def relatorio_usuario_pdf(usuario_id):
    """Rota para gerar o relatório em PDF."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    usuario = User.query.get_or_404(usuario_id)
    
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
    
    # Gera o relatório em PDF
    from app.utils.export import gerar_relatorio_pdf
    pdf_path = gerar_relatorio_pdf(usuario.id, mes_atual, ano_atual)
    
    # Retorna o arquivo PDF
    return redirect(url_for('static', filename=f'relatorios/{os.path.basename(pdf_path)}'))

@admin.route('/admin/relatorio/<int:usuario_id>/excel')
@login_required
def relatorio_usuario_excel(usuario_id):
    """Rota para gerar o relatório em Excel."""
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    usuario = User.query.get_or_404(usuario_id)
    
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
    
    # Gera o relatório em Excel
    from app.utils.export import gerar_relatorio_excel
    excel_path = gerar_relatorio_excel(usuario.id, mes_atual, ano_atual)
    
    # Retorna o arquivo Excel
    return redirect(url_for('static', filename=f'relatorios/{os.path.basename(excel_path)}'))
