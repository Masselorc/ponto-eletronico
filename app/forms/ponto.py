from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, TextAreaField, BooleanField, SelectField, HiddenField
from wtforms.validators import DataRequired, Optional, Length
from datetime import date

class RegistroPontoForm(FlaskForm):
    """Formulário para registro de ponto simples (apenas entrada)"""
    # CORREÇÃO DEFINITIVA: Adicionado campo oculto para armazenar a data original como string
    data_original = HiddenField('Data Original')
    
    # CORREÇÃO DEFINITIVA: Removido default=date.today para forçar o usuário a selecionar uma data
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[DataRequired()])
    saida_almoco = TimeField('Saída para almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[DataRequired()])
    atividades = TextAreaField('Atividades realizadas', validators=[Optional(), Length(max=500)])

class RegistroMultiploPontoForm(FlaskForm):
    """Formulário para registro de ponto completo (entrada, saída, almoço, etc.)"""
    # CORREÇÃO DEFINITIVA: Adicionado campo oculto para armazenar a data original como string
    data_original = HiddenField('Data Original')
    
    # CORREÇÃO DEFINITIVA: Removido default=date.today para forçar o usuário a selecionar uma data
    data = DateField('Data', validators=[DataRequired()])
    entrada = StringField('Entrada (HH:MM)', validators=[Optional()])
    saida_almoco = StringField('Saída para Almoço (HH:MM)', validators=[Optional()])
    retorno_almoco = StringField('Retorno do Almoço (HH:MM)', validators=[Optional()])
    saida = StringField('Saída (HH:MM)', validators=[Optional()])
    afastamento = BooleanField('Afastamento', default=False)
    tipo_afastamento = SelectField('Tipo de Afastamento', 
                                  choices=[
                                      ('', 'Selecione'),
                                      ('ferias', 'Férias'),
                                      ('atestado', 'Atestado Médico'),
                                      ('licenca', 'Licença'),
                                      ('falta', 'Falta'),
                                      ('outro', 'Outro')
                                  ],
                                  validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional(), Length(max=500)])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional(), Length(max=1000)])

class EditarPontoForm(FlaskForm):
    """Formulário para edição de ponto"""
    # CORREÇÃO DEFINITIVA: Adicionado campo oculto para armazenar a data original como string
    data_original = HiddenField('Data Original')
    
    # CORREÇÃO DEFINITIVA: Removido default=date.today para forçar o usuário a selecionar uma data
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[DataRequired()])
    saida_almoco = TimeField('Saída para almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[DataRequired()])
    atividades = TextAreaField('Atividades realizadas', validators=[Optional(), Length(max=500)])

class AtividadeForm(FlaskForm):
    """Formulário para registro de atividade"""
    descricao = TextAreaField('Descrição da Atividade', validators=[DataRequired(), Length(max=1000)])

# CORREÇÃO: Adicionada a classe RegistroAfastamentoForm que estava faltando
class RegistroAfastamentoForm(FlaskForm):
    """Formulário para registro de afastamento (férias, licença, etc.)."""
    data = DateField('Data', validators=[DataRequired()])
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('Férias', 'Férias'),
        ('Licença Médica', 'Licença Médica'),
        ('Licença Maternidade/Paternidade', 'Licença Maternidade/Paternidade'),
        ('Falta Justificada', 'Falta Justificada'),
        ('Falta Não Justificada', 'Falta Não Justificada'),
        ('Compensação', 'Compensação'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
