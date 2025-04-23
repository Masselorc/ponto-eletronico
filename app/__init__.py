from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sqlite3
from dotenv import load_dotenv
import logging

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()

def migrate_db(app):
    """Adiciona as colunas afastamento e tipo_afastamento à tabela pontos se não existirem"""
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
        
        app.logger.info("Migração do banco de dados concluída com sucesso!")
        
    except Exception as e:
        app.logger.error(f"Erro ao executar a migração do banco de dados: {e}")
        # Não propagar a exceção para não impedir a inicialização da aplicação

def create_app():
    # Cria e configura a aplicação
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configurar logging mais detalhado
    if not app.debug:
        app.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(handler)
    
    # Inicializa extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        # Cria as tabelas se não existirem
        db.create_all()
        
        # Executa a migração para adicionar as colunas necessárias
        # Importante: isso deve ser feito antes de registrar os blueprints
        migrate_db(app)
    
    # Registra blueprints após a migração do banco de dados
    from app.controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.controllers.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    return app
