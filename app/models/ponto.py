from app import db
from datetime import datetime, date, timedelta

class Ponto(db.Model):
    __tablename__ = 'pontos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # IMPORTANTE: Campo data sem valor padrão para evitar que a data atual seja usada automaticamente
    # Isso garante que a data selecionada pelo usuário seja sempre usada
    data = db.Column(db.Date, nullable=False)
    entrada = db.Column(db.Time, nullable=True)
    saida_almoco = db.Column(db.Time, nullable=True)
    retorno_almoco = db.Column(db.Time, nullable=True)
    saida = db.Column(db.Time, nullable=True)
    horas_trabalhadas = db.Column(db.Float, nullable=True)
    afastamento = db.Column(db.Boolean, default=False)
    tipo_afastamento = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    atividades = db.relationship('Atividade', backref='ponto', lazy=True, cascade="all, delete-orphan")
    
    def calcular_horas_trabalhadas(self):
        """Calcula as horas trabalhadas com base nos horários registrados"""
        if self.afastamento:
            self.horas_trabalhadas = 0
            return
            
        total_horas = 0
        
        # Período da manhã (entrada até saída para almoço)
        if self.entrada and self.saida_almoco:
            # IMPORTANTE: Usar a data do registro (self.data) em vez de date.today()
            delta_manha = datetime.combine(self.data, self.saida_almoco) - datetime.combine(self.data, self.entrada)
            total_horas += delta_manha.total_seconds() / 3600
            
        # Período da tarde (retorno do almoço até saída)
        if self.retorno_almoco and self.saida:
            # IMPORTANTE: Usar a data do registro (self.data) em vez de date.today()
            delta_tarde = datetime.combine(self.data, self.saida) - datetime.combine(self.data, self.retorno_almoco)
            total_horas += delta_tarde.total_seconds() / 3600
            
        # Se não tiver registro de almoço, mas tiver entrada e saída
        if self.entrada and self.saida and not (self.saida_almoco or self.retorno_almoco):
            # IMPORTANTE: Usar a data do registro (self.data) em vez de date.today()
            delta_total = datetime.combine(self.data, self.saida) - datetime.combine(self.data, self.entrada)
            total_horas = delta_total.total_seconds() / 3600
            
        self.horas_trabalhadas = round(total_horas, 1)
    
    def __repr__(self):
        return f'<Ponto {self.data} - Usuário {self.user_id}>'

class Atividade(db.Model):
    __tablename__ = 'atividades'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey('pontos.id', ondelete='CASCADE'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Atividade {self.id} - Ponto {self.ponto_id}>'
