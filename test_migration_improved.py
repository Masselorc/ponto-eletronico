"""
Script para testar a migração automática do banco de dados usando SQLAlchemy.
Este script simula o ambiente de produção para verificar se a migração
das colunas afastamento e tipo_afastamento ocorre corretamente.
"""

import os
import tempfile
import shutil
import logging
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto
from datetime import date

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_migration_improved():
    """Testa se a migração automática usando SQLAlchemy funciona corretamente"""
    logger.info("Iniciando teste de migração automática com SQLAlchemy...")
    
    # Cria um diretório temporário para o banco de dados de teste
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_db.sqlite')
    
    try:
        # Configura a variável de ambiente para o banco de dados de teste
        os.environ['DATABASE_URI'] = f'sqlite:///{db_path}'
        
        # Cria a aplicação com um banco de dados vazio
        app = create_app()
        
        with app.app_context():
            # Cria um usuário de teste
            user = User(
                name='Usuário Teste',
                email='teste@example.com',
                matricula='TEST001',
                vinculo='SENAPPEN',
                is_admin=False
            )
            user.set_password('senha123')
            db.session.add(user)
            db.session.commit()
            
            # Cria um registro de ponto de teste sem usar as colunas novas
            # Simula um registro antigo antes da migração
            conn = db.engine.raw_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pontos (user_id, data, entrada, saida) VALUES (?, ?, ?, ?)",
                (user.id, date.today().isoformat(), '08:00', '17:00')
            )
            conn.commit()
            conn.close()
            
            logger.info("Banco de dados de teste criado com sucesso")
            
            # Verifica se as colunas foram adicionadas
            ponto = Ponto.query.filter_by(user_id=user.id).first()
            
            # Verifica se o atributo afastamento existe e pode ser acessado
            try:
                afastamento = ponto.afastamento
                logger.info(f"Coluna 'afastamento' existe e tem valor: {afastamento}")
            except AttributeError:
                logger.error("ERRO: Coluna 'afastamento' não foi adicionada corretamente")
                return False
            
            # Verifica se o atributo tipo_afastamento existe e pode ser acessado
            try:
                tipo_afastamento = ponto.tipo_afastamento
                logger.info(f"Coluna 'tipo_afastamento' existe e tem valor: {tipo_afastamento}")
            except AttributeError:
                logger.error("ERRO: Coluna 'tipo_afastamento' não foi adicionada corretamente")
                return False
            
            # Tenta atualizar os valores das novas colunas
            ponto.afastamento = True
            ponto.tipo_afastamento = "Teste de Migração Automática"
            db.session.commit()
            
            # Verifica se os valores foram salvos corretamente
            ponto_atualizado = Ponto.query.filter_by(user_id=user.id).first()
            if ponto_atualizado.afastamento != True or ponto_atualizado.tipo_afastamento != "Teste de Migração Automática":
                logger.error("ERRO: Não foi possível atualizar os valores das novas colunas")
                return False
            
            logger.info("Valores das novas colunas atualizados com sucesso!")
        
        logger.info("Teste de migração automática com SQLAlchemy concluído com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
        return False
    
    finally:
        # Limpa o diretório temporário
        shutil.rmtree(temp_dir)
        # Restaura a variável de ambiente
        if 'DATABASE_URI' in os.environ:
            del os.environ['DATABASE_URI']

if __name__ == "__main__":
    test_migration_improved()
