# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from app.models.user import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegisterForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(min=2, max=100)])

    UF_CHOICES = [
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
        ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
        ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
        ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
    ]
    uf = SelectField('UF', choices=UF_CHOICES, validators=[DataRequired()])

    telefone = StringField('Telefone (com DDD)', validators=[
        DataRequired(),
        Length(min=10, max=20, message='Formato inválido. Use (XX)XXXXX-XXXX')
    ])

    VINCULO_CHOICES = [
        ('Mobilizado', 'Mobilizado'),
        ('Colaborador Eventual', 'Colaborador Eventual'),
        ('PPF', 'PPF'),
        ('Terceirizado', 'Terceirizado'),
        ('Estagiário', 'Estagiário')
    ]
    vinculo = SelectField('Vínculo com SENAPPEN', choices=VINCULO_CHOICES, validators=[DataRequired()])

    # --- NOVOS CAMPOS ADICIONADOS ---
    unidade_setor = StringField('Unidade/Setor de Lotação na DIRPP', validators=[DataRequired(), Length(max=150)])
    chefia_imediata = StringField('Chefia Imediata', validators=[DataRequired(), Length(max=100)])
    # ---------------------------------

    foto = FileField('Foto (obrigatória)', validators=[
        FileRequired(message='Por favor, envie uma foto'),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens JPG ou PNG são permitidas')
    ])

    password = PasswordField('Senha', validators=[
        DataRequired(),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres')
    ])

    password2 = PasswordField('Confirmar Senha', validators=[
        DataRequired(),
        EqualTo('password', message='As senhas devem ser iguais')
    ])

    submit = SubmitField('Cadastrar')

    # Validações customizadas (mantidas)
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está em uso. Por favor, use outro.')

    def validate_matricula(self, matricula):
        user = User.query.filter_by(matricula=matricula.data).first()
        if user:
            raise ValidationError('Esta matrícula já está em uso. Por favor, verifique.')

