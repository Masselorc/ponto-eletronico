from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# --- CORREÇÃO CSRF: Importar CSRFProtect ---
from flask_wtf.csrf import CSRFProtect
# ------------------------------------------
import os
import sqlite3
from dotenv import load_dotenv
import logging
import shutil
from datetime import datetime
import calendar # Importar calendar aqui se migrate_db for movida para cá

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()
# --- CORREÇÃO CSRF: Criar instância do CSRFProtect ---
csrf = CSRFProtect()
# ---------------------------------------------------

# Nota: A função migrate_db foi movida para init_db_production.py
# Se for necessário executá-la também na inicialização normal da app (não apenas no build),
# ela precisaria ser definida aqui ou importada. Por agora, vamos assumir
# que a migração durante o build é suficiente.

# def migrate_db(app):
#    """Adiciona as colunas necessárias às tabelas se não existirem"""
#    # ... (código da função migrate_db, adaptado se necessário) ...
#    pass


def ensure_instance_directory(app):
    """Garante que o diretório instance exista e tenha as permissões corretas"""
    try:
        instance_path = app.instance_path
        app.logger.info(f"Verificando diretório instance: {instance_path}")
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")
        try:
             os.chmod(instance_path, 0o777)
             app.logger.info(f"Permissões do diretório instance ajustadas para 777")
        except OSError as e:
             app.logger.warning(f"Não foi possível alterar permissões do diretório instance: {e}")

        render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
        if os.environ.get('RENDER'):
            app.logger.info(f"Ambiente Render detectado. Verificando disco persistente em: {render_disk_mount_path}")
            if not os.path.exists(render_disk_mount_path):
                os.makedirs(render_disk_mount_path, exist_ok=True)
                try:
                    os.chmod(render_disk_mount_path, 0o777)
                    app.logger.info(f"Diretório no disco persistente criado: {render_disk_mount_path}")
                except OSError as e:
                    app.logger.warning(f"Não foi possível alterar permissões do diretório no disco persistente: {e}")
    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}", exc_info=True)


def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__, instance_relative_config=True)
    # Define a chave secreta - ESSENCIAL para CSRF e sessões
    # Render deve injetar uma chave segura via variável de ambiente
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar')
    # Adiciona configuração para habilitar CSRF (já é True por padrão, mas explícito é bom)
    app.config['WTF_CSRF_ENABLED'] = True

    # Configuração de logging
    log_level = logging.DEBUG if os.environ.get('DEBUG', 'False').lower() == 'true' else logging.INFO
    app.logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    if not app.logger.handlers:
        app.logger.addHandler(handler)

    # Configuração do banco de dados
    render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
    db_name = 'ponto_eletronico.db'
    default_db_path = os.path.join(render_disk_mount_path, db_name)
    if os.environ.get('RENDER'):
        db_uri = f'sqlite:///{default_db_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.logger.info(f"Ambiente Render detectado. Usando banco de dados em: {db_uri}")
    else:
        dev_db_path = os.path.join(app.instance_path, db_name)
        db_uri = f'sqlite:///{dev_db_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.logger.info(f"Ambiente de desenvolvimento. Usando banco de dados em: {db_uri}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    # --- CORREÇÃO CSRF: Inicializar CSRFProtect ---
    csrf.init_app(app)
    # ---------------------------------------------
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    with app.app_context():
        # Garante diretório instance
        ensure_instance_directory(app)
        try:
            # Cria tabelas se não existirem
            # Nota: A migração de colunas agora está no script init_db_production.py
            # Se precisar que a migração ocorra a cada inicialização,
            # a lógica de migrate_db() precisaria estar aqui.
            db.create_all()
            app.logger.info("db.create_all() executado (tabelas criadas se não existiam).")
            # migrate_db(app) # Descomente se a migração for necessária em cada inicialização
        except Exception as e:
            app.logger.error(f"Erro durante a inicialização do banco de dados (create_all): {e}", exc_info=True)
            raise

    # Processador de contexto para datetime
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Importar e registrar blueprints
    from app.controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    from app.controllers.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from app.controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # Importar modelos
    from app.models.user import User

    # Configura o user_loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError) as e:
             app.logger.error(f"Erro ao carregar usuário - ID inválido '{user_id}': {e}")
             return None
        except Exception as e:
            app.logger.error(f"Erro inesperado ao carregar usuário {user_id}: {e}", exc_info=True)
            return None

    app.logger.info("Aplicação criada e configurada com sucesso.")
    return app
