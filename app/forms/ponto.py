from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length
from datetime import datetime

class RegistroPontoForm(FlaskForm):
    # IMPORTANTE: Campo data sem valor padrão para garantir que a data selecionada pelo usuário seja usada
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    hora = StringField('Hora', validators=[DataRequired()])
    tipo = SelectField('Tipo de Registro', choices=[
        ('entrada', 'Entrada'),
        ('saida_almoco', 'Saída para Almoço'),
        ('retorno_almoco', 'Retorno do Almoço'),
        ('saida', 'Saída')
    ], validators=[DataRequired()])
    submit = SubmitField('Registrar Ponto')

class RegistroMultiploPontoForm(FlaskForm):
    # IMPORTANTE: Campo data sem valor padrão para garantir que a data selecionada pelo usuário seja usada
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    
    afastamento = BooleanField('Férias ou outros afastamentos')
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('ferias', 'Férias'),
        ('licenca_medica', 'Licença Médica'),
        ('licenca_maternidade', 'Licença Maternidade/Paternidade'),
        ('falta_justificada', 'Falta Justificada'),
        ('outro', 'Outro')
    ], validators=[Optional()])
    
    entrada = StringField('Hora de Entrada', validators=[Optional()])
    saida_almoco = StringField('Hora de Saída para Almoço', validators=[Optional()])
    retorno_almoco = StringField('Hora de Retorno do Almoço', validators=[Optional()])
    saida = StringField('Hora de Saída', validators=[Optional()])
    
    observacoes = TextAreaField('Observações', validators=[Optional(), Length(max=500)])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional(), Length(max=1000)],
                              description='Descreva as atividades realizadas neste dia')
    
    submit = SubmitField('Registrar Horários')
    
    def validate(self, extra_validators=None):
        if not super().validate():
            return False
            
        if self.afastamento.data:
            if not self.tipo_afastamento.data:
                self.tipo_afastamento.errors.append('Selecione o tipo de afastamento')
                return False
            # Se for afastamento, os campos de horário não são necessários
            return True
            
        # Verifica se pelo menos um campo de horário foi preenchido
        if not any([self.entrada.data, self.saida_almoco.data, self.retorno_almoco.data, self.saida.data]):
            self.entrada.errors.append('Preencha pelo menos um horário')
            return False
            
        # Verifica o formato dos horários
        for field in [self.entrada, self.saida_almoco, self.retorno_almoco, self.saida]:
            if field.data:
                try:
                    datetime.strptime(field.data, '%H:%M')
                except ValueError:
                    field.errors.append('Formato inválido. Use HH:MM')
                    return False
                    
        return True

class EditarPontoForm(FlaskForm):
    # IMPORTANTE: Campo data sem valor padrão para garantir que a data selecionada pelo usuário seja usada
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    
    afastamento = BooleanField('Férias ou outros afastamentos')
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('ferias', 'Férias'),
        ('licenca_medica', 'Licença Médica'),
        ('licenca_maternidade', 'Licença Maternidade/Paternidade'),
        ('falta_justificada', 'Falta Justificada'),
        ('outro', 'Outro')
    ], validators=[Optional()])
    
    entrada = StringField('Hora de Entrada', validators=[Optional()])
    saida_almoco = StringField('Hora de Saída para Almoço', validators=[Optional()])
    retorno_almoco = StringField('Hora de Retorno do Almoço', validators=[Optional()])
    saida = StringField('Hora de Saída', validators=[Optional()])
    
    observacoes = TextAreaField('Observações', validators=[Optional(), Length(max=500)])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional(), Length(max=1000)],
                              description='Descreva as atividades realizadas neste dia')
    
    submit = SubmitField('Atualizar Registro')
    
    def validate(self, extra_validators=None):
        if not super().validate():
            return False
            
        if self.afastamento.data:
            if not self.tipo_afastamento.data:
                self.tipo_afastamento.errors.append('Selecione o tipo de afastamento')
                return False
            # Se for afastamento, os campos de horário não são necessários
            return True
            
        # Verifica se pelo menos um campo de horário foi preenchido
        if not any([self.entrada.data, self.saida_almoco.data, self.retorno_almoco.data, self.saida.data]):
            self.entrada.errors.append('Preencha pelo menos um horário')
            return False
            
        # Verifica o formato dos horários
        for field in [self.entrada, self.saida_almoco, self.retorno_almoco, self.saida]:
            if field.data:
                try:
                    datetime.strptime(field.data, '%H:%M')
                except ValueError:
                    field.errors.append('Formato inválido. Use HH:MM')
                    return False
                    
        return True

class AtividadeForm(FlaskForm):
    descricao = TextAreaField('Descrição da Atividade', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Registrar Atividade')
