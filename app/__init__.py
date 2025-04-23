from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sqlite3
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()

def migrate_db(app):
    """Adiciona as colunas afastamento e tipo_afastamento à tabela pontos se não existirem"""
    with app.app_context():
        # Obtém o caminho do banco de dados da configuração do app
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Verifica se o arquivo do banco de dados existe
        if not os.path.exists(db_path):
            # O banco de dados será criado automaticamente pelo SQLAlchemy
            return
        
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verifica se a tabela pontos existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pontos'")
            if not cursor.fetchone():
                # A tabela será criada automaticamente pelo SQLAlchemy
                conn.close()
                return
            
            # Verifica se as colunas já existem
            cursor.execute("PRAGMA table_info(pontos)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Adiciona a coluna afastamento se não existir
            if 'afastamento' not in columns:
                app.logger.info("Adicionando coluna 'afastamento' à tabela pontos...")
                cursor.execute("ALTER TABLE pontos ADD COLUMN afastamento BOOLEAN DEFAULT 0")
                app.logger.info("Coluna 'afastamento' adicionada com sucesso!")
            
            # Adiciona a coluna tipo_afastamento se não existir
            if 'tipo_afastamento' not in columns:
                app.logger.info("Adicionando coluna 'tipo_afastamento' à tabela pontos...")
                cursor.execute("ALTER TABLE pontos ADD COLUMN tipo_afastamento VARCHAR(100)")
                app.logger.info("Coluna 'tipo_afastamento' adicionada com sucesso!")
            
            # Commit das alterações
            conn.commit()
            app.logger.info("Migração do banco de dados concluída com sucesso!")
            
            # Fecha a conexão
            conn.close()
            
        except sqlite3.Error as e:
            app.logger.error(f"Erro ao executar a migração do banco de dados: {e}")

def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Registra blueprints
    from app.controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.controllers.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    # Executa a migração do banco de dados automaticamente
    with app.app_context():
        # Cria as tabelas se não existirem
        db.create_all()
        # Executa a migração para adicionar as colunas necessárias
        migrate_db(app)
    
    return app
