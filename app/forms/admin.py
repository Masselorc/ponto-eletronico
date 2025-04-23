from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, DateField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from app.models.user import User

class UserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20)])
    vinculo = StringField('Vínculo com SENAPPEN', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Senha', validators=[
        Optional(),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres')
    ])
    password2 = PasswordField('Confirmar Senha', validators=[
        EqualTo('password', message='As senhas devem ser iguais')
    ])
    is_admin = BooleanField('Cadastrador (Administrador)')
    submit = SubmitField('Salvar')

class FeriadoForm(FlaskForm):
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Salvar')
