# -*- coding: utf-8 -*-
"""
Controlador para Autenticação e Gerenciamento de Contas de Usuário.

Este módulo define as rotas para login, logout e registro de usuários.
Utiliza Flask Blueprints e Flask-Login.
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
# CORREÇÃO: Remover import não utilizado
# from werkzeug.security import generate_password_hash

# Importações locais
from app import db
from app.models.user import User
# Importar apenas LoginForm (RegisterForm não é usado pois a rota está comentada)
from app.forms.auth import LoginForm

# Configuração do Blueprint
auth = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

# --- Rotas de Autenticação ---

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Processa o login do usuário."""
    # Se o usuário já está autenticado, redireciona para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Filtrar por email, conforme o campo do formulário
            user = User.query.filter_by(email=form.email.data).first()

            # Verifica se o usuário existe e a senha está correta
            if user and user.check_password(form.password.data):
                 # Verifica se o usuário está ativo
                 if not user.ativo:
                      flash('Sua conta está desativada. Entre em contato com o administrador.', 'warning')
                      logger.warning(f"Tentativa de login falhou para usuário inativo: {form.email.data}")
                      return render_template('auth/login.html', form=form, title="Login") # Renderiza novamente a página de login

                 # CORREÇÃO: Usar form.remember.data (o campo no form é 'remember')
                 login_user(user, remember=form.remember.data)
                 # Usa email no log pois username pode não ser único ou pode não existir dependendo da opção
                 logger.info(f"Usuário (Email: {user.email}) logado com sucesso.")

                 # Redireciona para a página 'next' se existir, senão para o dashboard
                 next_page = request.args.get('next')
                 # Validação básica para evitar redirecionamento aberto
                 if next_page and not next_page.startswith('/'):
                      next_page = None # Ignora se não for um caminho relativo
                 return redirect(next_page or url_for('main.dashboard'))
            else:
                # Mensagem de erro genérica para não dar dicas sobre qual campo está errado
                flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
                logger.warning(f"Tentativa de login falhou para email: {form.email.data}")
        except Exception as e:
            logger.error(f"Erro durante o processo de login para {form.email.data}: {e}", exc_info=True)
            flash("Ocorreu um erro inesperado durante o login. Tente novamente.", "danger")
            # Não precisa redirecionar aqui, apenas renderiza o template com o form e o title

    # Renderiza o template de login (se GET ou se a validação falhar)
    return render_template('auth/login.html', form=form, title="Login")


# Rota de logout já estava correta (aceita POST e requer login)
@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    """Processa o logout do usuário."""
    try:
        # Usa email no log para consistência
        logger.info(f"Usuário (Email: {current_user.email}) deslogado.")
        logout_user()
        flash('Você foi desconectado com sucesso.', 'success')
    except Exception as e:
        # Tenta obter o email, fallback para ID se não disponível
        user_identifier = getattr(current_user, 'email', f"ID:{getattr(current_user, 'id', 'N/A')}")
        logger.error(f"Erro durante o logout do usuário {user_identifier}: {e}", exc_info=True)
        flash("Ocorreu um erro ao tentar desconectar.", "danger")
    return redirect(url_for('auth.login'))


# Rota de Registro - Mantida comentada conforme o original
"""
@auth.route('/register', methods=['GET', 'POST'])
def register():
    # ... (código comentado como antes) ...
    # Precisaria definir RegistrationForm e passar 'title'
    # return render_template('auth/register.html', title='Registrar', form=form)
"""
