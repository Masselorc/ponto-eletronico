from app import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    # Mapeando a coluna 'descricao' do banco para o atributo 'nome' no modelo
    _nome = db.Column('descricao', db.String(255), nullable=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    tipo = db.Column(db.String(20), default='nacional')  # nacional, estadual, municipal
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Propriedade híbrida para acessar 'nome' que na verdade é 'descricao' no banco
    @hybrid_property
    def nome(self):
        return self._nome
    
    @nome.setter
    def nome(self, value):
        self._nome = value
    
    def __repr__(self):
        return f'<Feriado {self.nome} - {self.data}>'
