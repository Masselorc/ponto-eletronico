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
    horas_trabalhadas = db.Column(db.Float, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    afastamento = db.Column(db.Boolean, default=False, nullable=False)
    tipo_afastamento = db.Column(db.String(100), nullable=True)
    # --- NOVO CAMPO ---
    resultados_produtos = db.Column(db.Text, nullable=True) # Campo para Resultados/Produtos Gerados
    # ------------------

    # Relacionamento com Atividades
    atividades = db.relationship('Atividade', backref='ponto', lazy=True, cascade="all, delete-orphan")

    __table_args__ = (db.Index('ix_ponto_user_data', 'user_id', 'data'), )

    def __repr__(self):
        return f'<Ponto {self.id} - User {self.user_id} - Data {self.data}>'

class Atividade(db.Model):
    """Modelo para as atividades diárias vinculadas a um registro de ponto."""
    __tablename__ = 'atividades'

    id = db.Column(db.Integer, primary_key=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey('pontos.id', ondelete='CASCADE'), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Atividade {self.id} para Ponto {self.ponto_id}>'

