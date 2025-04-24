from app import db
from datetime import datetime, date, timedelta
from app.models.feriado import Feriado

class Ponto(db.Model):
    """
    Modelo para representar registros de ponto no sistema.
    
    Atributos:
        id (int): Identificador único do registro de ponto
        user_id (int): ID do usuário associado ao registro
        data (date): Data do registro
        entrada (datetime): Horário de entrada
        saida_almoco (datetime): Horário de saída para almoço
        retorno_almoco (datetime): Horário de retorno do almoço
        saida (datetime): Horário de saída
        horas_trabalhadas (float): Total de horas trabalhadas
        afastamento (bool): Indica se é um registro de afastamento
        tipo_afastamento (str): Tipo de afastamento, se aplicável
        observacoes (str): Observações sobre o registro
    """
    __tablename__ = 'pontos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    entrada = db.Column(db.DateTime, nullable=True)
    saida_almoco = db.Column(db.DateTime, nullable=True)
    retorno_almoco = db.Column(db.DateTime, nullable=True)
    saida = db.Column(db.DateTime, nullable=True)
    horas_trabalhadas = db.Column(db.Float, nullable=True)
    afastamento = db.Column(db.Boolean, default=False)
    tipo_afastamento = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    atividades = db.relationship('Atividade', backref='ponto', lazy=True, cascade="all, delete-orphan")
    
    def calcular_horas_trabalhadas(self):
        """
        Calcula as horas trabalhadas com base nos horários registrados.
        
        Se for um registro de afastamento, as horas trabalhadas são zero.
        Caso contrário, calcula com base nos horários de entrada, saída para almoço,
        retorno do almoço e saída.
        
        Validações são aplicadas para garantir que os horários estejam em ordem cronológica.
        """
        if self.afastamento:
            self.horas_trabalhadas = 0
            return
            
        total_horas = 0
        
        # Validar ordem cronológica dos horários
        if self.entrada and self.saida_almoco and self.entrada > self.saida_almoco:
            # Se os horários estiverem fora de ordem, não calcula
            return
            
        if self.retorno_almoco and self.saida and self.retorno_almoco > self.saida:
            # Se os horários estiverem fora de ordem, não calcula
            return
            
        # Período da manhã (entrada até saída para almoço)
        if self.entrada and self.saida_almoco:
            delta_manha = self.saida_almoco - self.entrada
            total_horas += delta_manha.total_seconds() / 3600
            
        # Período da tarde (retorno do almoço até saída)
        if self.retorno_almoco and self.saida:
            delta_tarde = self.saida - self.retorno_almoco
            total_horas += delta_tarde.total_seconds() / 3600
            
        # Se não tiver registro de almoço, mas tiver entrada e saída
        if self.entrada and self.saida and not (self.saida_almoco or self.retorno_almoco):
            delta_total = self.saida - self.entrada
            total_horas = delta_total.total_seconds() / 3600
            
        self.horas_trabalhadas = round(total_horas, 1)
    
    def __repr__(self):
        """Representação em string do objeto."""
        return f'<Ponto {self.data} - Usuário {self.user_id}>'

class Atividade(db.Model):
    """
    Modelo para representar atividades associadas a registros de ponto.
    
    Atributos:
        id (int): Identificador único da atividade
        ponto_id (int): ID do registro de ponto associado
        descricao (str): Descrição da atividade
        created_at (datetime): Data e hora de criação da atividade
    """
    __tablename__ = 'atividades'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey('pontos.id', ondelete='CASCADE'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        """Representação em string do objeto."""
        return f'<Atividade {self.id} - Ponto {self.ponto_id}>'
