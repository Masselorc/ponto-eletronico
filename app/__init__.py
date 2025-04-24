from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
import sqlite3
from dotenv import load_dotenv
import logging
import shutil
from app.utils.backup import backup_database

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def ensure_instance_directory(app):
    """Garante que o diretório instance exista e tenha as permissões corretas"""
    try:
        instance_path = app.instance_path
        app.logger.info(f"Verificando diretório instance: {instance_path}")
        
        # Cria o diretório instance se não existir
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)
            app.logger.info(f"Diretório instance criado: {instance_path}")
        
        # Garante que o diretório tenha permissões adequadas
        # Usa permissões mais restritivas configuráveis por ambiente
        permissions = int(os.environ.get('INSTANCE_DIR_PERMISSIONS', '0755'), 8)
        os.chmod(instance_path, permissions)
        app.logger.info(f"Permissões do diretório instance ajustadas para {oct(permissions)}")
        
        # No ambiente Render, verifica se o diretório está no disco persistente
        if os.environ.get('RENDER'):
            render_disk_path = '/opt/render/project/src/instance'
            
            # Garante que o diretório no disco persistente exista
            if not os.path.exists(render_disk_path):
                os.makedirs(render_disk_path, exist_ok=True)
                # Usa as mesmas permissões configuráveis
                os.chmod(render_disk_path, permissions)
                app.logger.info(f"Diretório no disco persistente criado: {render_disk_path}")
            
            # Se o diretório do disco persistente existir, mas não for o mesmo que instance_path
            if instance_path != render_disk_path:
                app.logger.info(f"Sincronizando dados do banco de dados com o disco persistente")
                
                # Copia arquivos .db do diretório instance para o disco persistente
                for file in os.listdir(instance_path):
                    if file.endswith('.db'):
                        src = os.path.join(instance_path, file)
                        dst = os.path.join(render_disk_path, file)
                        shutil.copy2(src, dst)
                        app.logger.info(f"Arquivo {file} copiado para o disco persistente")
    
    except Exception as e:
        app.logger.error(f"Erro ao verificar/criar diretório instance: {e}")
        # Registra o erro, mas não interrompe a execução

def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-padrao')
    
    # Configuração de logging mais detalhado
    if not app.debug:
        app.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(handler)
    
    # Configuração do banco de dados baseada em variáveis de ambiente
    db_uri = os.getenv('DATABASE_URI')
    if os.environ.get('RENDER'):
        # No ambiente Render, use o caminho configurável ou o padrão para o disco persistente
        db_path = os.getenv('RENDER_DB_PATH', '/opt/render/project/src/instance/ponto_eletronico.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.logger.info(f"Ambiente Render detectado. Usando caminho para o banco de dados: {db_path}")
    elif db_uri:
        # Usa a URI configurada na variável de ambiente
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.logger.info(f"Usando URI de banco de dados da variável de ambiente: {db_uri}")
    else:
        # Em ambiente de desenvolvimento, use o caminho relativo padrão
        db_path = os.path.join(app.instance_path, 'ponto_eletronico.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.logger.info(f"Usando caminho padrão para o banco de dados: {db_path}")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        # Garante que o diretório instance exista e tenha as permissões corretas
        ensure_instance_directory(app)
        
        try:
            # Cria as tabelas se não existirem (em desenvolvimento)
            # Em produção, as migrações devem ser executadas com flask db upgrade
            if os.environ.get('FLASK_ENV') == 'development':
                db.create_all()
                app.logger.info("Tabelas criadas em ambiente de desenvolvimento")
        except Exception as e:
            app.logger.error(f"Erro durante a inicialização do banco de dados: {e}")
            # Não propagar a exceção para permitir que a aplicação continue
    
    # Registra blueprints
    from app.controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.controllers.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    # Carrega o modelo User para o login_manager
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app
