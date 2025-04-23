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
    # Gera um nome de arquivo único usando UUID para evitar colisões
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_ext
    
    # Define o caminho para salvar a imagem
    upload_folder = os.path.join(current_app.root_path, 'static/uploads/fotos')
    
    # Cria o diretório se não existir
    os.makedirs(upload_folder, exist_ok=True)
    
    # Caminho completo do arquivo
    picture_path = os.path.join(upload_folder, picture_filename)
    
    # Salva a imagem
    form_picture.save(picture_path)
    
    # Retorna o caminho relativo para armazenar no banco de dados
    return 'uploads/fotos/' + picture_filename

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Email ou senha inválidos', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Esta rota será para o cadastro de novos usuários
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        # Salva a foto e obtém o caminho relativo
        foto_path = save_picture(form.foto.data)
        
        # Cria o novo usuário com todos os campos
        user = User(
            name=form.name.data,
            email=form.email.data,
            matricula=form.matricula.data,
            cargo=form.cargo.data,
            uf=form.uf.data,
            telefone=form.telefone.data,
            vinculo=form.vinculo.data,
            foto_path=foto_path,
            is_admin=False  # Usuários comuns não são administradores
        )
        user.set_password(form.password.data)
        
        # Salva no banco de dados
        db.session.add(user)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)
