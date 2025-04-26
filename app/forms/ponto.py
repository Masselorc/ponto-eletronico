from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from datetime import date

# Opções padrão para tipo de afastamento
TIPO_AFASTAMENTO_CHOICES = [
    ('', '-- Selecione --'),
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
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")], default=date.today)
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()], render_kw={"rows": 3})
    # --- NOVO CAMPO ---
    resultados_produtos = TextAreaField('Resultados/Produtos Gerados', validators=[Optional()], render_kw={"rows": 3})
    # ------------------
    observacoes = TextAreaField('Observações', validators=[Optional()], render_kw={"rows": 2})
    # submit = SubmitField('Registrar Ponto')

class EditarPontoForm(FlaskForm):
    """Formulário para edição de registro de ponto."""
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()], render_kw={"rows": 3})
    # --- NOVO CAMPO ---
    resultados_produtos = TextAreaField('Resultados/Produtos Gerados', validators=[Optional()], render_kw={"rows": 3})
    # ------------------
    observacoes = TextAreaField('Observações', validators=[Optional()], render_kw={"rows": 2})
    afastamento = BooleanField('Marcar como Afastamento (Férias, Licença, etc.)')
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[Optional()]
    )
    # submit = SubmitField('Salvar Alterações')

class RegistroAfastamentoForm(FlaskForm):
    """Formulário para registro de afastamento (férias, licença, etc.)."""
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")], default=date.today)
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[DataRequired(message="Selecione o tipo de afastamento.")]
    )
    # submit = SubmitField('Registrar Afastamento')

class AtividadeForm(FlaskForm):
    """Formulário para registrar/editar atividades de um ponto."""
    # Nota: Este form é separado, não inclui resultados/produtos
    descricao = TextAreaField(
        'Descrição das Atividades',
        validators=[DataRequired("A descrição das atividades é obrigatória."), Length(min=5, message="Descreva um pouco mais as atividades (mínimo 5 caracteres).")],
        render_kw={"rows": 4, "placeholder": "Descreva as principais atividades realizadas neste dia..."}
    )
    submit = SubmitField('Salvar Atividade')

class MultiploPontoForm(FlaskForm):
    """Formulário vazio usado apenas para gerar o token CSRF
       na página de registro de múltiplos pontos."""
    pass

