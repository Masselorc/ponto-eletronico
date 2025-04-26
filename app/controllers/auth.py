from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from app.forms.auth import LoginForm, RegisterForm
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

auth = Blueprint('auth', __name__)

def save_picture(form_picture):
    """Salva a imagem de perfil e retorna o caminho relativo."""
    if not form_picture:
        return None # Retorna None se nenhuma foto for enviada

    try:
        random_hex = uuid.uuid4().hex
        _, f_ext = os.path.splitext(form_picture.filename)
        picture_filename = random_hex + f_ext.lower() # Garante extensão minúscula

        # Define o caminho para salvar a imagem (usando instance_path é mais seguro)
        # upload_folder = os.path.join(current_app.root_path, 'static/uploads/fotos') # Caminho antigo
        upload_folder = os.path.join(current_app.instance_path, 'uploads/fotos') # Novo caminho seguro
        os.makedirs(upload_folder, exist_ok=True) # Cria diretórios se não existirem

        picture_path = os.path.join(upload_folder, picture_filename)
        form_picture.save(picture_path)

        # Retorna o caminho relativo a partir da pasta 'instance' para referência futura
        # Nota: Servir arquivos de 'instance' requer configuração adicional no servidor web (Flask não faz isso por padrão)
        # Alternativa: Salvar em 'static' mas garantir que nomes são únicos e seguros.
        # Vamos manter em 'instance' por segurança, mas a exibição precisará de uma rota específica.
        # Por ora, retornaremos um caminho que *não* será diretamente servível pelo Flask.
        # A exibição precisará de uma rota como /user_photo/<filename>
        # return 'instance/uploads/fotos/' + picture_filename # Caminho não servível diretamente

        # --- Alternativa: Salvar em static (mais simples para exibir, requer cuidado com nomes) ---
        static_upload_folder = os.path.join(current_app.static_folder, 'uploads/fotos')
        os.makedirs(static_upload_folder, exist_ok=True)
        static_picture_path = os.path.join(static_upload_folder, picture_filename)
        form_picture.save(static_picture_path)
        return 'uploads/fotos/' + picture_filename # Caminho relativo a 'static'
        # ------------------------------------------------------------------------------------

    except Exception as e:
        current_app.logger.error(f"Erro ao salvar foto: {e}", exc_info=True)
        return None # Retorna None em caso de erro

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Verifica se usuário existe E se a senha está correta E se o usuário está ativo
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            # Redireciona para a página desejada ou dashboard
            flash(f'Login bem-sucedido! Bem-vindo(a), {user.name}.', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        elif user and not user.is_active:
             flash('Sua conta está inativa. Entre em contato com o administrador.', 'warning')
        else:
            flash('Email ou senha inválidos. Por favor, tente novamente.', 'danger')

    return render_template('auth/login.html', form=form, title="Login")

# --- CORREÇÃO: Alterado para aceitar apenas POST ---
@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    """Rota de logout (agora apenas POST)."""
    logout_user()
    flash('Você saiu do sistema com sucesso.', 'info')
    return redirect(url_for('auth.login'))
# --------------------------------------------------

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de cadastro de novos usuários."""
    # Redireciona se já estiver logado
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            # Tenta salvar a foto
            foto_rel_path = save_picture(form.foto.data)
            if foto_rel_path is None and form.foto.data: # Verifica se houve erro ao salvar
                 flash('Erro ao salvar a foto. Tente novamente.', 'danger')
                 return render_template('auth/register.html', form=form, title="Cadastro")

            # Cria o novo usuário
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                matricula=form.matricula.data,
                cargo=form.cargo.data,
                uf=form.uf.data,
                telefone=form.telefone.data,
                vinculo=form.vinculo.data,
                foto_path=foto_rel_path, # Armazena o caminho relativo
                is_admin=False, # Novos usuários nunca são admin por padrão
                is_active_db=True # Novos usuários são ativos por padrão
            )
            new_user.set_password(form.password.data)

            db.session.add(new_user)
            db.session.commit()

            flash('Cadastro realizado com sucesso! Agora você pode fazer login.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro durante o cadastro do usuário {form.email.data}: {e}", exc_info=True)
            flash('Ocorreu um erro durante o cadastro. Tente novamente.', 'danger')

    return render_template('auth/register.html', form=form, title="Cadastro")
