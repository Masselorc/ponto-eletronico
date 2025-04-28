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

# --- CORREÇÃO: Definir extensões globalmente, mas sem inicializar ---
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
# --- FIM DA CORREÇÃO ---

# A importação do modelo RelatorioMensalCompleto foi removida daqui
# Será importado dentro de create_app ou onde for necessário, após a inicialização do db

def ensure_instance_directory(app):
    """Garante que o diretório instance exista e tenha as permissões corretas"""
    try:
        instance_path = app.instance_path
        # app.logger.info(f"Verificando diretório instance: {instance_path}") # Removido log excessivo
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")
        # Tentar ajustar permissões pode não ser necessário ou possível no Render
        # try:
        #      os.chmod(instance_path, 0o777)
        #      app.logger.info(f"Permissões do diretório instance ajustadas para 777")
        # except OSError as e:
        #      app.logger.warning(f"Não foi possível alterar permissões do diretório instance: {e}")

        render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
        if os.environ.get('RENDER'):
            # app.logger.info(f"Ambiente Render detectado. Verificando disco persistente em: {render_disk_mount_path}") # Removido log excessivo
            if not os.path.exists(render_disk_mount_path):
                os.makedirs(render_disk_mount_path, exist_ok=True)
                app.logger.info(f"Diretório no disco persistente criado: {render_disk_mount_path}")
                # Tentar ajustar permissões pode não ser necessário ou possível no Render
                # try:
                #     os.chmod(render_disk_mount_path, 0o777)
                #     app.logger.info(f"Permissões do diretório no disco persistente ajustadas para 777")
                # except OSError as e:
                #     app.logger.warning(f"Não foi possível alterar permissões do diretório no disco persistente: {e}")
    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}", exc_info=True)


def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar-padrao') # Usar um padrão mais seguro
    app.config['WTF_CSRF_ENABLED'] = True

    # Configuração de logging
    log_level = logging.DEBUG if os.environ.get('FLASK_DEBUG', '0') == '1' else logging.INFO # Usar FLASK_DEBUG
    # Remover handlers existentes para evitar duplicação em recargas
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    # Configurar handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    # Remover logs padrão do Werkzeug se não estiver em debug para logs mais limpos
    if log_level != logging.DEBUG:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)


    # Configuração do banco de dados
    render_disk_mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', app.instance_path)
    db_name = 'ponto_eletronico.db'
    default_db_path = os.path.join(render_disk_mount_path, db_name)

    # Prioriza DATABASE_URL se definida (comum no Render)
    db_uri = os.getenv('DATABASE_URL')
    if not db_uri:
        if os.environ.get('RENDER'):
            db_uri = f'sqlite:///{default_db_path}'
            app.logger.info(f"Ambiente Render detectado. Usando banco de dados SQLite em: {db_uri}")
        else: # Desenvolvimento
            dev_db_path = os.path.join(app.instance_path, db_name)
            db_uri = f'sqlite:///{dev_db_path}'
            app.logger.info(f"Ambiente de desenvolvimento. Usando banco de dados SQLite em: {db_uri}")
    else:
         # Se DATABASE_URL foi definida, ajusta para SQLAlchemy se for Postgres
         if db_uri.startswith("postgres://"):
             db_uri = db_uri.replace("postgres://", "postgresql://", 1)
         app.logger.info(f"Usando DATABASE_URL: {db_uri}")

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False # Desativar echo SQL em produção

    # --- CORREÇÃO: Inicializar extensões com o app AQUI ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    # --- FIM DA CORREÇÃO ---

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    # Importar modelos AQUI, depois de db ter sido inicializado com init_app
    # Isso garante que os modelos possam usar o 'db' corretamente
    from app.models.user import User
    from app.models.ponto import Ponto, Atividade
    from app.models.feriado import Feriado
    from app.models.relatorio_completo import RelatorioMensalCompleto

    with app.app_context():
        # Garante diretório instance
        ensure_instance_directory(app)
        try:
            # Cria tabelas se não existirem
            # A migração de colunas (ALTER TABLE) ainda deve ser tratada
            # separadamente (ex: em init_db_production.py ou com Flask-Migrate)
            # db.create_all() # Comentado temporariamente para focar no erro de importação
            app.logger.info("db.create_all() chamado (se descomentado).")
        except Exception as e:
            app.logger.error(f"Erro durante db.create_all(): {e}", exc_info=True)
            # Não levantar exceção aqui permite que o app continue inicializando
            # para registrar blueprints, mas o DB pode não estar pronto.

    # Processador de contexto para datetime
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Configura o user_loader
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

    # Importar e registrar blueprints DEPOIS de tudo inicializado
    with app.app_context():
        from app.controllers.auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)
        from app.controllers.main import main as main_blueprint
        app.register_blueprint(main_blueprint)
        from app.controllers.admin import admin as admin_blueprint
        app.register_blueprint(admin_blueprint)
        app.logger.info("Blueprints registrados.")

    app.logger.info("Aplicação Flask criada e configurada.")
    return app

