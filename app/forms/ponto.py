from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, TimeField, DateField
from wtforms.validators import DataRequired, Length
from datetime import datetime, date, time

class RegistroPontoForm(FlaskForm):
    tipo = SelectField('Tipo de Registro', choices=[
        ('entrada', 'Entrada'),
        ('saida_almoco', 'Saída para Almoço'),
        ('retorno_almoco', 'Retorno do Almoço'),
        ('saida', 'Saída')
    ], validators=[DataRequired()])
    
    data = DateField('Data', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    
    # Usando time() para obter apenas o componente de hora do datetime.now()
    hora = TimeField('Hora', format='%H:%M', default=lambda: datetime.now().time(), validators=[DataRequired()])
    
    submit = SubmitField('Registrar')

class AtividadeForm(FlaskForm):
    descricao = TextAreaField('Descrição da Atividade', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='A descrição deve ter entre 10 e 1000 caracteres')
    ])
    
    data = DateField('Data', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    
    submit = SubmitField('Salvar Atividade')
