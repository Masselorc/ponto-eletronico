from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, TimeField, DateField, BooleanField
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
    
    afastamento = BooleanField('Férias ou outros afastamentos')
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('', 'Selecione o tipo de afastamento'),
        ('ferias', 'Férias'),
        ('licenca_medica', 'Licença Médica'),
        ('licenca_maternidade', 'Licença Maternidade/Paternidade'),
        ('abono', 'Abono'),
        ('outro', 'Outro Afastamento')
    ], validators=[Optional()])
    
    hora_entrada = TimeField('Hora de Entrada', format='%H:%M', validators=[Optional()])
    hora_saida_almoco = TimeField('Hora de Saída para Almoço', format='%H:%M', validators=[Optional()])
    hora_retorno_almoco = TimeField('Hora de Retorno do Almoço', format='%H:%M', validators=[Optional()])
    hora_saida = TimeField('Hora de Saída', format='%H:%M', validators=[Optional()])
    
    submit = SubmitField('Registrar Horários')
    
    def validate(self, extra_validators=None):
        if not super().validate():
            return False
        
        # Se for afastamento, não precisa validar os horários
        if self.afastamento.data:
            if not self.tipo_afastamento.data:
                self.tipo_afastamento.errors = ['Selecione o tipo de afastamento.']
                return False
            return True
            
        # Se não for afastamento, verifica se pelo menos um campo de hora foi preenchido
        if not (self.hora_entrada.data or self.hora_saida_almoco.data or 
                self.hora_retorno_almoco.data or self.hora_saida.data):
            self.hora_entrada.errors = ['Preencha pelo menos um horário.']
            return False
            
        return True

class EditarPontoForm(FlaskForm):
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    
    afastamento = BooleanField('Férias ou outros afastamentos')
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('', 'Selecione o tipo de afastamento'),
        ('ferias', 'Férias'),
        ('licenca_medica', 'Licença Médica'),
        ('licenca_maternidade', 'Licença Maternidade/Paternidade'),
        ('abono', 'Abono'),
        ('outro', 'Outro Afastamento')
    ], validators=[Optional()])
    
    entrada = StringField('Hora de Entrada', validators=[Optional()])
    saida_almoco = StringField('Hora de Saída para Almoço', validators=[Optional()])
    retorno_almoco = StringField('Hora de Retorno do Almoço', validators=[Optional()])
    saida = StringField('Hora de Saída', validators=[Optional()])
    
    observacoes = TextAreaField('Observações', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Atualizar Registro')
    
    def validate(self, extra_validators=None):
        if not super().validate():
            return False
        
        # Se for afastamento, não precisa validar os horários
        if self.afastamento.data:
            if not self.tipo_afastamento.data:
                self.tipo_afastamento.errors = ['Selecione o tipo de afastamento.']
                return False
            return True
            
        # Validação de formato de hora (HH:MM)
        for field in [self.entrada, self.saida_almoco, self.retorno_almoco, self.saida]:
            if field.data:
                try:
                    hora, minuto = map(int, field.data.split(':'))
                    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
                        field.errors = ['Formato de hora inválido. Use HH:MM (00-23:00-59).']
                        return False
                except (ValueError, TypeError):
                    field.errors = ['Formato de hora inválido. Use HH:MM.']
                    return False
            
        return True

class AtividadeForm(FlaskForm):
    descricao = TextAreaField('Descrição da Atividade', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='A descrição deve ter entre 10 e 1000 caracteres')
    ])
    
    data = DateField('Data', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    
    submit = SubmitField('Salvar Atividade')
