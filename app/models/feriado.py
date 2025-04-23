from app import db
from datetime import datetime

class Feriado(db.Model):
    __tablename__ = 'feriados'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data = db.Column(db.Date, nullable=False, unique=True)
    tipo = db.Column(db.String(20), default='nacional')  # nacional, estadual, municipal
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Feriado {self.nome} - {self.data}>'
