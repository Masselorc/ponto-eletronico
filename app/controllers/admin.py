from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.models.user import User
from app.models.ponto import Ponto
from app.models.feriado import Feriado
from datetime import datetime, date
from calendar import monthrange
import logging
import os
from app.utils.export import generate_pdf, generate_excel

admin = Blueprint('admin', __name__)

logger = logging.getLogger(__name__)

@admin.route('/dashboard')
@login_required
def dashboard():
    """Rota para o dashboard administrativo."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém a contagem de usuários ativos
    usuarios_ativos = User.query.filter_by(is_active=True).count()
    
    # Obtém a contagem de registros de ponto do mês atual
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
    registros_mes = Ponto.query.filter(
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).count()
    
    # Obtém a contagem de feriados cadastrados
    feriados = Feriado.query.count()
    
    return render_template('admin/dashboard.html',
                          usuarios_ativos=usuarios_ativos,
                          registros_mes=registros_mes,
                          feriados=feriados)

@admin.route('/usuarios')
@login_required
def usuarios():
    """Rota para listar usuários."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém todos os usuários
    usuarios = User.query.order_by(User.name).all()
    
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    """Rota para criar um novo usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Importa o formulário aqui para evitar importação circular
    from app.forms.admin import UserForm
    
    form = UserForm()
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso
        usuario_existente = User.query.filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este email já está em uso.', 'danger')
            return render_template('admin/novo_usuario.html', form=form)
        
        # Cria um novo usuário
        novo_usuario = User(
            name=form.name.data,
            email=form.email.data,
            matricula=form.matricula.data,
            vinculo=form.vinculo.data,
            is_admin=form.is_admin.data,
            is_active=form.is_active.data
        )
        
        # Define a senha
        novo_usuario.set_password(form.password.data)
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin.usuarios'))
    
    return render_template('admin/novo_usuario.html', form=form)

@admin.route('/usuario/visualizar/<int:user_id>')
@login_required
def visualizar_usuario(user_id):
    """Rota para visualizar um usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
    # Obtém os registros de ponto do mês atual para o usuário
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    primeiro_dia = date(ano_atual, mes_atual, 1)
    ultimo_dia = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
    registros = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    ).order_by(Ponto.data).all()
    
    return render_template('admin/visualizar_usuario.html',
                          user=user,
                          registros=registros,
                          mes_atual=mes_atual,
                          ano_atual=ano_atual)

@admin.route('/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    """Rota para editar um usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
    # Importa o formulário aqui para evitar importação circular
    from app.forms.admin import UserEditForm
    
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso por outro usuário
        usuario_existente = User.query.filter(User.email == form.email.data, User.id != user_id).first()
        if usuario_existente:
            flash('Este email já está em uso por outro usuário.', 'danger')
            return render_template('admin/editar_usuario.html', form=form, user=user)
        
        # Atualiza os dados do usuário
        user.name = form.name.data
        user.email = form.email.data
        user.matricula = form.matricula.data
        user.vinculo = form.vinculo.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
        # Se uma nova senha foi fornecida, atualiza a senha
        if form.password.data:
            user.set_password(form.password.data)
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.visualizar_usuario', user_id=user_id))
    
    return render_template('admin/editar_usuario.html', form=form, user=user)

@admin.route('/usuario/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    """Rota para excluir um usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
    # Não permite excluir o próprio usuário
    if user.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    # Exclui o usuário
    from app import db
    db.session.delete(user)
    db.session.commit()
    
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('admin.usuarios'))

@admin.route('/feriados')
@login_required
def feriados():
    """Rota para listar feriados."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém todos os feriados
    feriados = Feriado.query.order_by(Feriado.data).all()
    
    return render_template('admin/feriados.html', feriados=feriados)

@admin.route('/feriado/novo', methods=['GET', 'POST'])
@login_required
def novo_feriado():
    """Rota para criar um novo feriado."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Importa o formulário aqui para evitar importação circular
    from app.forms.admin import FeriadoForm
    
    form = FeriadoForm()
    
    if form.validate_on_submit():
        # Verifica se já existe um feriado para esta data
        feriado_existente = Feriado.query.filter_by(data=form.data.data).first()
        if feriado_existente:
            flash(f'Já existe um feriado cadastrado para {form.data.data.strftime("%d/%m/%Y")}.', 'danger')
            return render_template('admin/novo_feriado.html', form=form)
        
        # Cria um novo feriado
        novo_feriado = Feriado(
            data=form.data.data,
            descricao=form.descricao.data
        )
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_feriado)
        db.session.commit()
        
        flash('Feriado criado com sucesso!', 'success')
        return redirect(url_for('admin.feriados'))
    
    return render_template('admin/novo_feriado.html', form=form)

@admin.route('/feriado/editar/<int:feriado_id>', methods=['GET', 'POST'])
@login_required
def editar_feriado(feriado_id):
    """Rota para editar um feriado."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o feriado
    feriado = Feriado.query.get_or_404(feriado_id)
    
    # Importa o formulário aqui para evitar importação circular
    from app.forms.admin import FeriadoForm
    
    form = FeriadoForm(obj=feriado)
    
    if form.validate_on_submit():
        # Verifica se já existe um feriado para esta data (exceto o atual)
        feriado_existente = Feriado.query.filter(Feriado.data == form.data.data, Feriado.id != feriado_id).first()
        if feriado_existente:
            flash(f'Já existe um feriado cadastrado para {form.data.data.strftime("%d/%m/%Y")}.', 'danger')
            return render_template('admin/editar_feriado.html', form=form, feriado=feriado)
        
        # Atualiza os dados do feriado
        feriado.data = form.data.data
        feriado.descricao = form.descricao.data
        
        # Salva as alterações
        from app import db
        db.session.commit()
        
        flash('Feriado atualizado com sucesso!', 'success')
        return redirect(url_for('admin.feriados'))
    
    return render_template('admin/editar_feriado.html', form=form, feriado=feriado)

@admin.route('/feriado/excluir/<int:feriado_id>', methods=['POST'])
@login_required
def excluir_feriado(feriado_id):
    """Rota para excluir um feriado."""
    # Verifica se o usuário é admin
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
    return redirect(url_for('admin.feriados'))

@admin.route('/relatorios')
@login_required
def relatorios():
    """Rota para a página de relatórios."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # CORREÇÃO: Obter todos os usuários ativos para exibir na página de relatórios
    usuarios = User.query.filter_by(is_active=True).order_by(User.name).all()
    
    return render_template('admin/relatorios.html', usuarios=usuarios)

@admin.route('/relatorio/usuario/<int:user_id>')
@login_required
def relatorio_usuario(user_id):
    """Rota para visualizar o relatório de um usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
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
    
    # Calcula a carga horária devida (8h por dia útil)
    # CORREÇÃO: Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    return render_template('admin/relatorio_usuario.html',
                          user=user,
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
                          feriados_dict=feriados_dict)

# CORREÇÃO: Adicionando a rota relatorio_usuario_pdf que estava faltando
@admin.route('/relatorio/<int:user_id>/pdf')
@login_required
def relatorio_usuario_pdf(user_id):
    """Rota para exportar o relatório de um usuário em PDF."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
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
    
    # Calcula a carga horária devida (8h por dia útil)
    # CORREÇÃO: Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # Gera o PDF
    pdf_path = generate_pdf(
        usuario=user,
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
        feriados_dict=feriados_dict
    )
    
    return send_file(pdf_path, as_attachment=True, download_name=f'relatorio_{user.name}_{nome_mes}_{ano_atual}.pdf')

# CORREÇÃO: Adicionando a rota relatorio_usuario_excel que estava faltando
@admin.route('/relatorio/<int:user_id>/excel')
@login_required
def relatorio_usuario_excel(user_id):
    """Rota para exportar o relatório de um usuário em Excel."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
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
    
    # Calcula a carga horária devida (8h por dia útil)
    # CORREÇÃO: Não é mais necessário subtrair dias de afastamento, pois já foram excluídos do cálculo de dias úteis
    carga_horaria_devida = 8 * dias_uteis
    
    # Calcula o saldo de horas
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    
    # Obtém o nome do mês
    nomes_meses = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    nome_mes = nomes_meses[mes_atual - 1]
    
    # Gera o Excel
    excel_path = generate_excel(
        usuario=user,
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
        feriados_dict=feriados_dict
    )
    
    return send_file(excel_path, as_attachment=True, download_name=f'relatorio_{user.name}_{nome_mes}_{ano_atual}.xlsx')

# CORREÇÃO: Adicionando a rota novo_ponto que estava faltando
@admin.route('/ponto/novo/<int:user_id>', methods=['GET', 'POST'])
@login_required
def novo_ponto(user_id):
    """Rota para criar um novo ponto para um usuário."""
    # Verifica se o usuário é admin
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtém o usuário
    user = User.query.get_or_404(user_id)
    
    # Importa o formulário aqui para evitar importação circular
    from app.forms.ponto import RegistroMultiploPontoForm
    
    form = RegistroMultiploPontoForm()
    
    # Se uma data for fornecida via GET, preenche o formulário
    data_str = request.args.get('data')
    if data_str:
        try:
            # CORREÇÃO DEFINITIVA: Armazenar a data original como string e converter para date
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            form.data.data = data_selecionada
            form.data_original.data = data_str
            logger.info(f"Data original armazenada via GET: {data_str}")
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    else:
        # CORREÇÃO DEFINITIVA: Não preencher automaticamente com a data atual
        # Deixar o campo vazio para forçar o usuário a selecionar uma data
        form.data_original.data = ""
        logger.info("Nenhuma data fornecida via GET, campo deixado vazio")
    
    if form.validate_on_submit():
        # CORREÇÃO DEFINITIVA: Usar a data original do formulário se disponível
        data_selecionada = None
        if form.data_original.data:
            try:
                data_selecionada = datetime.strptime(form.data_original.data, '%Y-%m-%d').date()
                logger.info(f"Usando data original do formulário: {data_selecionada}")
            except ValueError:
                logger.warning(f"Erro ao converter data original: {form.data_original.data}")
                data_selecionada = None
        
        # Se não conseguiu usar a data original, usa a data do campo normal
        if data_selecionada is None:
            data_selecionada = form.data.data
            logger.info(f"Usando data normal do formulário: {data_selecionada}")
        
        logger.info(f"Registrando ponto para a data: {data_selecionada}")
        
        # Verifica se já existe um registro para esta data
        registro_existente = Ponto.query.filter_by(
            user_id=user_id,
            data=data_selecionada
        ).first()
        
        # Permitir registro retroativo mesmo se já existir um registro para a data
        # Se já existir registro, pergunta se deseja sobrescrever
        if registro_existente:
            # Para datas anteriores, permite sobrescrever o registro existente
            from app import db
            db.session.delete(registro_existente)
            db.session.commit()
            flash(f'Registro anterior para {data_selecionada.strftime("%d/%m/%Y")} foi substituído.', 'info')
        
        # Cria um novo registro com a data selecionada
        novo_registro = Ponto(
            user_id=user_id,
            data=data_selecionada  # CORREÇÃO DEFINITIVA: Usar a data selecionada
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
                novo_registro.entrada = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.saida_almoco.data:
                hora, minuto = map(int, form.saida_almoco.data.split(':'))
                novo_registro.saida_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.retorno_almoco.data:
                hora, minuto = map(int, form.retorno_almoco.data.split(':'))
                novo_registro.retorno_almoco = datetime.min.time().replace(hour=hora, minute=minuto)
            
            if form.saida.data:
                hora, minuto = map(int, form.saida.data.split(':'))
                novo_registro.saida = datetime.min.time().replace(hour=hora, minute=minuto)
            
            # Calcula as horas trabalhadas
            novo_registro.calcular_horas_trabalhadas()
        
        # Salva no banco de dados
        from app import db
        db.session.add(novo_registro)
        db.session.commit()
        
        # Registra a atividade se o campo estiver preenchido
        if hasattr(form, 'atividades') and form.atividades.data:
            from app.models.ponto import Atividade
            atividade = Atividade(
                ponto_id=novo_registro.id,
                descricao=form.atividades.data
            )
            db.session.add(atividade)
            db.session.commit()
            logger.info(f"Atividade registrada para o ponto {novo_registro.id}")
        
        flash(f'Registro de ponto realizado com sucesso para {data_selecionada.strftime("%d/%m/%Y")}!', 'success')
        return redirect(url_for('admin.visualizar_usuario', user_id=user_id))
    
    return render_template('admin/novo_ponto.html', form=form, user=user)
