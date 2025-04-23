from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class RegistroPontoForm(FlaskForm):
    tipo = SelectField('Tipo de Registro', choices=[
        ('entrada', 'Entrada'),
        ('saida_almoco', 'Saída para Almoço'),
        ('retorno_almoco', 'Retorno do Almoço'),
        ('saida', 'Saída')
    ], validators=[DataRequired()])
    submit = SubmitField('Registrar')

class AtividadeForm(FlaskForm):
    descricao = TextAreaField('Descrição da Atividade', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='A descrição deve ter entre 10 e 1000 caracteres')
    ])
    submit = SubmitField('Salvar Atividade')
