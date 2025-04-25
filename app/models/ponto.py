# -*- coding: utf-8 -*-
"""
Modelos SQLAlchemy para a entidade Ponto e relacionadas.

Este módulo define as classes que representam as tabelas no banco de dados
relacionadas aos registros de ponto, afastamentos e atividades dos usuários.

Classes:
    - Ponto: Representa um registro de ponto (entrada ou saída).
    - Afastamento: Representa um período de afastamento (férias, licença).
    - Atividade: Representa um dia de atividade externa ou home office.
"""

from datetime import datetime
from app import db
from sqlalchemy.orm import relationship

class Ponto(db.Model):
    """Modelo para os registros de ponto."""
    __tablename__ = 'ponto' # Definindo o nome da tabela explicitamente

    id = db.Column(db.Integer, primary_key=True)
    # Chave estrangeira referenciando a tabela 'user' (geralmente 'user' ou 'users')
    # Assumindo que o modelo User tem uma tabela chamada 'user'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'Entrada' ou 'Saída'
    observacao = db.Column(db.Text, nullable=True)

    # Relacionamento com o usuário (opcional, mas útil)
    # O backref 'pontos' permite acessar os pontos a partir de um objeto User
    # user = relationship("User", backref=db.backref('pontos', lazy=True))

    def __repr__(self):
        return f"<Ponto {self.user_id} {self.data.strftime('%Y-%m-%d')} {self.hora.strftime('%H:%M')} ({self.tipo})>"

# CORREÇÃO: Adicionando os modelos Afastamento e Atividade

class Afastamento(db.Model):
    """Modelo para os registros de afastamento (férias, licenças, etc.)."""
    __tablename__ = 'afastamento'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    motivo = db.Column(db.String(100), nullable=False)
    timestamp_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamento opcional com o usuário
    user = relationship("User", backref=db.backref('afastamentos', lazy=True))

    def __repr__(self):
        return f"<Afastamento {self.user_id} {self.data_inicio.strftime('%d/%m/%Y')}-{self.data_fim.strftime('%d/%m/%Y')} ({self.motivo})>"

class Atividade(db.Model):
    """Modelo para os registros de atividade externa ou home office."""
    __tablename__ = 'atividade'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    timestamp_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamento opcional com o usuário
    user = relationship("User", backref=db.backref('atividades', lazy=True))

    def __repr__(self):
        return f"<Atividade {self.user_id} {self.data.strftime('%d/%m/%Y')} ({self.descricao[:20]}...)>"

# Nota: Certifique-se de que a classe User está definida (provavelmente em app/models/user.py)
# e que a inicialização do db (SQLAlchemy) está correta em app/__init__.py.
# Se você estiver usando Flask-Migrate, lembre-se de gerar e aplicar as migrações
# após adicionar novos modelos:
# flask db migrate -m "Add Afastamento and Atividade models"
# flask db upgrade
