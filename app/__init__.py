from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sqlite3
from dotenv import load_dotenv
import logging
import shutil
# --- CORREÇÃO: Importar datetime ---
from datetime import datetime
# -----------------------------------

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()

def migrate_db(app):
    """Adiciona as colunas necessárias às tabelas se não existirem"""
    try:
        app.logger.info("Iniciando migração do banco de dados (se necessário)...")
        with app.app_context(): # Garante contexto da aplicação
             with db.engine.connect() as connection:

                # Função helper para verificar e adicionar coluna
                def ensure_column(conn, table, col_name, col_def):
                    cursor = conn.execute(db.text(f"PRAGMA table_info({table})"))
                    columns = [c[1] for c in cursor.fetchall()]
                    if col_name not in columns:
                        app.logger.info(f"Adicionando coluna '{col_name}' à tabela '{table}'...")
                        # Executar ALTER TABLE dentro da conexão existente
                        conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                        # Para SQLite, commit pode não ser necessário para ALTER, mas não prejudica
                        # Se a conexão não estiver em autocommit, um commit pode ser necessário
                        # conn.commit() # Descomente se necessário, mas geralmente DDL é auto-commit
                        app.logger.info(f"Coluna '{col_name}' adicionada com sucesso!")
                    else:
                         app.logger.info(f"Coluna '{col_name}' já existe na tabela '{table}'.")

                # Verificar se a tabela pontos existe
                result_table = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='pontos'"))
                if result_table.fetchone():
                    # Adicionar colunas à tabela pontos
                    ensure_column(connection, 'pontos', 'afastamento', 'BOOLEAN DEFAULT 0')
                    ensure_column(connection, 'pontos', 'tipo_afastamento', 'VARCHAR(100)')
                    ensure_column(connection, 'pontos', 'observacoes', 'TEXT')
                else:
                    app.logger.info("Tabela 'pontos' não encontrada. Será criada por db.create_all().")

                # Verificar se a tabela atividades existe
                result_table = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='atividades'"))
                if result_table.fetchone():
                     # Adicionar coluna à tabela atividades
                    ensure_column(connection, 'atividades', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
                else:
                     app.logger.info("Tabela 'atividades' não encontrada. Será criada por db.create_all().")

                # Verificar se a tabela users existe
                result_table = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                if result_table.fetchone():
                    # Adicionar coluna à tabela users
                    ensure_column(connection, 'users', 'is_active_db', 'BOOLEAN NOT NULL DEFAULT 1')
                else:
                    app.logger.info("Tabela 'users' não encontrada. Será criada por db.create_all().")


        app.logger.info("Migração/Verificação do banco de dados concluída.")

    except Exception as e:
        app.logger.error(f"Erro ao executar a migração do banco de dados: {e}", exc_info=True)
        # Considerar relançar o erro se a migração for crítica para o startup
        # raise

def ensure_instance_directory(app):
    """Garante que o diretório instance exista e tenha as permissões corretas"""
    try:
        instance_path = app.instance_path
        app.logger.info(f"Verificando diretório instance: {instance_path}")

        # Cria o diretório instance se não existir
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")

        # Garante que o diretório tenha permissões adequadas (importante no Render)
        try:
             os.chmod(instance_path, 0o777) # Permissões mais amplas para garantir acesso
             app.logger.info(f"Permissões do diretório instance ajustadas para 777")
        except OSError as e:
             app.logger.warning(f"Não foi possível alterar permissões do diretório instance: {e}")


        # No ambiente Render, verifica se o diretório está no disco persistente
        render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', '/opt/render/project/src/instance')
        if os.environ.get('RENDER'):
            app.logger.info(f"Ambiente Render detectado. Verificando disco persistente em: {render_disk_mount_path}")

            # Garante que o diretório no disco persistente exista
            if not os.path.exists(render_disk_mount_path):
                os.makedirs(render_disk_mount_path, exist_ok=True)
                try:
                    os.chmod(render_disk_mount_path, 0o777) # Permissões mais amplas
                    app.logger.info(f"Diretório no disco persistente criado: {render_disk_mount_path}")
                except OSError as e:
                    app.logger.warning(f"Não foi possível alterar permissões do diretório no disco persistente: {e}")

    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}", exc_info=True)


def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True é boa prática
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev') # Usar 'dev' apenas para desenvolvimento

    # Configuração de logging
    log_level = logging.DEBUG if os.environ.get('DEBUG', 'False').lower() == 'true' else logging.INFO
    app.logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    if not app.logger.handlers:
        app.logger.addHandler(handler)

    # Configuração do banco de dados
    render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path) # Usar instance_path como fallback
    db_name = 'ponto_eletronico.db'
    default_db_path = os.path.join(render_disk_mount_path, db_name)

    if os.environ.get('RENDER'):
        db_uri = f'sqlite:///{default_db_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.logger.info(f"Ambiente Render detectado. Usando banco de dados em: {db_uri}")
    else:
        # Em desenvolvimento, usa instance_path que agora é relativo à raiz da app
        dev_db_path = os.path.join(app.instance_path, db_name)
        db_uri = f'sqlite:///{dev_db_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.logger.info(f"Ambiente de desenvolvimento. Usando banco de dados em: {db_uri}")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning" # Usar warning para mais destaque

    with app.app_context():
        # Garante diretório instance
        ensure_instance_directory(app)

        try:
            # Cria tabelas se não existirem
            db.create_all()
            app.logger.info("db.create_all() executado.")

            # Executa a migração/verificação de colunas
            migrate_db(app)
        except Exception as e:
            app.logger.error(f"Erro durante a inicialização do banco de dados (create_all/migrate_db): {e}", exc_info=True)
            raise # Re-lançar o erro é importante para saber que a inicialização falhou

    # --- CORREÇÃO: Adicionar processador de contexto para datetime ---
    @app.context_processor
    def inject_now():
        return {'datetime': datetime} # Disponibiliza o módulo datetime inteiro
    # -------------------------------------------------------------

    # Importar e registrar blueprints DEPOIS da inicialização e migração
    from app.controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.controllers.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # Importar modelos DEPOIS de db.init_app()
    from app.models.user import User

    # Configura o user_loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            # Tenta converter para int e buscar o usuário
            return User.query.get(int(user_id))
        except (ValueError, TypeError) as e:
             app.logger.error(f"Erro ao carregar usuário - ID inválido '{user_id}': {e}")
             return None
        except Exception as e:
            app.logger.error(f"Erro inesperado ao carregar usuário {user_id}: {e}", exc_info=True)
            return None

    app.logger.info("Aplicação criada e configurada com sucesso.")
    return app
