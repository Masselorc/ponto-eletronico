# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db, csrf # Importa csrf para proteger rotas se necessário
from app.forms.auth import LoginForm, RegisterForm
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import logging # Adicionado para logging

auth = Blueprint('auth', __name__)
logger = logging.getLogger(__name__) # Configura logger

# Função para salvar foto (mantida, mas com logging)
def save_picture(form_picture):
    """Salva a imagem de perfil e retorna o caminho relativo."""
    if not form_picture or not form_picture.filename:
        logger.info("Nenhuma foto enviada para salvar.")
        return None

    try:
        random_hex = uuid.uuid4().hex
        _, f_ext = os.path.splitext(form_picture.filename)
        picture_filename = random_hex + f_ext.lower()

        # Salva na pasta static/uploads/fotos para ser servível diretamente
        static_upload_folder = os.path.join(current_app.static_folder, 'uploads/fotos')
        os.makedirs(static_upload_folder, exist_ok=True) # Cria diretórios se não existirem
        static_picture_path = os.path.join(static_upload_folder, picture_filename)

        logger.info(f"Tentando salvar foto em: {static_picture_path}")
        form_picture.save(static_picture_path)
        logger.info(f"Foto salva com sucesso: {picture_filename}")

        # Retorna o caminho relativo a 'static'
        return 'uploads/fotos/' + picture_filename

    except Exception as e:
        logger.error(f"Erro ao salvar foto '{form_picture.filename}': {e}", exc_info=True)
        return None # Retorna None em caso de erro

# Rota de login (mantida)
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Login bem-sucedido! Bem-vindo(a), {user.name}.', 'success')
            logger.info(f"Login bem-sucedido para usuário: {user.email}")
            return redirect(next_page or url_for('main.dashboard'))
        elif user and not user.is_active:
             flash('Sua conta está inativa. Entre em contato com o administrador.', 'warning')
             logger.warning(f"Tentativa de login falhou (usuário inativo): {form.email.data}")
        else:
            flash('Email ou senha inválidos. Por favor, tente novamente.', 'danger')
            logger.warning(f"Tentativa de login falhou (credenciais inválidas): {form.email.data}")

    return render_template('auth/login.html', form=form, title="Login")

# Rota de logout (mantida - apenas POST)
@auth.route('/logout', methods=['POST'])
@login_required
# @csrf.exempt # Descomente se o CSRF estiver causando problemas APENAS nesta rota POST sem form explícito
def logout():
    """Rota de logout (agora apenas POST)."""
    user_email = current_user.email # Guarda email para log antes do logout
    logout_user()
    flash('Você saiu do sistema com sucesso.', 'info')
    logger.info(f"Logout bem-sucedido para usuário: {user_email}")
    return redirect(url_for('auth.login'))

# Rota de cadastro (atualizada para incluir novos campos)
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de cadastro de novos usuários."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        logger.info(f"Tentativa de cadastro para email: {form.email.data}")
        try:
            foto_rel_path = save_picture(form.foto.data)
            # Verifica se a foto foi enviada mas houve erro ao salvar
            if foto_rel_path is None and form.foto.data and form.foto.data.filename:
                 flash('Erro ao salvar a foto. Verifique o arquivo e tente novamente.', 'danger')
                 logger.error(f"Erro ao salvar foto durante cadastro de: {form.email.data}")
                 # Não retorna aqui, permite continuar sem foto se houve erro, mas avisa.
                 # Se a foto for estritamente obrigatória mesmo com erro de upload, descomente:
                 # return render_template('auth/register.html', form=form, title="Cadastro")
                 foto_rel_path = None # Garante que não tente salvar path inválido

            # Cria o novo usuário incluindo os novos campos
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                matricula=form.matricula.data,
                cargo=form.cargo.data,
                uf=form.uf.data,
                telefone=form.telefone.data,
                vinculo=form.vinculo.data,
                # --- NOVOS CAMPOS ---
                unidade_setor=form.unidade_setor.data,
                chefia_imediata=form.chefia_imediata.data,
                # --------------------
                foto_path=foto_rel_path, # Armazena o caminho relativo ou None
                is_admin=False,
                is_active_db=True # Novos usuários são ativos por padrão
            )
            new_user.set_password(form.password.data)

            db.session.add(new_user)
            db.session.commit()

            flash('Cadastro realizado com sucesso! Agora você pode fazer login.', 'success')
            logger.info(f"Novo usuário cadastrado com sucesso: {new_user.email} (ID: {new_user.id})")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            # Usar logger.exception para incluir traceback no log
            logger.exception(f"Erro CRÍTICO durante o cadastro do usuário {form.email.data}: {e}")
            flash('Ocorreu um erro inesperado durante o cadastro. Tente novamente ou contate o suporte.', 'danger')

    # Se GET ou validação falhar, renderiza o form novamente (com erros, se houver)
    return render_template('auth/register.html', form=form, title="Cadastro")
