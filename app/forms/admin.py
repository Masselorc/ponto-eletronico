# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField, TextAreaField, SelectField, HiddenField # Adicionado HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models.user import User # Import User para validações customizadas
from datetime import date

# Validador customizado para email único (exceto o próprio usuário na edição)
def unique_email(form, field):
    # Acessa o user_id do campo oculto, se existir no formulário
    user_id = form.user_id.data if hasattr(form, 'user_id') and form.user_id.data else None
    query = User.query.filter(User.email == field.data)
    if user_id:
        query = query.filter(User.id != int(user_id)) # Converte user_id para int
    user = query.first()
    if user:
        raise ValidationError('Este email já está em uso por outro usuário.')

# Validador customizado para matrícula única (exceto o próprio usuário na edição)
def unique_matricula(form, field):
    user_id = form.user_id.data if hasattr(form, 'user_id') and form.user_id.data else None
    query = User.query.filter(User.matricula == field.data)
    if user_id:
        query = query.filter(User.id != int(user_id)) # Converte user_id para int
    user = query.first()
    if user:
        raise ValidationError('Esta matrícula já está em uso por outro usuário.')

class NovoUsuarioForm(FlaskForm):
    """Formulário para criar novo usuário (Admin)."""
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), unique_email])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20), unique_matricula])
    vinculo = StringField('Vínculo', validators=[DataRequired(), Length(max=50)])
    # --- NOVOS CAMPOS ADICIONADOS ---
    unidade_setor = StringField('Unidade/Setor (DIRPP)', validators=[DataRequired(), Length(max=150)])
    chefia_imediata = StringField('Chefia Imediata', validators=[DataRequired(), Length(max=100)])
    # ---------------------------------
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo', default=True) # Default para ativo
    submit = SubmitField('Criar Usuário')

class EditarUsuarioForm(FlaskForm):
    """Formulário para editar usuário (Admin)."""
    # Campo oculto para armazenar o ID do usuário sendo editado
    # Necessário para as validações unique_email e unique_matricula
    user_id = HiddenField('User ID')

    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), unique_email])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20), unique_matricula])
    vinculo = StringField('Vínculo', validators=[DataRequired(), Length(max=50)])
    # --- NOVOS CAMPOS ADICIONADOS ---
    unidade_setor = StringField('Unidade/Setor (DIRPP)', validators=[DataRequired(), Length(max=150)])
    chefia_imediata = StringField('Chefia Imediata', validators=[DataRequired(), Length(max=100)])
    # ---------------------------------
    password = PasswordField('Nova Senha (deixe em branco para não alterar)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo')
    submit = SubmitField('Salvar Alterações')

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

# Formulário minimalista para CSRF em exclusões
class DeleteForm(FlaskForm):
    """Formulário vazio usado apenas para gerar o token CSRF
       em botões/links de exclusão."""
    pass
