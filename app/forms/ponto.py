from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, TimeField, SubmitField # Adicionado SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from datetime import date

# Opções padrão para tipo de afastamento
TIPO_AFASTAMENTO_CHOICES = [
    ('', '-- Selecione --'), # Opção vazia
    ('Férias', 'Férias'),
    ('Licença Médica', 'Licença Médica'),
    ('Licença Maternidade/Paternidade', 'Licença Maternidade/Paternidade'),
    ('Licença Capacitação', 'Licença Capacitação'),
    ('Falta Justificada', 'Falta Justificada'),
    ('Falta Abonada', 'Falta Abonada'),
    ('Outro', 'Outro')
]

class RegistroPontoForm(FlaskForm):
    """Formulário para registro de ponto."""
    # Data: Obrigatório, default para hoje
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")], default=date.today)
    # Horários: Opcionais
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    # Textos: Opcionais
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    # Botão de submit (pode ser adicionado aqui ou diretamente no template)
    submit = SubmitField('Registrar Ponto')

class EditarPontoForm(FlaskForm):
    """Formulário para edição de registro de ponto."""
    # Data: Obrigatório
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")])
    # Horários: Opcionais
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    # Textos: Opcionais
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()])
    observacoes = TextAreaField('Observações', validators=[Optional()])

    # --- CORREÇÃO: Adicionando os campos que faltavam ---
    afastamento = BooleanField('Férias ou outros afastamentos')
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[Optional()] # Opcional por padrão, validação será feita no controller se afastamento=True
    )
    # Não adicionamos submit aqui, pois é melhor colocá-lo direto no HTML
    # ----------------------------------------------------

class RegistroAfastamentoForm(FlaskForm):
    """Formulário para registro de afastamento (férias, licença, etc.)."""
    # Data: Obrigatório, default para hoje
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")], default=date.today)
    # Tipo de Afastamento: Obrigatório para este formulário
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[DataRequired("Selecione o tipo de afastamento.")]
    )
    submit = SubmitField('Registrar Afastamento')

# Nota: O formulário RegistroMultiploPontoForm não está definido aqui,
# a rota correspondente parece ler os dados diretamente de request.form.getlist.
# Se fosse usar WTForms, seria necessário criar um FieldList de um FormField.
