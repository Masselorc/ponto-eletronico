# -*- coding: utf-8 -*-
"""
Formulários WTForms para as Funcionalidades de Administração.

Este módulo define as classes de formulário usadas nas rotas administrativas
para gerenciar usuários, feriados e gerar relatórios.
"""

from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField, SelectField,
                     DateField, FloatField, IntegerField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, NumberRange
from app.models.user import User # Importar User para validação de duplicidade
from datetime import datetime, date
import calendar

# --- Formulários de Usuário ---

class AdminUserForm(FlaskForm):
    """Formulário para criar um novo usuário (pelo Admin)."""
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=80)])
    jornada_diaria = FloatField('Jornada Diária (horas)', default=8.0, validators=[Optional(), NumberRange(min=0, max=24)])
    is_admin = BooleanField('É Administrador?', default=False)
    ativo = BooleanField('Usuário Ativo?', default=True) # Campo para ativar/desativar
    submit = SubmitField('Criar Usuário')

    # Validação customizada para verificar duplicidade de username
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

    # Validação customizada para verificar duplicidade de email
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está cadastrado. Por favor, use outro.')

class EditarUsuarioForm(FlaskForm):
    """Formulário para editar um usuário existente (pelo Admin)."""
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(max=120)])
    # Senha é opcional na edição
    password = PasswordField('Nova Senha (deixe em branco para não alterar)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=80)])
    jornada_diaria = FloatField('Jornada Diária (horas)', validators=[Optional(), NumberRange(min=0, max=24)])
    is_admin = BooleanField('É Administrador?', default=False)
    ativo = BooleanField('Usuário Ativo?', default=True)
    submit = SubmitField('Salvar Alterações')

    # Precisa do ID do usuário original para validar duplicidade corretamente
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditarUsuarioForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Este nome de usuário já está em uso por outro usuário.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Este email já está em uso por outro usuário.')


# --- Formulários de Feriado ---

class FeriadoForm(FlaskForm):
    """Formulário para adicionar/editar feriados."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    descricao = StringField('Descrição do Feriado', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Salvar Feriado')

    # Validação para evitar duplicidade de data (exceto na edição do próprio feriado)
    def __init__(self, original_data=None, *args, **kwargs):
         super(FeriadoForm, self).__init__(*args, **kwargs)
         self.original_data = original_data # Armazena a data original ao editar

    def validate_data(self, data_field):
         from app.models.feriado import Feriado # Import local para evitar ciclos
         # Se estamos editando e a data não mudou, não valida duplicidade
         if self.original_data and self.original_data == data_field.data:
              return
         # Verifica se já existe feriado na (nova) data
         feriado_existente = Feriado.query.filter_by(data=data_field.data).first()
         if feriado_existente:
              raise ValidationError(f'Já existe um feriado cadastrado para esta data: {feriado_existente.descricao}.')


class EditarFeriadoForm(FeriadoForm):
     """Formulário específico para editar feriados (herda de FeriadoForm)."""
     # A lógica de validação já está no __init__ e validate_data de FeriadoForm
     submit = SubmitField('Salvar Alterações')


# --- Formulários de Relatório ---

class RelatorioUsuarioForm(FlaskForm):
    """Formulário para selecionar parâmetros para gerar relatório de usuário."""
    # Choices de usuário serão preenchidos na view
    usuario = SelectField('Usuário', coerce=int, validators=[DataRequired()])
    # Choices de mês
    mes = SelectField('Mês', coerce=int, validators=[DataRequired()], choices=[
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ], default=datetime.now().month)
    # Choices de ano serão preenchidos na view
    ano = SelectField('Ano', coerce=int, validators=[DataRequired()], default=datetime.now().year)
    formato = SelectField('Formato', choices=[('pdf', 'PDF'), ('excel', 'Excel')], default='pdf')
    submit = SubmitField('Gerar Relatório')

