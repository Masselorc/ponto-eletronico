from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, TimeField, DateField
from wtforms.validators import DataRequired, Length, Optional
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

class RegistroMultiploPontoForm(FlaskForm):
    data = DateField('Data', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    
    hora_entrada = TimeField('Hora de Entrada', format='%H:%M', validators=[Optional()])
    hora_saida_almoco = TimeField('Hora de Saída para Almoço', format='%H:%M', validators=[Optional()])
    hora_retorno_almoco = TimeField('Hora de Retorno do Almoço', format='%H:%M', validators=[Optional()])
    hora_saida = TimeField('Hora de Saída', format='%H:%M', validators=[Optional()])
    
    submit = SubmitField('Registrar Horários')
    
    def validate(self):
        if not super().validate():
            return False
        
        # Verifica se pelo menos um campo de hora foi preenchido
        if not (self.hora_entrada.data or self.hora_saida_almoco.data or 
                self.hora_retorno_almoco.data or self.hora_saida.data):
            self.hora_entrada.errors = ['Preencha pelo menos um horário.']
            return False
            
        return True

class AtividadeForm(FlaskForm):
    descricao = TextAreaField('Descrição da Atividade', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='A descrição deve ter entre 10 e 1000 caracteres')
    ])
    
    data = DateField('Data', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    
    submit = SubmitField('Salvar Atividade')
