# -*- coding: utf-8 -*-
"""
Modelo SQLAlchemy para a entidade User.

Este módulo define a classe User, que representa a tabela de usuários
no banco de dados, incluindo informações de autenticação e perfil.
Integra-se com Flask-Login para gerenciamento de sessão.

Classes:
    - User: Representa um usuário da aplicação.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager # Importa db e login_manager da inicialização

class User(UserMixin, db.Model):
    """Modelo para os usuários da aplicação."""
    # CORREÇÃO: Definindo explicitamente o nome da tabela como 'user'
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Aumentado para hashes mais longos
    nome_completo = db.Column(db.String(120), nullable=True)
    cargo = db.Column(db.String(80), nullable=True)
    jornada_diaria = db.Column(db.Float, default=8.0) # Jornada padrão de 8 horas
    is_admin = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True) # Para desativar usuários

    # Relacionamentos (já definidos com backref nos outros modelos)
    # pontos = db.relationship('Ponto', backref='autor', lazy='dynamic') # Exemplo se backref fosse 'autor'

    def set_password(self, password):
        """Gera o hash da senha e armazena."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} (Admin: {self.is_admin})>'

# O user_loader já está definido em app/__init__.py
# @login_manager.user_loader
# def load_user(id):
#     return User.query.get(int(id))
