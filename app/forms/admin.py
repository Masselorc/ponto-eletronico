# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
# --- Adicionado FileField e FileAllowed ---
from flask_wtf.file import FileField, FileAllowed
# -----------------------------------------
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models.user import User
from datetime import date

# --- COPIADO DE app/forms/auth.py ---
VINCULO_CHOICES = [
    ('', '-- Selecione --'), # Adicionado opção vazia
    ('Mobilizado', 'Mobilizado'),
    ('Colaborador Eventual', 'Colaborador Eventual'),
    ('PPF', 'PPF'),
    ('Terceirizado', 'Terceirizado'),
    ('Estagiário', 'Estagiário'),
    ('Outro', 'Outro') # Adicionada opção Outro, se aplicável
]
# -----------------------------------

# Validador customizado para email único (mantido)
def unique_email(form, field):
    user_id = form.user_id.data if hasattr(form, 'user_id') and form.user_id.data else None
    query = User.query.filter(User.email == field.data)
    if user_id:
        query = query.filter(User.id != int(user_id))
    user = query.first()
    if user:
        raise ValidationError('Este email já está em uso por outro usuário.')

# Validador customizado para matrícula única (mantido)
def unique_matricula(form, field):
    user_id = form.user_id.data if hasattr(form, 'user_id') and form.user_id.data else None
    query = User.query.filter(User.matricula == field.data)
    if user_id:
        query = query.filter(User.id != int(user_id))
    user = query.first()
    if user:
        raise ValidationError('Esta matrícula já está em uso por outro usuário.')

class NovoUsuarioForm(FlaskForm):
    """Formulário para criar novo usuário (Admin)."""
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), unique_email])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20), unique_matricula])
    # --- CORREÇÃO: Alterado para SelectField ---
    vinculo = SelectField('Vínculo', choices=VINCULO_CHOICES, validators=[DataRequired("Selecione um vínculo.")])
    # -----------------------------------------
    unidade_setor = StringField('Unidade/Setor (DIRPP)', validators=[DataRequired(), Length(max=150)])
    chefia_imediata = StringField('Chefia Imediata', validators=[DataRequired(), Length(max=100)])
    # --- NOVO CAMPO: Foto (Obrigatória na criação) ---
    foto = FileField('Foto do Usuário', validators=[
        FileRequired(message='A foto é obrigatória para novos usuários.'),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens JPG, JPEG ou PNG são permitidas!')
    ])
    # ------------------------------------------------
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo', default=True)
    submit = SubmitField('Criar Usuário')

class EditarUsuarioForm(FlaskForm):
    """Formulário para editar usuário (Admin)."""
    user_id = HiddenField('User ID')
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), unique_email])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20), unique_matricula])
    # --- CORREÇÃO: Alterado para SelectField ---
    vinculo = SelectField('Vínculo', choices=VINCULO_CHOICES, validators=[DataRequired("Selecione um vínculo.")])
    # -----------------------------------------
    unidade_setor = StringField('Unidade/Setor (DIRPP)', validators=[DataRequired(), Length(max=150)])
    chefia_imediata = StringField('Chefia Imediata', validators=[DataRequired(), Length(max=100)])
    # --- NOVO CAMPO: Foto (Opcional na edição) ---
    foto = FileField('Alterar Foto (opcional)', validators=[
        Optional(), # Torna o campo opcional
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens JPG, JPEG ou PNG são permitidas!')
    ])
    # -------------------------------------------
    password = PasswordField('Nova Senha (deixe em branco para não alterar)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo')
    submit = SubmitField('Salvar Alterações')

# --- Forms de Feriado e Delete (mantidos) ---
class NovoFeriadoForm(FlaskForm):
    """Formulário para criar novo feriado."""
    data = DateField('Data', validators=[DataRequired("Selecione a data do feriado.")], default=date.today, format='%Y-%m-%d')
    descricao = StringField('Descrição', validators=[DataRequired("A descrição é obrigatória."), Length(max=100)])
    submit = SubmitField('Criar Feriado')

class EditarFeriadoForm(FlaskForm):
    """Formulário para editar feriado."""
    data = DateField('Data', validators=[DataRequired("Selecione a data do feriado.")], format='%Y-%m-%d')
    descricao = StringField('Descrição', validators=[DataRequired("A descrição é obrigatória."), Length(max=100)])
    submit = SubmitField('Salvar Alterações')

class DeleteForm(FlaskForm):
    """Formulário vazio usado apenas para gerar o token CSRF
       em botões/links de exclusão."""
    pass
