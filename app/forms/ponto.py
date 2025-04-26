# -*- coding: utf-8 -*-
"""
Formulários WTForms para as funcionalidades de Ponto do Usuário.

Este módulo define as classes de formulário usadas nas rotas
relacionadas ao registro e gerenciamento de pontos, afastamentos e atividades
pelo usuário comum.

Classes:
    - RegistroPontoForm: Formulário para registrar um único ponto (entrada/saída).
    - DateForm: Formulário simples para selecionar uma data.
    - EditarPontoForm: Formulário para editar um registro de ponto existente.
    - PontoEntryForm: Sub-formulário para uma entrada de ponto (usado em MultiRegistroPontoForm).
    - MultiRegistroPontoForm: Formulário para registrar/editar múltiplos pontos em um dia.
    - AfastamentoForm: Formulário para registrar um período de afastamento (férias, licença).
    - AtividadeForm: Formulário para registrar uma atividade externa ou home office.
"""

from datetime import date, time, datetime
from flask_wtf import FlaskForm
# Adicionado 'validators' à importação do WTForms
from wtforms import (StringField, SubmitField, SelectField, TimeField, DateField,
                     TextAreaField, FieldList, FormField, validators)
# Importar validadores específicos necessários
from wtforms.validators import DataRequired, Optional, ValidationError, Length

# Validador customizado para garantir que a hora esteja no formato correto
def time_check(form, field):
    """Validador para garantir que a hora esteja no formato HH:MM."""
    if field.data:
        try:
            if isinstance(field.data, time):
                 pass # Já é um objeto time
            else:
                 time.fromisoformat(str(field.data)) # Tenta converter de string
        except (ValueError, TypeError):
            raise ValidationError('Formato de hora inválido. Use HH:MM.')

class RegistroPontoForm(FlaskForm):
    """Formulário para registrar um único ponto (entrada ou saída)."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    hora = TimeField('Hora (HH:MM)', validators=[Optional(), time_check], format='%H:%M')
    tipo = SelectField('Tipo', choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')], validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=500)])
    # CORREÇÃO Ponto 6: Adicionado campo atividades
    atividades = TextAreaField('Atividades Realizadas (Opcional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Registrar Ponto')

class DateForm(FlaskForm):
    """Formulário simples para selecionar uma data."""
    data = DateField('Selecione a Data', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Visualizar')

class EditarPontoForm(FlaskForm):
    """Formulário para editar um registro de ponto existente."""
    data = DateField('Data', validators=[DataRequired()])
    hora = TimeField('Hora (HH:MM)', validators=[DataRequired(), time_check], format='%H:%M')
    tipo = SelectField('Tipo', choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')], validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional(), Length(max=500)])
    # CORREÇÃO Ponto 6: Adicionado campo atividades
    atividades = TextAreaField('Atividades Realizadas (Opcional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Salvar Alterações')

class PontoEntryForm(FlaskForm):
    """
    Sub-formulário para representar uma única entrada/saída de ponto.
    Usado dentro do MultiRegistroPontoForm.
    """
    hora = TimeField('Hora', validators=[Optional(), time_check], format='%H:%M')
    tipo = SelectField('Tipo', choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')], validators=[Optional()])
    observacao = StringField('Observação', validators=[Optional(), Length(max=200)])

class MultiRegistroPontoForm(FlaskForm):
    """Formulário para registrar múltiplos pontos em um dia."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    pontos = FieldList(FormField(PontoEntryForm), min_entries=1)
    submit = SubmitField('Salvar Registros do Dia')

# --- Formulários adicionados para Afastamento e Atividade ---

class AfastamentoForm(FlaskForm):
    """Formulário para registrar um período de afastamento."""
    data_inicio = DateField('Data de Início', validators=[DataRequired()], default=date.today)
    data_fim = DateField('Data Final', validators=[DataRequired()], default=date.today)
    motivo = StringField('Motivo', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Registrar Afastamento')

    def validate_data_fim(self, field):
        """Valida se a data final não é anterior à data inicial."""
        if self.data_inicio.data and field.data:
            if field.data < self.data_inicio.data:
                raise ValidationError('A data final não pode ser anterior à data inicial.')

class AtividadeForm(FlaskForm):
    """Formulário para registrar uma atividade externa ou home office."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    descricao = TextAreaField('Descrição da Atividade', validators=[DataRequired(), Length(min=5, max=200)])
    submit = SubmitField('Registrar Atividade')

