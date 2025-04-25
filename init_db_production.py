# -*- coding: utf-8 -*-
"""
Script de Inicialização do Banco de Dados para Produção (Render).

Este script é projetado para ser executado durante o processo de build
no ambiente Render. Ele garante que:
1. A aplicação Flask seja criada.
2. O banco de dados e suas tabelas sejam criados (usando db.create_all()).
3. Verifica a existência das tabelas e colunas esperadas (opcionalmente adiciona colunas ausentes).
4. Cria um usuário administrador padrão se não existir.
5. Adiciona dados iniciais essenciais (ex: feriados).

Uso:
    python init_db_production.py

Variáveis de Ambiente (Opcional):
    - ADMIN_USERNAME: Username para o administrador padrão.
    - ADMIN_NAME: Nome completo para o administrador padrão.
    - ADMIN_EMAIL: Email para o administrador padrão.
    - ADMIN_PASSWORD: Senha para o administrador padrão.
    - ADMIN_CARGO: Cargo para o administrador padrão.
    # Outras variáveis como MATRICULA, UF, etc., foram removidas pois não
    # correspondem aos campos atuais do modelo User. Adicione-os ao modelo
    # User se forem necessários.
"""

import os
import sys
import logging
# CORREÇÃO: Importar date e datetime do módulo datetime
from datetime import date, datetime
from sqlalchemy import inspect, text

# Adiciona o diretório raiz do projeto ao sys.path para permitir importações de 'app'
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Tenta importar componentes da aplicação
try:
    from app import create_app, db
    from app.models.user import User
    from app.models.feriado import Feriado
    from app.models.ponto import Ponto, Afastamento, Atividade # Importar todos os modelos
except ImportError as e:
    print(f"ERRO FATAL: Falha ao importar componentes da aplicação: {e}")
    print("Verifique se o script está no diretório raiz ou se o PYTHONPATH está configurado.")
    sys.exit(1)
except Exception as e: # Captura outros erros de inicialização (ex: DB não conecta)
    print(f"ERRO FATAL durante importação inicial: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Constantes Padrão para o Admin ---
ADMIN_DEFAULT_USERNAME = 'admin'
ADMIN_DEFAULT_NAME = 'Administrador Padrão'
ADMIN_DEFAULT_EMAIL = 'admin@example.com'
ADMIN_DEFAULT_PASSWORD = 'change_this_password' # SENHA FRACA - MUDE EM PRODUÇÃO!
ADMIN_DEFAULT_CARGO = 'Admin'
# Removidos defaults para campos inexistentes no modelo User atual
# ADMIN_DEFAULT_MATRICULA = '000000'
# ADMIN_DEFAULT_UF = 'DF'
# ADMIN_DEFAULT_TELEFONE = '(61) 99999-9999'
# ADMIN_DEFAULT_VINCULO = 'Estatutário'
# ADMIN_DEFAULT_FOTO = 'default.jpg'

# --- Função Principal de Inicialização ---
def init_production_db():
    """Executa os passos de inicialização do banco de dados para produção."""
    logger.info("================================================================================")
    logger.info("INICIALIZAÇÃO DO BANCO DE DADOS DE PRODUÇÃO")
    logger.info("================================================================================")
    # CORREÇÃO: datetime agora está importado e pode ser usado
    logger.info(f"Data e hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Diretório atual: {os.getcwd()}")
    logger.info("--------------------------------------------------------------------------------")

    app = None # Inicializa app como None
    try:
        # [1/6] Criar Aplicação Flask
        logger.info("[1/6] Criando aplicação Flask...")
        app = create_app()
        if not app:
            logger.error("Falha ao criar a aplicação Flask. Verifique app/__init__.py.")
            return False
        logger.info("Aplicação Flask criada com sucesso.")

        # Usar o contexto da aplicação para operações de banco de dados
        with app.app_context():
            logger.info("[2/6] Verificando/Criando Tabelas do Banco de Dados...")
            try:
                # db.create_all() já é chamado dentro de create_app,
                # mas podemos verificar tabelas específicas aqui se necessário.
                inspector = inspect(db.engine)
                tabelas_existentes = inspector.get_table_names()
                modelos_esperados = [User, Ponto, Feriado, Afastamento, Atividade]
                tabelas_esperadas = [m.__tablename__ for m in modelos_esperados if hasattr(m, '__tablename__')]

                tabelas_criadas_ou_verificadas = True
                for nome_tabela in tabelas_esperadas:
                    if nome_tabela not in tabelas_existentes:
                        logger.warning(f"  - Tabela '{nome_tabela}' não encontrada após create_app. Verifique a inicialização em app/__init__.py.")
                        # Se create_all() em __init__ falhou silenciosamente, a app pode não funcionar.
                        tabelas_criadas_ou_verificadas = False # Marcar como potencialmente problemático
                    else:
                        logger.info(f"  - Tabela '{nome_tabela}' encontrada.")

                if not tabelas_criadas_ou_verificadas:
                     logger.warning("Algumas tabelas esperadas não foram encontradas. A aplicação pode não funcionar corretamente.")
                     # Considerar retornar False ou tentar criar de novo:
                     # logger.info("Tentando db.create_all() novamente...")
                     # db.create_all()

                logger.info("[3/6] Verificação/Criação de Tabelas concluída.")

            except Exception as e:
                logger.error(f"Erro ao verificar/criar tabelas: {e}", exc_info=True)
                return False # Não continuar se houver erro no DB

            # [4/6] Verificar Usuário Admin
            logger.info("[4/6] Verificando se já existe um usuário administrador...")
            admin_user = User.query.filter_by(is_admin=True).first()

            if admin_user:
                logger.info(f"Usuário administrador '{admin_user.username}' já existe.")
            else:
                logger.info("Nenhum usuário administrador encontrado. Criando usuário padrão...")
                logger.info("[5/6] Criando usuário administrador e dados iniciais...")
                try:
                    # Obter dados do admin das variáveis de ambiente ou usar padrões
                    admin_username = os.getenv('ADMIN_USERNAME', ADMIN_DEFAULT_USERNAME)
                    admin_name = os.getenv('ADMIN_NAME', ADMIN_DEFAULT_NAME)
                    admin_email = os.getenv('ADMIN_EMAIL', ADMIN_DEFAULT_EMAIL)
                    admin_password = os.getenv('ADMIN_PASSWORD', ADMIN_DEFAULT_PASSWORD)
                    admin_cargo = os.getenv('ADMIN_CARGO', ADMIN_DEFAULT_CARGO)

                    # Cria o objeto User
                    admin = User(
                        username=admin_username,
                        email=admin_email,
                        nome_completo=admin_name,
                        cargo=admin_cargo,
                        is_admin=True,
                        ativo=True
                    )
                    admin.set_password(admin_password)
                    db.session.add(admin)
                    logger.info(f"Usuário administrador '{admin_username}' criado com sucesso.")
                    logger.warning(f"Senha padrão '{admin_password}' definida para o admin. MUDE ESTA SENHA IMEDIATAMENTE!")

                    # Adicionar Feriado de Exemplo (se necessário)
                    feriado_exemplo_data = date(date.today().year, 1, 1) # Ano Novo
                    feriado_existente = Feriado.query.filter_by(data=feriado_exemplo_data).first()
                    if not feriado_existente:
                        feriado_padrao = Feriado(data=feriado_exemplo_data, descricao='Confraternização Universal')
                        db.session.add(feriado_padrao)
                        logger.info("Feriado padrão 'Confraternização Universal' adicionado.")

                    db.session.commit()
                    logger.info("Dados iniciais adicionados e commit realizado.")

                except Exception as e:
                    db.session.rollback()
                    logger.error(f"ERRO AO CRIAR ADMIN/DADOS INICIAIS: {e}", exc_info=True)
                    print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print(f"ERRO AO CRIAR ADMIN/DADOS INICIAIS: {e}")
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                    return False # Falha na inicialização

            logger.info("[6/6] Inicialização do banco de dados concluída com sucesso.")
            logger.info("================================================================================")
            return True # Sucesso

    except Exception as e:
        # Captura erros que podem ocorrer antes ou fora do app_context
        logger.error(f"ERRO CRÍTICO DURANTE A INICIALIZAÇÃO: {e}", exc_info=True)
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"ERRO CRÍTICO DURANTE A INICIALIZAÇÃO: {e}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        print("Detalhes do erro:")
        import traceback
        traceback.print_exc()
        print("\n")
        # Garante que app_context seja fechado se app foi criado
        # (Normalmente o 'with' cuidaria disso, mas em caso de exceção fora dele)
        # if app and app.app_context():
        #     app.app_context().pop() # Não é a forma padrão, mas para garantir
        return False # Indica falha

# --- Execução do Script ---
if __name__ == '__main__':
    if init_production_db():
        print("\nScript de inicialização do banco de dados de produção concluído com SUCESSO.\n")
        sys.exit(0) # Saída com sucesso
    else:
        print("\nScript de inicialização do banco de dados de produção FALHOU.\n")
        sys.exit(1) # Saída com erro
