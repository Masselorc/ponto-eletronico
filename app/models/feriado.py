from app import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

class Feriado(db.Model):
    """
    Modelo para representar feriados no sistema.
    
    Atributos:
        id (int): Identificador único do feriado
        descricao (str): Descrição/nome do feriado
        data (date): Data do feriado
    
    Propriedades virtuais:
        nome (str): Alias para descricao, mantido para compatibilidade
        tipo (str): Tipo do feriado (sempre 'nacional')
        created_at (datetime): Data de criação (virtual)
        updated_at (datetime): Data de atualização (virtual)
    """
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Date, nullable=False, unique=True)
    
    # Propriedade híbrida para manter compatibilidade com código existente
    @property
    def nome(self):
        """Alias para o campo descricao, mantido para compatibilidade."""
        return self.descricao
    
    @nome.setter
    def nome(self, value):
        """Setter para o alias nome."""
        self.descricao = value
    
    # Propriedades virtuais documentadas
    @property
    def tipo(self):
        """
        Tipo do feriado (propriedade virtual).
        
        Returns:
            str: Sempre retorna 'nacional'
        """
        return 'nacional'  # Valor padrão para todos os feriados
    
    @property
    def created_at(self):
        """
        Data de criação (propriedade virtual).
        
        Returns:
            datetime: Data e hora atual
        """
        return datetime.now()  # Valor padrão
    
    @property
    def updated_at(self):
        """
        Data de atualização (propriedade virtual).
        
        Returns:
            datetime: Data e hora atual
        """
        return datetime.now()  # Valor padrão
    
    def __repr__(self):
        """Representação em string do objeto."""
        return f'<Feriado {self.descricao} - {self.data}>'
