# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField, HiddenField, SubmitField
from wtforms.validators import DataRequired

class RelatorioCompletoForm(FlaskForm):
    """
    Formulário para coletar dados da autoavaliação para o relatório completo.
    """
    # Campo para autoavaliação do desempenho
    autoavaliacao = TextAreaField(
        'AUTOAVALIAÇÃO DO SERVIDOR(A)/COLABORADOR',
        validators=[DataRequired("A autoavaliação é obrigatória.")],
        render_kw={'rows': 5},
        description="Avalie seu desempenho no período, considerando o cumprimento das atividades, qualidade do trabalho, pontualidade, iniciativa e colaboração com a equipe."
    )
    # Campo para dificuldades observadas
    dificuldades = TextAreaField(
        'DIFICULDADES OU NECESSIDADES OBSERVADAS',
        validators=[DataRequired("Este campo é obrigatório.")],
        render_kw={'rows': 3}
    )
    # Campo para sugestões de melhoria
    sugestoes = TextAreaField(
        'SUGESTÕES DE MELHORIA',
        validators=[DataRequired("Este campo é obrigatório.")],
        render_kw={'rows': 3}
    )
    # Campo de declaração (checkbox obrigatório)
    declaracao = BooleanField(
        'Declaro que as informações acima refletem, com veracidade, as atividades desempenhadas por mim durante o período informado.',
        validators=[DataRequired(message="Você deve marcar a declaração de veracidade.")]
    )
    # Campos ocultos para passar dados para a rota POST
    user_id = HiddenField()
    mes = HiddenField()
    ano = HiddenField()
    # Botão de submit específico para este formulário
    submit_completo = SubmitField('Gerar PDF Completo com Autoavaliação')

