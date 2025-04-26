from app import db
from datetime import datetime, date, time

class Ponto(db.Model):
    """Modelo para os registros de ponto."""
    __tablename__ = 'pontos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    entrada = db.Column(db.Time, nullable=True)
    saida_almoco = db.Column(db.Time, nullable=True)
    retorno_almoco = db.Column(db.Time, nullable=True)
    saida = db.Column(db.Time, nullable=True)
    horas_trabalhadas = db.Column(db.Float, nullable=True) # Armazena como float (ex: 8.5 para 8h30m)
    observacoes = db.Column(db.Text, nullable=True)
    afastamento = db.Column(db.Boolean, default=False, nullable=False)
    tipo_afastamento = db.Column(db.String(100), nullable=True)
    # --- NOVO CAMPO ---
    resultados_produtos = db.Column(db.Text, nullable=True) # Campo para Resultados/Produtos Gerados
    # ------------------

    # Relacionamento com Atividades (um Ponto pode ter várias Atividades)
    # cascade="all, delete-orphan" garante que as atividades sejam excluídas se o ponto for excluído
    atividades = db.relationship('Atividade', backref='ponto', lazy=True, cascade="all, delete-orphan")

    # Índices compostos podem ser úteis para otimizar buscas por usuário e data
    __table_args__ = (db.Index('ix_ponto_user_data', 'user_id', 'data'), )

    def __repr__(self):
        return f'<Ponto {self.id} - User {self.user_id} - Data {self.data}>'

class Atividade(db.Model):
    """Modelo para as atividades diárias vinculadas a um registro de ponto."""
    __tablename__ = 'atividades'

    id = db.Column(db.Integer, primary_key=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey('pontos.id', ondelete='CASCADE'), nullable=False, index=True) # ondelete='CASCADE'
    descricao = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Adicionado para rastreamento

    def __repr__(self):
        return f'<Atividade {self.id} para Ponto {self.ponto_id}>'

