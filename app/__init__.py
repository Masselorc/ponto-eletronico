from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os
import sqlite3
from dotenv import load_dotenv
import logging
import shutil
from datetime import datetime
import calendar

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Definir extensões globalmente, mas sem inicializar
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def ensure_instance_directory(app):
    """Garante que o diretório instance exista."""
    # (Código da função inalterado)
    try:
        instance_path = app.instance_path
        # app.logger.info(f"Verificando diretório instance: {instance_path}") # Removido log excessivo
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")

        render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
        if os.environ.get('RENDER'):
            # app.logger.info(f"Ambiente Render detectado. Verificando disco persistente em: {render_disk_mount_path}") # Removido log excessivo
            if not os.path.exists(render_disk_mount_path):
                os.makedirs(render_disk_mount_path, exist_ok=True)
                app.logger.info(f"Diretório no disco persistente criado: {render_disk_mount_path}")
    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}", exc_info=True)


def create_app():
    """Cria e configura a instância da aplicação Flask."""
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar-padrao')
    app.config['WTF_CSRF_ENABLED'] = True

    # Configuração de logging
    log_level = logging.INFO # Usar INFO por padrão em produção
    if os.environ.get('FLASK_DEBUG') == '1':
        log_level = logging.DEBUG
    for handler in app.logger.handlers[:]: app.logger.removeHandler(handler)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    if log_level != logging.DEBUG: logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # Configuração do banco de dados
    render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
    db_name = 'ponto_eletronico.db'
    default_db_path = os.path.join(render_disk_mount_path, db_name)
    db_uri = os.getenv('DATABASE_URL')
    if not db_uri:
        db_uri = f'sqlite:///{default_db_path}'
        app.logger.info(f"Usando banco de dados SQLite em: {db_uri}")
    else:
         if db_uri.startswith("postgres://"): db_uri = db_uri.replace("postgres://", "postgresql://", 1)
         app.logger.info(f"Usando DATABASE_URL: {db_uri}")
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False

    # Inicializar extensões com o app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    # Importar modelos AQUI, APÓS db.init_app(app)
    from app.models.user import User
    from app.models.ponto import Ponto, Atividade
    from app.models.feriado import Feriado
    from app.models.relatorio_completo import RelatorioMensalCompleto

    # Configura o user_loader ANTES de registrar blueprints
    @login_manager.user_loader
    def load_user(user_id):
        # A importação do User já foi feita acima
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError) as e:
             app.logger.error(f"Erro ao carregar usuário - ID inválido '{user_id}': {e}")
             return None
        except Exception as e:
            app.logger.error(f"Erro inesperado ao carregar usuário {user_id}: {e}", exc_info=True)
            return None

    # Processador de contexto para datetime
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Registrar blueprints DENTRO do contexto da aplicação
    with app.app_context():
        # Garante diretório instance antes de criar tabelas
        ensure_instance_directory(app)
        try:
            # Cria tabelas se não existirem
            db.create_all()
            app.logger.info("db.create_all() chamado.")
        except Exception as e:
            app.logger.error(f"Erro durante db.create_all(): {e}", exc_info=True)
            # Considerar se deve levantar a exceção ou apenas logar

        # Importar e registrar blueprints AQUI, dentro do contexto e após db.create_all
        from app.controllers.auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)
        from app.controllers.main import main as main_blueprint
        app.register_blueprint(main_blueprint)
        from app.controllers.admin import admin as admin_blueprint
        app.register_blueprint(admin_blueprint)
        app.logger.info("Blueprints registrados.")

    app.logger.info("Aplicação Flask criada e configurada.")
    return app
