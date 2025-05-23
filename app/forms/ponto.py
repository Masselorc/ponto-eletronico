# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, TimeField, SubmitField
# --- Adicionado ValidationError e datetime ---
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from datetime import date, datetime, timedelta, time # Adicionado time
# -------------------------------------------

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
    resultados_produtos = TextAreaField('Resultados/Produtos Gerados', validators=[Optional()], render_kw={"rows": 3})
    observacoes = TextAreaField('Observações', validators=[Optional()], render_kw={"rows": 2})

    # --- Validação customizada para almoço ---
    # --- CORREÇÃO: Adicionado parâmetro extra_validators ---
    def validate(self, extra_validators=None):
    # --- FIM DA CORREÇÃO ---
        # Executa validações padrão primeiro
        if not super(RegistroPontoForm, self).validate(extra_validators):
            return False

        # Validação do almoço apenas se entrada e saída foram preenchidas
        if self.entrada.data and self.saida.data:
            if not self.saida_almoco.data or not self.retorno_almoco.data:
                self.saida_almoco.errors.append('Os horários de início e fim do almoço são obrigatórios para dias trabalhados.')
                return False # Falha na validação

            try:
                data_ref = self.data.data or date(1900, 1, 1)
                saida_almoco_dt = datetime.combine(data_ref, self.saida_almoco.data)
                retorno_almoco_dt = datetime.combine(data_ref, self.retorno_almoco.data)

                if retorno_almoco_dt <= saida_almoco_dt:
                    retorno_almoco_dt += timedelta(days=1)

                duracao_almoco = retorno_almoco_dt - saida_almoco_dt
                if duracao_almoco.total_seconds() < 3600:
                    self.retorno_almoco.errors.append('O intervalo de almoço deve ter duração mínima de 1 hora.')
                    return False
            except (TypeError, ValueError) as e:
                 self.saida_almoco.errors.append(f'Erro ao calcular duração do almoço: {e}')
                 return False

        return True
    # --- Fim da Validação ---

class EditarPontoForm(FlaskForm):
    """Formulário para edição de registro de ponto."""
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    retorno_almoco = TimeField('Retorno do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    atividades = TextAreaField('Atividades Realizadas', validators=[Optional()], render_kw={"rows": 3})
    resultados_produtos = TextAreaField('Resultados/Produtos Gerados', validators=[Optional()], render_kw={"rows": 3})
    observacoes = TextAreaField('Observações', validators=[Optional()], render_kw={"rows": 2})
    afastamento = BooleanField('Marcar como Afastamento (Férias, Licença, etc.)')
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[Optional()]
    )

    # --- Validação customizada para almoço e tipo de afastamento ---
    # --- CORREÇÃO: Adicionado parâmetro extra_validators ---
    def validate(self, extra_validators=None):
    # --- FIM DA CORREÇÃO ---
        if not super(EditarPontoForm, self).validate(extra_validators):
            return False

        is_afastamento = self.afastamento.data
        tipo_afastamento_val = self.tipo_afastamento.data

        if is_afastamento and not tipo_afastamento_val:
            self.tipo_afastamento.errors.append('Selecione o Tipo de Afastamento quando "Afastamento" estiver marcado.')
            return False

        if not is_afastamento and self.entrada.data and self.saida.data:
            if not self.saida_almoco.data or not self.retorno_almoco.data:
                self.saida_almoco.errors.append('Os horários de início e fim do almoço são obrigatórios para dias trabalhados.')
                return False

            try:
                data_ref = self.data.data or date(1900, 1, 1)
                saida_almoco_dt = datetime.combine(data_ref, self.saida_almoco.data)
                retorno_almoco_dt = datetime.combine(data_ref, self.retorno_almoco.data)

                if retorno_almoco_dt <= saida_almoco_dt:
                    retorno_almoco_dt += timedelta(days=1)

                duracao_almoco = retorno_almoco_dt - saida_almoco_dt
                if duracao_almoco.total_seconds() < 3600:
                    self.retorno_almoco.errors.append('O intervalo de almoço deve ter duração mínima de 1 hora.')
                    return False
            except (TypeError, ValueError) as e:
                 self.saida_almoco.errors.append(f'Erro ao calcular duração do almoço: {e}')
                 return False

        return True
    # --- Fim da Validação ---


class RegistroAfastamentoForm(FlaskForm):
    """Formulário para registro de afastamento (férias, licença, etc.)."""
    data = DateField('Data', validators=[DataRequired("O campo Data é obrigatório.")], default=date.today)
    tipo_afastamento = SelectField(
        'Tipo de Afastamento',
        choices=TIPO_AFASTAMENTO_CHOICES,
        validators=[DataRequired(message="Selecione o tipo de afastamento.")]
    )

class AtividadeForm(FlaskForm):
    """Formulário para registrar/editar atividades de um ponto."""
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
