import os
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def backup_database(app):
    """
    Cria um backup do banco de dados antes de executar migrações.
    
    Args:
        app: A instância da aplicação Flask
        
    Returns:
        bool: True se o backup foi criado com sucesso, False caso contrário
    """
    try:
        # Obtém o caminho do banco de dados a partir da configuração
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Verifica se é um banco SQLite
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            
            # Se o caminho for relativo, converte para absoluto
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.root_path, '..', db_path)
            
            # Normaliza o caminho
            db_path = os.path.normpath(db_path)
            
            # Verifica se o arquivo existe
            if os.path.exists(db_path):
                # Cria o diretório de backup se não existir
                backup_dir = os.path.join(app.instance_path, 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                
                # Cria o nome do arquivo de backup com timestamp
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                backup_filename = f"ponto_eletronico_{timestamp}.db.backup"
                backup_path = os.path.join(backup_dir, backup_filename)
                
                # Copia o arquivo
                shutil.copy2(db_path, backup_path)
                
                # Registra o sucesso
                app.logger.info(f"Backup do banco de dados criado em {backup_path}")
                return True
            else:
                app.logger.warning(f"Arquivo de banco de dados não encontrado: {db_path}")
        else:
            app.logger.warning("Backup automático só é suportado para bancos SQLite")
    except Exception as e:
        app.logger.error(f"Erro ao criar backup do banco de dados: {e}")
    
    return False

def list_backups(app):
    """
    Lista todos os backups disponíveis.
    
    Args:
        app: A instância da aplicação Flask
        
    Returns:
        list: Lista de caminhos para os arquivos de backup
    """
    backup_dir = os.path.join(app.instance_path, 'backups')
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db.backup'):
            backups.append(os.path.join(backup_dir, filename))
    
    # Ordena por data (mais recente primeiro)
    backups.sort(reverse=True)
    return backups

def restore_backup(app, backup_path):
    """
    Restaura um backup do banco de dados.
    
    Args:
        app: A instância da aplicação Flask
        backup_path: Caminho para o arquivo de backup
        
    Returns:
        bool: True se a restauração foi bem-sucedida, False caso contrário
    """
    try:
        # Obtém o caminho do banco de dados a partir da configuração
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Verifica se é um banco SQLite
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            
            # Se o caminho for relativo, converte para absoluto
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.root_path, '..', db_path)
            
            # Normaliza o caminho
            db_path = os.path.normpath(db_path)
            
            # Verifica se o arquivo de backup existe
            if os.path.exists(backup_path):
                # Cria um backup do banco atual antes de restaurar
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                pre_restore_backup = os.path.join(os.path.dirname(db_path), 
                                                f"pre_restore_{timestamp}.db")
                
                # Só faz o backup pré-restauração se o banco atual existir
                if os.path.exists(db_path):
                    shutil.copy2(db_path, pre_restore_backup)
                    app.logger.info(f"Backup pré-restauração criado em {pre_restore_backup}")
                
                # Copia o backup para o local do banco de dados
                shutil.copy2(backup_path, db_path)
                
                # Registra o sucesso
                app.logger.info(f"Banco de dados restaurado a partir de {backup_path}")
                return True
            else:
                app.logger.warning(f"Arquivo de backup não encontrado: {backup_path}")
        else:
            app.logger.warning("Restauração automática só é suportada para bancos SQLite")
    except Exception as e:
        app.logger.error(f"Erro ao restaurar backup do banco de dados: {e}")
    
    return False
