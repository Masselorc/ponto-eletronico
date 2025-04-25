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
from app.forms.auth import LoginForm, RegistrationForm

# Configuração do Blueprint
auth = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

# --- Rotas de Autenticação ---

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Processa o login do usuário."""
    # Se o usuário já estiver autenticado, redireciona para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            # Verifica se o usuário existe e a senha está correta
            if user and user.check_password(form.password.data):
                 # Verifica se o usuário está ativo
                 if not user.ativo:
                      flash('Sua conta está desativada. Entre em contato com o administrador.', 'warning')
                      logger.warning(f"Tentativa de login falhou para usuário inativo: {form.username.data}")
                      return redirect(url_for('auth.login'))

                 # Registra o usuário na sessão
                 login_user(user, remember=form.remember_me.data)
                 logger.info(f"Usuário '{user.username}' logado com sucesso.")
                 # Redireciona para a página que o usuário tentava acessar (next) ou para o dashboard
                 next_page = request.args.get('next')
                 # Segurança: Garante que next_page seja uma URL relativa para evitar Open Redirect
                 if next_page and not next_page.startswith('/'):
                      next_page = None # Ignora URLs externas
                 return redirect(next_page or url_for('main.dashboard'))
            else:
                flash('Login inválido. Verifique seu nome de usuário e senha.', 'danger')
                logger.warning(f"Tentativa de login falhou para usuário: {form.username.data}")
        except Exception as e:
            logger.error(f"Erro durante o processo de login para {form.username.data}: {e}", exc_info=True)
            flash("Ocorreu um erro inesperado durante o login. Tente novamente.", "danger")

    return render_template('auth/login.html', form=form, title="Login")


# CORREÇÃO Item 9: Mudar logout para aceitar apenas POST
@auth.route('/logout', methods=['POST']) # Aceita apenas POST
@login_required # Garante que apenas usuários logados possam deslogar
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


# Rota de Registro - Descomente e ajuste se o auto-registro for permitido
# Geralmente, em sistemas corporativos, o admin cria os usuários.
"""
@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Impede acesso se já estiver logado
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Verifica se o auto-registro está habilitado (ex: config da app)
            # if not current_app.config.get('ALLOW_SELF_REGISTRATION', False):
            #     flash('O auto-registro não está habilitado.', 'warning')
            #     return redirect(url_for('auth.login'))

            user = User(
                username=form.username.data,
                email=form.email.data,
                nome_completo=form.nome_completo.data, # Adicionado nome completo
                # Outros campos podem ser definidos aqui ou deixados como padrão/null
                ativo=True # Novos usuários registrados são ativos por padrão?
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            logger.info(f"Novo usuário '{user.username}' registrado com sucesso.")
            flash('Sua conta foi criada com sucesso! Faça o login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro durante o registro do usuário {form.username.data}: {e}", exc_info=True)
            flash("Ocorreu um erro ao tentar criar sua conta. Tente novamente.", "danger")

    return render_template('auth/register.html', title='Registrar', form=form)
"""

