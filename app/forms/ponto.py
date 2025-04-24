from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional

class RegistroPontoForm(FlaskForm):
    """Formulário para registrar ponto."""
    data = DateField('Data', validators=[DataRequired(message='Data é obrigatória')])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    
    # Campo oculto para armazenar a data original como string
    data_original = StringField('Data Original', validators=[Optional()])

class EditarPontoForm(FlaskForm):
    """Formulário para editar ponto."""
    data = DateField('Data', validators=[DataRequired(message='Data é obrigatória')])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    
    # Campo oculto para armazenar a data original como string
    data_original = StringField('Data Original', validators=[Optional()])

class RegistroFeriasForm(FlaskForm):
    """Formulário para registrar férias."""
    data = DateField('Data', validators=[DataRequired(message='Data é obrigatória')])
    
    # Campo oculto para armazenar a data original como string
    data_original = StringField('Data Original', validators=[Optional()])
