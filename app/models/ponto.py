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
from sqlalchemy.orm import relationship # Importar relationship

# CORREÇÃO: Importar User explicitamente ANTES das classes dependentes
# Isso ajuda SQLAlchemy a resolver a referência da ForeignKey.
try:
    from app.models.user import User
except ImportError:
    # Fallback ou log se necessário, mas idealmente User deve estar disponível
    User = None # Ou levante um erro mais informativo
    print("AVISO: Não foi possível importar o modelo User em app.models.ponto")


class Ponto(db.Model):
    """Modelo para os registros de ponto."""
    __tablename__ = 'ponto' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    # Garante que 'user.id' corresponda à tabela/coluna de User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data = db.Column(db.Date, nullable=False, index=True) # Adicionado índice para otimizar buscas por data
    hora = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'Entrada' ou 'Saída'
    observacao = db.Column(db.Text, nullable=True)

    # Relacionamento com o usuário (opcional, mas útil)
    # O backref 'pontos' permite acessar os pontos a partir de um objeto User
    # Usando string "User" para evitar potencial import circular, mas a importação acima é preferível
    user = relationship("User", backref=db.backref('pontos', lazy='dynamic')) # Usar lazy='dynamic' para coleções grandes

    def __repr__(self):
        # Usar user.username se o relacionamento estiver ativo e carregado
        # Adiciona verificação se self.user existe (pode não estar carregado)
        user_info = self.user.username if self.user else f"UserID:{self.user_id}"
        return f"<Ponto {user_info} {self.data.strftime('%Y-%m-%d')} {self.hora.strftime('%H:%M')} ({self.tipo})>"

class Afastamento(db.Model):
    """Modelo para os registros de afastamento (férias, licenças, etc.)."""
    __tablename__ = 'afastamento' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    # Garante que 'user.id' corresponda à tabela/coluna de User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False, index=True) # Índice
    data_fim = db.Column(db.Date, nullable=False, index=True) # Índice
    motivo = db.Column(db.String(100), nullable=False)
    timestamp_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamento com o usuário
    user = relationship("User", backref=db.backref('afastamentos', lazy='dynamic'))

    def __repr__(self):
        user_info = self.user.username if self.user else f"UserID:{self.user_id}"
        return f"<Afastamento {user_info} {self.data_inicio.strftime('%d/%m/%Y')}-{self.data_fim.strftime('%d/%m/%Y')} ({self.motivo})>"

class Atividade(db.Model):
    """Modelo para os registros de atividade externa ou home office."""
    __tablename__ = 'atividade' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    # Garante que 'user.id' corresponda à tabela/coluna de User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True) # Índice
    descricao = db.Column(db.Text, nullable=False)
    timestamp_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamento com o usuário
    user = relationship("User", backref=db.backref('atividades', lazy='dynamic'))

    def __repr__(self):
        user_info = self.user.username if self.user else f"UserID:{self.user_id}"
        return f"<Atividade {user_info} {self.data.strftime('%d/%m/%Y')} ({self.descricao[:20]}...)>"

# Nota: A importação explícita de User no topo deste arquivo é a principal
# tentativa de corrigir o NoReferencedTableError.
# Se estiver usando Flask-Migrate, lembre-se das migrações.
