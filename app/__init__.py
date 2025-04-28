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
# --- CORREÇÃO: Importar modelo RelatorioMensalCompleto ---
from app.models.relatorio_completo import RelatorioMensalCompleto
# -------------------------------------------------------

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()
# --- CORREÇÃO CSRF: Criar instância do CSRFProtect ---
csrf = CSRFProtect()
# ---------------------------------------------------

# Nota: A função migrate_db foi movida para init_db_production.py

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
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar')
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
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    # Importar modelos ANTES de db.create_all e ANTES de registrar blueprints
    # Isso garante que o SQLAlchemy conheça os modelos
    from app.models.user import User
    from app.models.ponto import Ponto, Atividade
    from app.models.feriado import Feriado
    # A importação do RelatorioMensalCompleto já foi feita no topo

    with app.app_context():
        # Garante diretório instance
        ensure_instance_directory(app)
        try:
            # Cria tabelas se não existirem
            db.create_all()
            app.logger.info("db.create_all() executado (tabelas criadas se não existiam).")
            # A lógica de migração de colunas está em init_db_production.py
        except Exception as e:
            app.logger.error(f"Erro durante a inicialização do banco de dados (create_all): {e}", exc_info=True)
            raise

    # Processador de contexto para datetime
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Configura o user_loader ANTES de registrar os blueprints que usam @login_required
    @login_manager.user_loader
    def load_user(user_id):
        try:
            # Reimporta User aqui para garantir que está no escopo correto
            from app.models.user import User
            return User.query.get(int(user_id))
        except (ValueError, TypeError) as e:
             app.logger.error(f"Erro ao carregar usuário - ID inválido '{user_id}': {e}")
             return None
        except Exception as e:
            app.logger.error(f"Erro inesperado ao carregar usuário {user_id}: {e}", exc_info=True)
            return None

    # --- CORREÇÃO: Importar e registrar blueprints no final ---
    with app.app_context(): # Garante contexto para registro
        from app.controllers.auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)
        from app.controllers.main import main as main_blueprint
        app.register_blueprint(main_blueprint)
        from app.controllers.admin import admin as admin_blueprint
        app.register_blueprint(admin_blueprint)
    # --- FIM DA CORREÇÃO ---

    app.logger.info("Aplicação criada e configurada com sucesso.")
    return app
