from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Esta função é necessária para o Flask-Login carregar o usuário da sessão
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True) # Adicionado index para otimização
    matricula = db.Column(db.String(20), unique=True, nullable=False, index=True) # Adicionado index
    cargo = db.Column(db.String(100), nullable=True) # Permitir nulo temporariamente se houver dados antigos
    uf = db.Column(db.String(2), nullable=True) # Permitir nulo temporariamente
    telefone = db.Column(db.String(20), nullable=True) # Permitir nulo temporariamente
    vinculo = db.Column(db.String(50), nullable=False)
    foto_path = db.Column(db.String(255), nullable=True) # Permitir nulo, nem todos podem ter foto
    password_hash = db.Column(db.String(128), nullable=False) # Senha não deve ser nula
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- CORREÇÃO: Coluna para armazenar o status ativo no banco de dados ---
    # Esta coluna será gerenciada pelo administrador
    is_active_db = db.Column(db.Boolean, default=True, nullable=False, server_default='1')
    # -----------------------------------------------------------------------

    # Relacionamentos
    # cascade="all, delete-orphan" garante que os pontos do usuário sejam excluídos se o usuário for excluído
    pontos = db.relationship('Ponto', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Gera o hash da senha e armazena."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        # Garante que password_hash não seja None antes de verificar
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    # --- CORREÇÃO: Sobrescrevendo a propriedade is_active do UserMixin ---
    # Agora, a propriedade is_active lerá o valor da nossa coluna is_active_db
    @property
    def is_active(self):
        """Propriedade requerida pelo Flask-Login. Retorna o status da coluna do banco."""
        return self.is_active_db
    # -----------------------------------------------------------------------

    # Propriedades somente leitura (opcional, mas útil para Flask-Login)
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

