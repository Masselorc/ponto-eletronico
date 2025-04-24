from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class NovoFeriadoForm(FlaskForm):
    """Formulário para criar um novo feriado."""
    data = DateField('Data', validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=3, max=100)])

class EditarFeriadoForm(FlaskForm):
    """Formulário para editar um feriado."""
    data = DateField('Data', validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=3, max=100)])

class NovoUsuarioForm(FlaskForm):
    """Formulário para criar um novo usuário."""
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20)])
    vinculo = SelectField('Vínculo', choices=[
        ('Servidor', 'Servidor'),
        ('Terceirizado', 'Terceirizado'),
        ('Estagiário', 'Estagiário'),
        ('Bolsista', 'Bolsista'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
    password = PasswordField('Senha', validators=[
        DataRequired(),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres')
    ])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        DataRequired(),
        EqualTo('password', message='As senhas devem ser iguais')
    ])
    is_admin = BooleanField('Administrador', default=False)
    is_active = BooleanField('Ativo', default=True)

class EditarUsuarioForm(FlaskForm):
    """Formulário para editar um usuário."""
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20)])
    vinculo = SelectField('Vínculo', choices=[
        ('Servidor', 'Servidor'),
        ('Terceirizado', 'Terceirizado'),
        ('Estagiário', 'Estagiário'),
        ('Bolsista', 'Bolsista'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
    password = PasswordField('Senha', validators=[
        Optional(),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres')
    ])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        EqualTo('password', message='As senhas devem ser iguais')
    ])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo')
