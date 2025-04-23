from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, SubmitField, DateField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from app.models.user import User

class UserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=3, max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(min=3, max=100)])
    uf = SelectField('UF', validators=[DataRequired()], choices=[
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
        ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
        ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
        ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
    ])
    telefone = StringField('Telefone', validators=[DataRequired(), Length(min=10, max=15)])
    vinculo = SelectField('Vínculo com SENAPPEN', validators=[DataRequired()], choices=[
        ('Mobilizado', 'Mobilizado'),
        ('Colaborador Eventual', 'Colaborador Eventual'),
        ('PPF', 'PPF'),
        ('Terceirizado', 'Terceirizado'),
        ('Estagiário', 'Estagiário')
    ])
    foto = FileField('Foto', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')
    ])
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
