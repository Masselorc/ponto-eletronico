# -*- coding: utf-8 -*-
"""
Inicialização da Aplicação Flask.

Este módulo configura e inicializa a aplicação Flask, incluindo:
- Configuração da aplicação (chave secreta, URI do banco de dados).
- Inicialização de extensões (SQLAlchemy, LoginManager, CSRFProtect).
- Registro de Blueprints (main, auth, admin).
- Criação das tabelas do banco de dados (se necessário).
- Tratamento de ambiente (desenvolvimento vs. produção/Render).
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
# CORREÇÃO: Importar CSRFProtect
from flask_wtf.csrf import CSRFProtect

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

# Inicialização das extensões (sem app ainda)
db = SQLAlchemy()
login_manager = LoginManager()
# CORREÇÃO: Inicializar CSRFProtect
csrf = CSRFProtect()

# Define a view de login (para onde @login_required redireciona)
login_manager.login_view = 'auth.login'
# Mensagem exibida quando o usuário tenta acessar uma página protegida sem login
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info' # Categoria da mensagem flash

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
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True é boa prática

    # --- Configuração ---
    # Define a chave secreta - ESSENCIAL para CSRF e sessões
    # Use uma variável de ambiente em produção! Ex: os.environ.get('SECRET_KEY')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma-chave-secreta-muito-segura-padrao-para-dev')
    # Adicionar configuração para WTForms CSRF (geralmente True por padrão, mas explícito é bom)
    app.config['WTF_CSRF_ENABLED'] = True

    # Configuração do Banco de Dados (SQLite por padrão, detecta Render)
    is_render_env = 'RENDER' in os.environ
    db_name = 'ponto_eletronico.db'
    # Caminho da pasta 'instance' relativo à raiz da aplicação
    # instance_path_default = app.instance_path # Flask define isso automaticamente com instance_relative_config=True
    instance_path_default = os.path.join(os.path.dirname(os.path.dirname(app.root_path)), 'instance') # Garante ser na raiz do projeto


    if is_render_env:
        logger.info("Ambiente Render detectado.")
        # Em Render, usa o disco persistente montado em /data
        render_disk_path = '/data' # Caminho padrão do disco persistente no Render
        instance_path = render_disk_path
        logger.info(f"Tentando usar disco persistente em: {instance_path}")
        # Aviso se o disco não existir (pode indicar problema de configuração no Render)
        if not os.path.exists(render_disk_path) or not os.access(render_disk_path, os.W_OK):
             logger.warning(f"Disco persistente não encontrado ou não gravável em {render_disk_path}. Verifique a configuração do serviço no Render.")
             # Fallback para diretório local (DADOS SERÃO PERDIDOS)
             instance_path = instance_path_default
             logger.warning(f"Usando diretório local para instance: {instance_path}. Dados serão perdidos entre deploys.")
        db_path = os.path.join(instance_path, db_name)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"Usando banco de dados em: {app.config['SQLALCHEMY_DATABASE_URI']}")
    else:
        # Ambiente local
        logger.info("Ambiente local detectado.")
        instance_path = instance_path_default
        db_path = os.path.join(instance_path, db_name)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"Usando banco de dados em: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Define explicitamente a pasta 'instance' para o Flask (redundante com instance_relative_config=True, mas seguro)
    app.instance_path = instance_path
    logger.info(f"Flask instance_path definido como: {app.instance_path}")


    # Garante que a pasta 'instance' exista
    try:
        logger.info(f"Verificando diretório instance: {instance_path}")
        os.makedirs(instance_path, exist_ok=True)
        # Tenta ajustar permissões (pode falhar dependendo do ambiente)
        if sys.platform != 'win32': # chmod não existe no Windows
            try:
                os.chmod(instance_path, 0o755) # Permissão padrão mais segura
                logger.info(f"Permissões do diretório instance ajustadas para 755")
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
    # CORREÇÃO: Inicializar CSRFProtect com a app
    csrf.init_app(app)

    # --- Contexto da Aplicação ---
    with app.app_context():
        # Importar todos os modelos ANTES de create_all()
        logger.info("Importando modelos...")
        try:
            from app.models.user import User
            from app.models.ponto import Ponto, Afastamento, Atividade
            from app.models.feriado import Feriado
            logger.info("Modelos importados com sucesso.")
        except ImportError as e:
            logger.error(f"Erro ao importar modelos: {e}", exc_info=True)
            raise

        # Cria as tabelas do banco de dados, se não existirem
        logger.info("Executando db.create_all()...")
        try:
            db.create_all()
            logger.info("db.create_all() executado (tabelas criadas se não existiam).")
        except Exception as e:
            logger.error(f"Erro durante a inicialização do banco de dados (create_all): {e}", exc_info=True)
            raise e

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
             raise

        # --- Context Processors ---
        # Disponibiliza 'datetime' para todos os templates
        @app.context_processor
        def inject_datetime():
            return {'datetime': datetime}

        # A inicialização do CSRFProtect geralmente já disponibiliza csrf_token()
        # Se ainda não funcionar, podemos injetá-lo explicitamente:
        # @app.context_processor
        # def inject_csrf():
        #     from flask_wtf.csrf import generate_csrf
        #     return {'csrf_token': generate_csrf}

        # --- Configuração de Logging Adicional (Opcional) ---
        if not app.debug and not app.testing:
            log_dir = os.path.join(app.instance_path, 'logs') # Salva logs na pasta instance
            if not os.path.exists(log_dir):
                try: # Adiciona try-except para criação de pasta de log
                    os.makedirs(log_dir, exist_ok=True)
                except OSError as e:
                     logger.error(f"Não foi possível criar diretório de log {log_dir}: {e}")
                     log_dir = None # Impede tentativa de criar handler se pasta falhou

            if log_dir: # Só configura handler se a pasta existir/foi criada
                log_file = os.path.join(log_dir, 'ponto_eletronico.log')
                try:
                    file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
                    file_handler.setFormatter(logging.Formatter(
                        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
                    file_handler.setLevel(logging.INFO)
                    # Remove handlers padrão se existirem para evitar duplicação
                    for handler in app.logger.handlers[:]:
                        app.logger.removeHandler(handler)
                    app.logger.addHandler(file_handler)
                    app.logger.setLevel(logging.INFO)
                    app.logger.info('Aplicação Ponto Eletrônico iniciada (Logging para arquivo configurado)')
                except Exception as e:
                     app.logger.error(f"Falha ao configurar logging para arquivo em {log_file}: {e}")
            else:
                app.logger.warning("Logging para arquivo desabilitado devido a erro na criação do diretório de logs.")

        else:
             app.logger.info('Aplicação Ponto Eletrônico iniciada (Modo Debug/Testing)')


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
