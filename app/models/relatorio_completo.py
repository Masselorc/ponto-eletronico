# -*- coding: utf-8 -*-
from app import db
from datetime import datetime

class RelatorioMensalCompleto(db.Model):
    """
    Modelo para armazenar os dados da autoavaliação salva para um relatório mensal.
    """
    __tablename__ = 'relatorios_completos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ano = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)

    # Dados da autoavaliação
    autoavaliacao = db.Column(db.Text, nullable=False)
    dificuldades = db.Column(db.Text, nullable=False)
    sugestoes = db.Column(db.Text, nullable=False)
    declaracao_marcada = db.Column(db.Boolean, nullable=False, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraint para garantir que só exista um relatório salvo por usuário/mês/ano
    __table_args__ = (db.UniqueConstraint('user_id', 'ano', 'mes', name='uq_user_ano_mes_relatorio'), )

    # Relacionamento (opcional, mas útil)
    usuario = db.relationship('User', backref=db.backref('relatorios_completos', lazy=True))

    def __repr__(self):
        return f'<RelatorioMensalCompleto User {self.user_id} - {self.mes}/{self.ano}>'
