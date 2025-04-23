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
    # Removendo as definições diretas das colunas que não existem no banco
    
    # Propriedade híbrida para acessar 'nome' que na verdade é 'descricao' no banco
    @hybrid_property
    def nome(self):
        return self._nome
    
    @nome.setter
    def nome(self, value):
        self._nome = value
    
    # Propriedades para colunas que não existem no banco
    @property
    def tipo(self):
        return 'nacional'  # Valor padrão para todos os feriados
    
    @property
    def created_at(self):
        return datetime.now()  # Valor padrão
    
    @property
    def updated_at(self):
        return datetime.now()  # Valor padrão
    
    def __repr__(self):
        return f'<Feriado {self.nome} - {self.data}>'
