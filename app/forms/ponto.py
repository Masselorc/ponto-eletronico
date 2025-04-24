from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from datetime import date

class RegistroPontoForm(FlaskForm):
    """Formulário para registro de ponto."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional()])

class EditarPontoForm(FlaskForm):
    """Formulário para edição de registro de ponto."""
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional()])

class RegistroAfastamentoForm(FlaskForm):
    """Formulário para registro de afastamento (férias, licença, etc.)."""
    data = DateField('Data', validators=[DataRequired()], default=date.today)
    tipo_afastamento = SelectField('Tipo de Afastamento', choices=[
        ('Férias', 'Férias'),
        ('Licença Médica', 'Licença Médica'),
        ('Licença Maternidade/Paternidade', 'Licença Maternidade/Paternidade'),
        ('Licença Capacitação', 'Licença Capacitação'),
        ('Falta Justificada', 'Falta Justificada'),
        ('Falta Abonada', 'Falta Abonada'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
