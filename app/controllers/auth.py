# -*- coding: utf-8 -*-
"""
Controlador para Autenticação e Gerenciamento de Contas de Usuário.

Este módulo define as rotas para login, logout e registro de usuários.
Utiliza Flask Blueprints e Flask-Login.
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

# Importações locais
from app import db
from app.models.user import User
# Importar apenas LoginForm
from app.forms.auth import LoginForm

# Configuração do Blueprint
auth = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

# --- Rotas de Autenticação ---

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Processa o login do usuário."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            # CORREÇÃO: Filtrar por email, conforme o campo do formulário
            user = User.query.filter_by(email=form.email.data).first()
            # Verifica se o usuário existe e a senha está correta
            if user and user.check_password(form.password.data):
                 if not user.ativo:
                      flash('Sua conta está desativada. Entre em contato com o administrador.', 'warning')
                      logger.warning(f"Tentativa de login falhou para usuário inativo: {form.email.data}")
                      # CORREÇÃO: Passar title também no redirect/render de erro
                      return render_template('auth/login.html', form=form, title="Login")

                 login_user(user, remember=form.remember_me.data)
                 logger.info(f"Usuário '{user.username}' (Email: {user.email}) logado com sucesso.")
                 next_page = request.args.get('next')
                 if next_page and not next_page.startswith('/'):
                      next_page = None
                 return redirect(next_page or url_for('main.dashboard'))
            else:
                flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
                logger.warning(f"Tentativa de login falhou para email: {form.email.data}")
        except Exception as e:
            logger.error(f"Erro durante o processo de login para {form.email.data}: {e}", exc_info=True)
            flash("Ocorreu um erro inesperado durante o login. Tente novamente.", "danger")
            # Não precisa redirecionar aqui, apenas renderiza o template com o form e o title

    # CORREÇÃO: Passar a variável 'title' para o template
    return render_template('auth/login.html', form=form, title="Login")


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    """Processa o logout do usuário."""
    try:
        logger.info(f"Usuário '{current_user.username}' deslogado.")
        logout_user()
        flash('Você foi desconectado com sucesso.', 'success')
    except Exception as e:
        logger.error(f"Erro durante o logout do usuário {getattr(current_user, 'username', 'N/A')}: {e}", exc_info=True)
        flash("Ocorreu um erro ao tentar desconectar.", "danger")
    return redirect(url_for('auth.login'))


# Rota de Registro - Mantida comentada
"""
@auth.route('/register', methods=['GET', 'POST'])
def register():
    # ... (código comentado como antes) ...
    # Precisaria definir RegistrationForm e passar 'title'
    # return render_template('auth/register.html', title='Registrar', form=form)
"""

