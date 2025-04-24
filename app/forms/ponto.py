from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional, Length

class RegistroPontoForm(FlaskForm):
    """Formulário para registro de ponto."""
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[DataRequired()])
    saida_almoco = TimeField('Saída para almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[DataRequired()])
    atividades = TextAreaField('Atividades realizadas', validators=[Optional(), Length(max=500)])

class EditarPontoForm(FlaskForm):
    """Formulário para edição de registro de ponto."""
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[DataRequired()])
    saida_almoco = TimeField('Saída para almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[DataRequired()])
    atividades = TextAreaField('Atividades realizadas', validators=[Optional(), Length(max=500)])

# CORREÇÃO: Modificar para permitir diferentes tipos de afastamento
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
