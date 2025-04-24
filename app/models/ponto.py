from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app import db
import logging

logger = logging.getLogger(__name__)

class Ponto(db.Model):
    """Modelo para registro de ponto."""
    __tablename__ = 'pontos'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # CORREÇÃO DEFINITIVA: Removido o valor padrão date.today() para o campo data
    data = Column(Date, nullable=False)
    entrada = Column(Time, nullable=True)
    saida_almoco = Column(Time, nullable=True)
    retorno_almoco = Column(Time, nullable=True)
    saida = Column(Time, nullable=True)
    afastamento = Column(Boolean, default=False)
    tipo_afastamento = Column(String(50), nullable=True)
    observacoes = Column(Text, nullable=True)
    horas_trabalhadas = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = relationship('User', back_populates='pontos')
    atividades = relationship('Atividade', back_populates='ponto', cascade='all, delete-orphan')
    
    def calcular_horas_trabalhadas(self):
        """Calcula as horas trabalhadas no dia."""
        # Se for um dia de afastamento, não há horas trabalhadas
        if self.afastamento:
            self.horas_trabalhadas = 0
            return
        
        # Se não tiver entrada ou saída, não é possível calcular
        if not self.entrada or not self.saida:
            self.horas_trabalhadas = 0
            return
        
        # CORREÇÃO: Usar a data do registro em vez de date.today()
        data_registro = self.data
        logger.info(f"Calculando horas trabalhadas para a data: {data_registro}")
        
        # Cria objetos datetime para os horários
        entrada_dt = datetime.combine(data_registro, self.entrada)
        saida_dt = datetime.combine(data_registro, self.saida)
        
        # Se tiver horário de almoço, desconta do total
        if self.saida_almoco and self.retorno_almoco:
            saida_almoco_dt = datetime.combine(data_registro, self.saida_almoco)
            retorno_almoco_dt = datetime.combine(data_registro, self.retorno_almoco)
            
            # Calcula o tempo total trabalhado
            tempo_antes_almoco = (saida_almoco_dt - entrada_dt).total_seconds() / 3600
            tempo_depois_almoco = (saida_dt - retorno_almoco_dt).total_seconds() / 3600
            self.horas_trabalhadas = tempo_antes_almoco + tempo_depois_almoco
        else:
            # Calcula o tempo total trabalhado sem intervalo de almoço
            self.horas_trabalhadas = (saida_dt - entrada_dt).total_seconds() / 3600
        
        logger.info(f"Horas trabalhadas calculadas: {self.horas_trabalhadas}")
        return self.horas_trabalhadas

class Atividade(db.Model):
    """Modelo para registro de atividades realizadas."""
    __tablename__ = 'atividades'
    
    id = Column(Integer, primary_key=True)
    ponto_id = Column(Integer, ForeignKey('pontos.id'), nullable=False)
    descricao = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    ponto = relationship('Ponto', back_populates='atividades')
