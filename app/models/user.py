# -*- coding: utf-8 -*-
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Esta função é necessária para o Flask-Login carregar o usuário da sessão
@login_manager.user_loader
def load_user(user_id):
    # Adicionado tratamento de erro para IDs inválidos
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        # Log ou tratamento adicional pode ser inserido aqui
        return None

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    cargo = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    vinculo = db.Column(db.String(50), nullable=False)
    foto_path = db.Column(db.String(255), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active_db = db.Column(db.Boolean, default=True, nullable=False, server_default='1')

    # --- NOVOS CAMPOS ADICIONADOS ---
    unidade_setor = db.Column(db.String(150), nullable=False, server_default='') # Unidade/Setor de Lotação na DIRPP
    chefia_imediata = db.Column(db.String(100), nullable=False, server_default='') # Nome da Chefia Imediata
    # ---------------------------------

    # Relacionamentos
    pontos = db.relationship('Ponto', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Gera o hash da senha e armazena."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        """Propriedade requerida pelo Flask-Login. Retorna o status da coluna do banco."""
        return self.is_active_db

    @property
    def is_authenticated(self):
        """Propriedade requerida pelo Flask-Login. Sempre True para usuários logados."""
        return True

    @property
    def is_anonymous(self):
        """Propriedade requerida pelo Flask-Login. Sempre False para usuários logados."""
        return False

    def get_id(self):
        """Método requerido pelo Flask-Login. Retorna o ID do usuário como string."""
        return str(self.id)

    def __repr__(self):
        """Representação em string do objeto User."""
        return f'<User {self.id}: {self.name} ({self.email})>'

