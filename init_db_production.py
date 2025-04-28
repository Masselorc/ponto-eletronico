#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inicialização do Banco de Dados para Ambiente de Produção
"""
import os
import sys
import traceback
from datetime import datetime, date
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
import calendar
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes para dados padrão
ADMIN_DEFAULT_NAME = 'Administrador'
ADMIN_DEFAULT_EMAIL = 'admin@example.com'
ADMIN_DEFAULT_MATRICULA = 'ADMIN001'
ADMIN_DEFAULT_PASSWORD = 'admin123'
ADMIN_DEFAULT_CARGO = 'Administrador'
ADMIN_DEFAULT_UF = 'DF'
ADMIN_DEFAULT_TELEFONE = '(61) 99999-9999'
ADMIN_DEFAULT_VINCULO = 'SENAPPEN - Administração'
ADMIN_DEFAULT_FOTO = 'default.png'
# --- NOVOS PADRÕES (se necessário, mas como são obrigatórios, não terão padrão real) ---
ADMIN_DEFAULT_UNIDADE_SETOR = 'GAB/DIRPP' # Exemplo
ADMIN_DEFAULT_CHEFIA = 'Nome Chefe Exemplo' # Exemplo
# ------------------------------------------------------------------------------------
FERIADOS_2025 = [
    {'data': date(2025, 1, 1), 'descricao': 'Confraternização Universal'},
    {'data': date(2025, 2, 17), 'descricao': 'Carnaval'},
    {'data': date(2025, 2, 18), 'descricao': 'Carnaval'},
    {'data': date(2025, 4, 18), 'descricao': 'Sexta-feira Santa'},
    {'data': date(2025, 4, 21), 'descricao': 'Tiradentes'},
    {'data': date(2025, 5, 1), 'descricao': 'Dia do Trabalho'},
    {'data': date(2025, 6, 19), 'descricao': 'Corpus Christi'},
    {'data': date(2025, 9, 7), 'descricao': 'Independência do Brasil'},
    {'data': date(2025, 10, 12), 'descricao': 'Nossa Senhora Aparecida'},
    {'data': date(2025, 11, 2), 'descricao': 'Finados'},
    {'data': date(2025, 11, 15), 'descricao': 'Proclamação da República'},
    {'data': date(2025, 12, 25), 'descricao': 'Natal'}
]

def ensure_column_exists(app, table_name, column_name, column_definition):
    """Função genérica para verificar e adicionar uma coluna a uma tabela."""
    with app.app_context():
        try:
            logger.info(f"  - Verificando coluna '{column_name}' na tabela '{table_name}'...")
            with db.engine.connect() as connection:
                result_table = connection.execute(db.text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
                if not result_table.fetchone():
                    logger.info(f"  - Tabela '{table_name}' não encontrada. Será criada por db.create_all().")
                    return

                result_columns = connection.execute(db.text(f"PRAGMA table_info({table_name})"))
                columns = [column[1] for column in result_columns.fetchall()]

                if column_name not in columns:
                    logger.info(f"  - Coluna '{column_name}' não encontrada. Adicionando...")
                    try:
                        # Usar TEXT para strings em SQLite via ALTER TABLE
                        # Adicionar DEFAULT '' para contornar limitação do SQLite com NOT NULL em ALTER TABLE
                        sql_command = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                        logger.info(f"  - Executando SQL: {sql_command}")
                        connection.execute(db.text(sql_command))
                        # Commit pode ser necessário dependendo do modo de transação do SQLAlchemy/DBAPI
                        connection.commit()
                        logger.info(f"  - Coluna '{column_name}' adicionada com sucesso!")
                    except Exception as alter_err:
                        logger.error(f"  - ERRO ao executar ALTER TABLE para '{column_name}': {alter_err}", exc_info=True)
                        # connection.rollback() # Rollback se o commit falhar ou se necessário
                        raise
                else:
                    logger.info(f"  - Coluna '{column_name}' já existe.")
        except Exception as e:
            logger.error(f"  - ERRO ao verificar/adicionar coluna '{column_name}' na tabela '{table_name}': {e}", exc_info=True)
            raise

def init_production_db():
    """Inicializa o banco de dados em ambiente de produção."""
    try:
        print("\n" + "="*80); print("INICIALIZAÇÃO DO BANCO DE DADOS DE PRODUÇÃO"); print("="*80)
        print(f"Data e hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"); print(f"Python version: {sys.version}"); print(f"Diretório atual: {os.getcwd()}"); print("-"*80 + "\n")
        print("[1/6] Criando aplicação Flask...")
        logger.info("[1/6] Criando aplicação Flask...")
        app = create_app()
        with app.app_context():
            try:
                print("[2/6] Garantindo que todas as tabelas existam (db.create_all)...")
                logger.info("[2/6] Garantindo que todas as tabelas existam (db.create_all)...")
                db.create_all()
                print("[2/6] db.create_all() concluído.")
                logger.info("[2/6] db.create_all() concluído.")

                print("[3/6] Verificando/Adicionando colunas de migração necessárias...")
                logger.info("[3/6] Verificando/Adicionando colunas de migração necessárias...")
                # Definições para SQLite com NOT NULL e DEFAULT
                ensure_column_exists(app, 'users', 'is_active_db', 'BOOLEAN NOT NULL DEFAULT 1')
                ensure_column_exists(app, 'pontos', 'afastamento', 'BOOLEAN DEFAULT 0')
                ensure_column_exists(app, 'pontos', 'tipo_afastamento', 'VARCHAR(100)')
                ensure_column_exists(app, 'pontos', 'observacoes', 'TEXT')
                ensure_column_exists(app, 'pontos', 'resultados_produtos', 'TEXT')
                ensure_column_exists(app, 'atividades', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
                # --- ADICIONANDO NOVAS COLUNAS ---
                ensure_column_exists(app, 'users', 'unidade_setor', "TEXT NOT NULL DEFAULT ''")
                ensure_column_exists(app, 'users', 'chefia_imediata', "TEXT NOT NULL DEFAULT ''")
                # ---------------------------------
                print("[3/6] Verificação/Adição de colunas concluída.")
                logger.info("[3/6] Verificação/Adição de colunas concluída.")

                print("[4/6] Verificando se já existe um usuário administrador...")
                logger.info("[4/6] Verificando se já existe um usuário administrador...")
                admin = User.query.filter_by(is_admin=True).first()
                if not admin:
                    print("[5/6] Criando usuário administrador e dados iniciais...")
                    logger.info("[5/6] Criando usuário administrador e dados iniciais...")
                    admin = User(
                        name=os.getenv('ADMIN_NAME', ADMIN_DEFAULT_NAME),
                        email=os.getenv('ADMIN_EMAIL', ADMIN_DEFAULT_EMAIL),
                        matricula=os.getenv('ADMIN_MATRICULA', ADMIN_DEFAULT_MATRICULA),
                        cargo=os.getenv('ADMIN_CARGO', ADMIN_DEFAULT_CARGO),
                        uf=os.getenv('ADMIN_UF', ADMIN_DEFAULT_UF),
                        telefone=os.getenv('ADMIN_TELEFONE', ADMIN_DEFAULT_TELEFONE),
                        vinculo=os.getenv('ADMIN_VINCULO', ADMIN_DEFAULT_VINCULO),
                        foto_path=os.getenv('ADMIN_FOTO_PATH', ADMIN_DEFAULT_FOTO),
                        # --- DADOS PARA NOVOS CAMPOS DO ADMIN ---
                        unidade_setor=os.getenv('ADMIN_UNIDADE_SETOR', ADMIN_DEFAULT_UNIDADE_SETOR),
                        chefia_imediata=os.getenv('ADMIN_CHEFIA', ADMIN_DEFAULT_CHEFIA),
                        # --------------------------------------
                        is_admin=True, is_active_db=True
                    )
                    print("  - Definindo senha do administrador...")
                    logger.info("  - Definindo senha do administrador...")
                    admin.set_password(os.getenv('ADMIN_PASSWORD', ADMIN_DEFAULT_PASSWORD))
                    db.session.add(admin)

                    print("  - Criando usuário de demonstração...")
                    logger.info("  - Criando usuário de demonstração...")
                    user_demo_exists = User.query.filter_by(email='demo@example.com').first()
                    if not user_demo_exists:
                        user = User(
                            name='Usuário Demonstração', email='demo@example.com', matricula='DEMO001',
                            cargo='Analista', uf='DF', telefone='(61) 88888-8888',
                            vinculo='SENAPPEN - Demonstração', foto_path='default.png',
                            # --- DADOS PARA NOVOS CAMPOS DO DEMO ---
                            unidade_setor='Setor Demo', chefia_imediata='Chefe Demo',
                            # -------------------------------------
                            is_admin=False, is_active_db=True
                        )
                        user.set_password('demo123')
                        db.session.add(user)
                        print("  - Usuário de demonstração criado.")
                        logger.info("  - Usuário de demonstração criado.")
                    else:
                        print("  - Usuário de demonstração já existe.")
                        logger.info("  - Usuário de demonstração já existe.")

                    print("  - Adicionando feriados nacionais para 2025 (se não existirem)...")
                    logger.info("  - Adicionando feriados nacionais para 2025 (se não existirem)...")
                    feriados_adicionados = 0
                    for feriado_data in FERIADOS_2025:
                        feriado_exists = Feriado.query.filter_by(data=feriado_data['data']).first()
                        if not feriado_exists:
                            feriado = Feriado(data=feriado_data['data'], descricao=feriado_data['descricao'])
                            db.session.add(feriado)
                            feriados_adicionados += 1
                    print(f"  - {feriados_adicionados} feriados adicionados.")
                    logger.info(f"  - {feriados_adicionados} feriados adicionados.")

                    print("  - Realizando commit das alterações...")
                    logger.info("  - Realizando commit das alterações...")
                    db.session.commit()
                    print("[6/6] Banco de dados de produção inicializado com sucesso!")
                    logger.info("[6/6] Banco de dados de produção inicializado com sucesso!")
                else:
                    print("[5/6] Usuário administrador já existe.")
                    logger.info("[5/6] Usuário administrador já existe.")
                    print("  - Verificando/Adicionando feriados nacionais para 2025 (se não existirem)...")
                    logger.info("  - Verificando/Adicionando feriados nacionais para 2025 (se não existirem)...")
                    feriados_adicionados = 0
                    for feriado_data in FERIADOS_2025:
                        feriado_exists = Feriado.query.filter_by(data=feriado_data['data']).first()
                        if not feriado_exists:
                            feriado = Feriado(data=feriado_data['data'], descricao=feriado_data['descricao'])
                            db.session.add(feriado)
                            feriados_adicionados += 1
                    if feriados_adicionados > 0:
                        db.session.commit()
                        print(f"  - {feriados_adicionados} feriados adicionados.")
                        logger.info(f"  - {feriados_adicionados} feriados adicionados.")
                    else:
                        print("  - Todos os feriados de 2025 já existem.")
                        logger.info("  - Todos os feriados de 2025 já existem.")
                    print("[6/6] Banco de dados já inicializado anteriormente.")
                    logger.info("[6/6] Banco de dados já inicializado anteriormente.")

                print("\n" + "-"*80); print("INICIALIZAÇÃO CONCLUÍDA COM SUCESSO"); print("-"*80 + "\n")
                logger.info("INICIALIZAÇÃO CONCLUÍDA COM SUCESSO")
                return True
            except Exception as e:
                db.session.rollback()
                print("\n" + "!"*80); print(f"ERRO AO INICIALIZAR O BANCO DE DADOS: {e}"); print("!"*80)
                print("\nDetalhes do erro:"); print(traceback.format_exc())
                logger.error(f"ERRO AO INICIALIZAR O BANCO DE DADOS: {e}", exc_info=True)
                raise
    except Exception as e:
        print("\n" + "!"*80); print(f"ERRO CRÍTICO DURANTE A INICIALIZAÇÃO DO BANCO DE DADOS: {e}"); print("!"*80)
        print("\nDetalhes do erro:"); print(traceback.format_exc())
        logger.critical(f"ERRO CRÍTICO DURANTE A INICIALIZAÇÃO DO BANCO DE DADOS: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        success = init_production_db()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERRO FATAL DURANTE A EXECUÇÃO DO SCRIPT: {e}")
        logger.critical(f"ERRO FATAL DURANTE A EXECUÇÃO DO SCRIPT: {e}", exc_info=True)
        sys.exit(1)
