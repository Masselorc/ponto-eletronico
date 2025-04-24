from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, BooleanField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo

class NovoFeriadoForm(FlaskForm):
    """Formulário para criar um novo feriado."""
    data = DateField('Data', validators=[DataRequired(message='Data é obrigatória')])
    descricao = StringField('Descrição', validators=[DataRequired(message='Descrição é obrigatória')])

class EditarFeriadoForm(FlaskForm):
    """Formulário para editar um feriado."""
    data = DateField('Data', validators=[DataRequired(message='Data é obrigatória')])
    descricao = StringField('Descrição', validators=[DataRequired(message='Descrição é obrigatória')])

class NovoUsuarioForm(FlaskForm):
    """Formulário para criar um novo usuário."""
    name = StringField('Nome', validators=[DataRequired(message='Nome é obrigatório')])
    email = StringField('Email', validators=[DataRequired(message='Email é obrigatório'), Email(message='Email inválido')])
    matricula = StringField('Matrícula', validators=[DataRequired(message='Matrícula é obrigatória')])
    vinculo = SelectField('Vínculo', choices=[
        ('CLT', 'CLT'),
        ('Estagiário', 'Estagiário'),
        ('Terceirizado', 'Terceirizado'),
        ('PJ', 'PJ'),
        ('Outro', 'Outro')
    ], validators=[DataRequired(message='Vínculo é obrigatório')])
    password = PasswordField('Senha', validators=[
        DataRequired(message='Senha é obrigatória'),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres'),
        EqualTo('confirm_password', message='As senhas devem ser iguais')
    ])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(message='Confirmação de senha é obrigatória')])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo', default=True)

class EditarUsuarioForm(FlaskForm):
    """Formulário para editar um usuário."""
    name = StringField('Nome', validators=[DataRequired(message='Nome é obrigatório')])
    email = StringField('Email', validators=[DataRequired(message='Email é obrigatório'), Email(message='Email inválido')])
    matricula = StringField('Matrícula', validators=[DataRequired(message='Matrícula é obrigatória')])
    vinculo = SelectField('Vínculo', choices=[
        ('CLT', 'CLT'),
        ('Estagiário', 'Estagiário'),
        ('Terceirizado', 'Terceirizado'),
        ('PJ', 'PJ'),
        ('Outro', 'Outro')
    ], validators=[DataRequired(message='Vínculo é obrigatório')])
    password = PasswordField('Senha (deixe em branco para manter a atual)', validators=[
        Optional(),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres'),
        EqualTo('confirm_password', message='As senhas devem ser iguais')
    ])
    confirm_password = PasswordField('Confirmar Senha')
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Ativo')
