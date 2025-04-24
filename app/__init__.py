from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sqlite3
from dotenv import load_dotenv
import logging
import shutil

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()

def migrate_db(app):
    """Adiciona as colunas necessárias à tabela pontos se não existirem"""
    try:
        # Usar diretamente a conexão do SQLAlchemy em vez de tentar acessar o arquivo
        app.logger.info("Iniciando migração do banco de dados...")
        
        # Verificar se a tabela pontos existe
        result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='pontos'"))
        if not result.fetchone():
            app.logger.info("Tabela 'pontos' não existe. Será criada automaticamente pelo SQLAlchemy.")
            return
        
        # Verificar se as colunas já existem
        result = db.session.execute(db.text("PRAGMA table_info(pontos)"))
        columns = [column[1] for column in result.fetchall()]
        
        # Adicionar a coluna afastamento se não existir
        if 'afastamento' not in columns:
            app.logger.info("Adicionando coluna 'afastamento' à tabela pontos...")
            db.session.execute(db.text("ALTER TABLE pontos ADD COLUMN afastamento BOOLEAN DEFAULT 0"))
            db.session.commit()
            app.logger.info("Coluna 'afastamento' adicionada com sucesso!")
        else:
            app.logger.info("Coluna 'afastamento' já existe.")
        
        # Adicionar a coluna tipo_afastamento se não existir
        if 'tipo_afastamento' not in columns:
            app.logger.info("Adicionando coluna 'tipo_afastamento' à tabela pontos...")
            db.session.execute(db.text("ALTER TABLE pontos ADD COLUMN tipo_afastamento VARCHAR(100)"))
            db.session.commit()
            app.logger.info("Coluna 'tipo_afastamento' adicionada com sucesso!")
        else:
            app.logger.info("Coluna 'tipo_afastamento' já existe.")
        
        # Adicionar a coluna observacoes se não existir
        if 'observacoes' not in columns:
            app.logger.info("Adicionando coluna 'observacoes' à tabela pontos...")
            db.session.execute(db.text("ALTER TABLE pontos ADD COLUMN observacoes TEXT"))
            db.session.commit()
            app.logger.info("Coluna 'observacoes' adicionada com sucesso!")
        else:
            app.logger.info("Coluna 'observacoes' já existe.")
        
        # Verificar se a tabela atividades existe
        result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='atividades'"))
        if not result.fetchone():
            app.logger.info("Tabela 'atividades' não existe. Criando...")
            db.session.execute(db.text("""
                CREATE TABLE atividades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ponto_id INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    FOREIGN KEY (ponto_id) REFERENCES pontos (id) ON DELETE CASCADE
                )
            """))
            db.session.commit()
            app.logger.info("Tabela 'atividades' criada com sucesso!")
        else:
            app.logger.info("Tabela 'atividades' já existe.")
        
        app.logger.info("Migração do banco de dados concluída com sucesso!")
        
    except Exception as e:
        app.logger.error(f"Erro ao executar a migração do banco de dados: {e}")
        # Não propagar a exceção para não impedir a inicialização da aplicação

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
        os.chmod(instance_path, 0o777)  # Permissões mais amplas para garantir acesso
        app.logger.info(f"Permissões do diretório instance ajustadas")
        
        # No ambiente Render, verifica se o diretório está no disco persistente
        if os.environ.get('RENDER'):
            render_disk_path = '/opt/render/project/src/instance'
            
            # Garante que o diretório no disco persistente exista
            if not os.path.exists(render_disk_path):
                os.makedirs(render_disk_path, exist_ok=True)
                os.chmod(render_disk_path, 0o777)  # Permissões mais amplas
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
    
    # Configuração do banco de dados para garantir persistência no Render
    if os.environ.get('RENDER'):
        # No ambiente Render, use o caminho absoluto para o banco de dados no disco persistente
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////opt/render/project/src/instance/ponto_eletronico.db'
        app.logger.info("Ambiente Render detectado. Usando caminho absoluto para o banco de dados no disco persistente.")
    else:
        # Em ambiente de desenvolvimento, use o caminho relativo
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///instance/ponto_eletronico.db')
        app.logger.info("Usando caminho relativo para o banco de dados em ambiente de desenvolvimento.")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        # Garante que o diretório instance exista e tenha as permissões corretas
        ensure_instance_directory(app)
        
        try:
            # Cria as tabelas se não existirem
            db.create_all()
            
            # Executa a migração para adicionar as colunas necessárias
            # Importante: isso deve ser feito antes de registrar os blueprints
            migrate_db(app)
        except Exception as e:
            app.logger.error(f"Erro durante a inicialização do banco de dados: {e}")
            # Não propagar a exceção para permitir que a aplicação continue
    
    # Registra blueprints após a migração do banco de dados
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
