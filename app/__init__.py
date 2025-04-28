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
# --- Adicionar Flask-Migrate ---
from flask_migrate import Migrate
# -----------------------------

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
# --- Inicializar Migrate ---
migrate = Migrate()
# -------------------------

def ensure_instance_directory(app):
    """Garante que o diretório instance exista."""
    try:
        instance_path = app.instance_path
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")

        # --- Garante que o mountPath do disco exista ---
        render_disk_mount_path = app.config.get('RENDER_DISK_MOUNT_PATH', instance_path) # Pega do config
        if not os.path.exists(render_disk_mount_path):
             os.makedirs(render_disk_mount_path, exist_ok=True)
             app.logger.info(f"Diretório no disco persistente criado: {render_disk_mount_path}")
        # ---------------------------------------------

    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}", exc_info=True)


def create_app():
    """Cria e configura a instância da aplicação Flask."""
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar-padrao')
    app.config['WTF_CSRF_ENABLED'] = True

    # Configuração de logging (mantida)
    log_level = logging.INFO
    if os.environ.get('FLASK_DEBUG') == '1':
        log_level = logging.DEBUG
    for handler in app.logger.handlers[:]: app.logger.removeHandler(handler)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    if log_level != logging.DEBUG: logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # --- Configuração do Banco de Dados (MODIFICADA) ---
    # Define o caminho absoluto para o disco persistente
    render_disk_mount_path = '/opt/render/project/src/instance' # Caminho fixo do render.yaml
    app.config['RENDER_DISK_MOUNT_PATH'] = render_disk_mount_path # Guarda para ensure_instance_directory
    db_name = 'ponto_eletronico.db'
    db_path = os.path.join(render_disk_mount_path, db_name)
    db_uri = f'sqlite:///{db_path}' # Usa SEMPRE o caminho absoluto

    app.logger.info(f"Usando banco de dados SQLite em: {db_uri}") # Log para confirmar
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False # Manter False em produção
    # ---------------------------------------------------

    # --- Garante diretório ANTES de inicializar DB ---
    ensure_instance_directory(app)
    # -----------------------------------------------

    # Inicializar extensões com o app
    db.init_app(app)
    # --- Inicializar Migrate ---
    migrate.init_app(app, db)
    # -------------------------
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

    # Configura o user_loader (mantido)
    @login_manager.user_loader
    def load_user(user_id):
        try:
            # Tenta converter para int e buscar o usuário
            return User.query.get(int(user_id))
        except (ValueError, TypeError) as e:
             # Loga o erro se o ID não for um inteiro válido
             app.logger.error(f"Erro ao carregar usuário - ID inválido '{user_id}': {e}")
             return None
        except Exception as e:
            # Loga qualquer outro erro inesperado durante a busca
            app.logger.error(f"Erro inesperado ao carregar usuário {user_id}: {e}", exc_info=True)
            return None


    # Processador de contexto para datetime (mantido)
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Registrar blueprints DENTRO do contexto da aplicação
    with app.app_context():
        # db.create_all() não é mais necessário aqui se usar Flask-Migrate
        # A migração inicial criará as tabelas.

        # Importar e registrar blueprints AQUI
        from app.controllers.auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)
        from app.controllers.main import main as main_blueprint
        app.register_blueprint(main_blueprint)
        from app.controllers.admin import admin as admin_blueprint
        app.register_blueprint(admin_blueprint)
        app.logger.info("Blueprints registrados.")

    app.logger.info("Aplicação Flask criada e configurada.")
    return app
