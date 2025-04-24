from app import db
from datetime import datetime, date

class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    descricao = db.Column(db.String(100), nullable=False)
    
    @property
    def nome(self):
        return self.descricao
        
    @property
    def tipo(self):
        return 'nacional'
        
    @property
    def created_at(self):
        return datetime.now()
        
    @property
    def updated_at(self):
        return datetime.now()
    
    def __repr__(self):
        return f'<Feriado {self.data} - {self.descricao}>'
