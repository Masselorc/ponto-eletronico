# -*- coding: utf-8 -*-
"""
Inicialização da Aplicação Flask.

Este módulo configura e inicializa a aplicação Flask, incluindo:
- Configuração da aplicação (chave secreta, URI do banco de dados).
- Inicialização de extensões (SQLAlchemy, LoginManager, Bootstrap).
- Registro de Blueprints (main, auth, admin).
- Criação das tabelas do banco de dados (se necessário).
- Tratamento de ambiente (desenvolvimento vs. produção/Render).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
# from flask_bootstrap import Bootstrap # Bootstrap pode ser carregado via CDN no base.html

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

# Inicialização das extensões (sem app ainda)
db = SQLAlchemy()
login_manager = LoginManager()
# Define a view de login (para onde @login_required redireciona)
login_manager.login_view = 'auth.login'
# Mensagem exibida quando o usuário tenta acessar uma página protegida sem login
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info' # Categoria da mensagem flash

# Bootstrap(app) # Inicialização do Bootstrap, se usado via extensão

# --- Função Factory da Aplicação ---
def create_app(config_class=None):
    """
    Cria e configura uma instância da aplicação Flask.

    Utiliza o padrão Application Factory.

    Args:
        config_class: Classe de configuração a ser usada. Se None, tenta detectar
                      o ambiente (Render vs. local).

    Returns:
        Instância da aplicação Flask configurada.
    """
    app = Flask(__name__)

    # --- Configuração ---
    # Define a chave secreta
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma-chave-secreta-muito-segura-padrao')

    # Configuração do Banco de Dados (SQLite por padrão, detecta Render)
    is_render_env = 'RENDER' in os.environ
    db_name = 'ponto_eletronico.db'
    instance_path = os.path.join(app.root_path, 'instance') # Caminho padrão da pasta instance

    if is_render_env:
        logger.info("Ambiente Render detectado.")
        # Em Render, usa o disco persistente montado em /data ou o diretório do projeto
        # Verifica se um disco persistente está configurado e montado em /data
        render_disk_path = '/data' # Caminho padrão do disco persistente no Render
        if os.path.exists(render_disk_path) and os.access(render_disk_path, os.W_OK):
             instance_path = render_disk_path
             logger.info(f"Usando disco persistente em: {instance_path}")
        else:
            # Se não houver disco persistente ou não for gravável, usa o diretório do projeto
            # ATENÇÃO: Dados serão perdidos entre deploys sem disco persistente!
            instance_path = os.path.join(app.root_path, 'instance')
            logger.warning(f"Disco persistente não encontrado ou não gravável em {render_disk_path}. Usando diretório local: {instance_path}. Dados podem ser perdidos.")

        db_path = os.path.join(instance_path, db_name)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"Usando banco de dados em: {app.config['SQLALCHEMY_DATABASE_URI']}")
    else:
        # Ambiente local
        logger.info("Ambiente local detectado.")
        db_path = os.path.join(instance_path, db_name)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"Usando banco de dados em: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Garante que a pasta 'instance' exista
    try:
        logger.info(f"Verificando diretório instance: {instance_path}")
        os.makedirs(instance_path, exist_ok=True)
        # Tenta ajustar permissões (pode falhar dependendo do ambiente)
        if sys.platform != 'win32': # chmod não existe no Windows
            try:
                os.chmod(instance_path, 0o777) # Permissão ampla para garantir escrita
                logger.info(f"Permissões do diretório instance ajustadas para 777")
            except OSError as e:
                 logger.warning(f"Não foi possível ajustar permissões para {instance_path}: {e}")
        else:
             logger.info("Ajuste de permissões não aplicável no Windows.")

    except OSError as e:
        logger.error(f"Erro ao criar ou verificar o diretório instance '{instance_path}': {e}", exc_info=True)
        # Decide se quer parar a aplicação ou continuar (pode falhar depois)
        # raise # Descomente para parar a aplicação se a pasta não puder ser criada

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Desativa rastreamento de modificações do SQLAlchemy

    # --- Inicialização das Extensões com a App ---
    db.init_app(app)
    login_manager.init_app(app)
    # Bootstrap(app) # Se for usar a extensão

    # --- Contexto da Aplicação ---
    with app.app_context():
        # CORREÇÃO: Importar todos os modelos ANTES de create_all()
        # Isso garante que SQLAlchemy conheça todas as tabelas e suas relações.
        logger.info("Importando modelos...")
        try:
            from app.models.user import User
            from app.models.ponto import Ponto, Afastamento, Atividade
            from app.models.feriado import Feriado
            logger.info("Modelos importados com sucesso.")
        except ImportError as e:
            logger.error(f"Erro ao importar modelos: {e}", exc_info=True)
            # Considerar levantar o erro ou retornar None para indicar falha na criação
            raise # Re-levanta o erro para parar a inicialização se modelos não puderem ser importados

        # Cria as tabelas do banco de dados, se não existirem
        # É seguro chamar create_all mesmo que as tabelas já existam
        logger.info("Executando db.create_all()...")
        try:
            db.create_all()
            logger.info("db.create_all() executado (tabelas criadas se não existiam).")
        except Exception as e:
            # Log detalhado do erro de banco de dados
            logger.error(f"Erro durante a inicialização do banco de dados (create_all): {e}", exc_info=True)
            # Você pode querer levantar o erro aqui para impedir que a app inicie sem DB
            # raise e # Descomente para parar a aplicação em caso de erro no DB

        # --- Registro dos Blueprints ---
        logger.info("Registrando blueprints...")
        try:
            from app.controllers.main import main as main_blueprint
            app.register_blueprint(main_blueprint)

            from app.controllers.auth import auth as auth_blueprint
            app.register_blueprint(auth_blueprint, url_prefix='/auth')

            from app.controllers.admin import admin as admin_blueprint
            app.register_blueprint(admin_blueprint, url_prefix='/admin')
            logger.info("Blueprints registrados com sucesso.")
        except Exception as e:
             logger.error(f"Erro ao registrar blueprints: {e}", exc_info=True)
             raise # Parar a inicialização se blueprints não puderem ser registrados

        # --- Configuração de Logging Adicional (Opcional) ---
        if not app.debug and not app.testing:
            # Log para arquivo em produção
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/ponto_eletronico.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Aplicação Ponto Eletrônico iniciada')

        logger.info("Criação da aplicação Flask concluída.")
        return app

# --- Carregador de Usuário para Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    """
    Função callback usada pelo Flask-Login para carregar um usuário
    a partir do ID armazenado na sessão.
    """
    # Importa User aqui para evitar dependência circular na inicialização
    from app.models.user import User
    try:
        # O user_id vem como string da sessão, converte para int
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Erro ao carregar usuário {user_id}: {e}")
        return None

# --- Verificação de Permissão de Administrador ---
# Decorator personalizado para verificar se o usuário é administrador
from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso restrito a administradores.', 'warning')
            # Redireciona para o dashboard ou outra página apropriada
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
