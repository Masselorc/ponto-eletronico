from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    vinculo = db.Column(db.String(50), nullable=False)
    foto_path = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    pontos = db.relationship('Ponto', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.name}>'
