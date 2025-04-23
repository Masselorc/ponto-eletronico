from app import db
from datetime import datetime, date

class Ponto(db.Model):
    __tablename__ = 'pontos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    entrada = db.Column(db.Time, nullable=True)
    saida_almoco = db.Column(db.Time, nullable=True)
    retorno_almoco = db.Column(db.Time, nullable=True)
    saida = db.Column(db.Time, nullable=True)
    horas_trabalhadas = db.Column(db.Float, nullable=True)
    afastamento = db.Column(db.Boolean, default=False)
    tipo_afastamento = db.Column(db.String(100), nullable=True)
    
    # Relacionamentos
    atividades = db.relationship('Atividade', backref='ponto', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Ponto {self.data} - Usuário {self.user_id}>'

class Atividade(db.Model):
    __tablename__ = 'atividades'
    
    id = db.Column(db.Integer, primary_key=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey('pontos.id'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Atividade {self.id} - Ponto {self.ponto_id}>'

class Feriado(db.Model):
    __tablename__ = 'feriados'
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    descricao = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<Feriado {self.data} - {self.descricao}>'
