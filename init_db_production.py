#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inicialização do Banco de Dados para Ambiente de Produção
==================================================================

VERSÃO: 2.1.0 (Abril 2025)
AUTOR: Equipe de Desenvolvimento
REVISÃO: Correção de erro 'no such column: users.is_active_db' durante build

Este script é responsável por inicializar o banco de dados em ambiente de produção.
Ele cria as tabelas necessárias, usuários padrão e dados iniciais como feriados.
Adiciona verificação e criação da coluna 'is_active_db' na tabela 'users'.
"""

import os
import sys
import traceback
from datetime import datetime, date

# Importações da aplicação
# É importante que create_app() seja chamado antes de importar modelos se eles dependem de 'db'
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado

# Configurações e constantes
ADMIN_DEFAULT_NAME = 'Administrador'
ADMIN_DEFAULT_EMAIL = 'admin@example.com'
ADMIN_DEFAULT_MATRICULA = 'ADMIN001'
ADMIN_DEFAULT_PASSWORD = 'admin123'
ADMIN_DEFAULT_CARGO = 'Administrador'
ADMIN_DEFAULT_UF = 'DF'
ADMIN_DEFAULT_TELEFONE = '(61) 99999-9999'
ADMIN_DEFAULT_VINCULO = 'SENAPPEN - Administração'
ADMIN_DEFAULT_FOTO = 'default.png' # Considerar um caminho relativo ou URL

# Lista de feriados nacionais para 2025
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

def ensure_is_active_db_column(app):
    """Verifica e adiciona a coluna is_active_db à tabela users se não existir."""
    with app.app_context():
        try:
            print("  - Verificando coluna 'is_active_db' na tabela 'users'...")
            with db.engine.connect() as connection:
                # Verificar se a tabela users existe primeiro
                result_table = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                if not result_table.fetchone():
                    print("  - Tabela 'users' não encontrada. Será criada por db.create_all().")
                    return # Deixa o create_all lidar com a criação da tabela

                # Verificar colunas da tabela users
                result_columns = connection.execute(db.text("PRAGMA table_info(users)"))
                columns = [column[1] for column in result_columns.fetchall()]

                if 'is_active_db' not in columns:
                    print("  - Coluna 'is_active_db' não encontrada. Adicionando...")
                    # Usar transação para adicionar a coluna
                    with connection.begin():
                        # Adiciona a coluna com NOT NULL e DEFAULT 1 (True)
                        connection.execute(db.text("ALTER TABLE users ADD COLUMN is_active_db BOOLEAN NOT NULL DEFAULT 1"))
                    print("  - Coluna 'is_active_db' adicionada com sucesso!")
                else:
                    print("  - Coluna 'is_active_db' já existe.")
        except Exception as e:
            print(f"  - ERRO ao verificar/adicionar coluna 'is_active_db': {e}")
            print(traceback.format_exc())
            # Decide se quer relançar o erro ou apenas logar
            # raise # Descomente para parar a execução em caso de erro aqui


def init_production_db():
    """
    Inicializa o banco de dados em ambiente de produção.
    """
    try:
        # Imprime cabeçalho e informações de diagnóstico
        print("\n" + "="*80)
        print("INICIALIZAÇÃO DO BANCO DE DADOS DE PRODUÇÃO")
        print("="*80)
        print(f"Data e hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"Python version: {sys.version}")
        print(f"Diretório atual: {os.getcwd()}")
        print("-"*80 + "\n")

        # Cria a aplicação com configurações de produção
        print("[1/6] Criando aplicação Flask...")
        app = create_app() # create_app já configura logging, db, etc.

        with app.app_context():
            try:
                # Cria todas as tabelas definidas nos modelos, se não existirem
                print("[2/6] Garantindo que todas as tabelas existam (db.create_all)...")
                db.create_all()

                # --- CORREÇÃO: Garantir que a coluna is_active_db exista ANTES de consultá-la ---
                print("[3/6] Verificando/Adicionando colunas de migração necessárias...")
                ensure_is_active_db_column(app)
                # Poderia chamar a função migrate_db de app/__init__.py aqui também,
                # mas adicionar a verificação específica para is_active_db é mais direto para este erro.
                # migrate_db(app) # Se quiser executar toda a migração aqui
                # ---------------------------------------------------------------------------------

                # Verifica se já existe um usuário administrador
                print("[4/6] Verificando se já existe um usuário administrador...")
                # Esta consulta agora deve funcionar pois a coluna is_active_db foi verificada/adicionada
                admin = User.query.filter_by(is_admin=True).first()

                if not admin:
                    print("[5/6] Criando usuário administrador e dados iniciais...")

                    # Cria um usuário administrador padrão usando variáveis de ambiente ou defaults
                    admin = User(
                        name=os.getenv('ADMIN_NAME', ADMIN_DEFAULT_NAME),
                        email=os.getenv('ADMIN_EMAIL', ADMIN_DEFAULT_EMAIL),
                        matricula=os.getenv('ADMIN_MATRICULA', ADMIN_DEFAULT_MATRICULA),
                        cargo=os.getenv('ADMIN_CARGO', ADMIN_DEFAULT_CARGO),
                        uf=os.getenv('ADMIN_UF', ADMIN_DEFAULT_UF),
                        telefone=os.getenv('ADMIN_TELEFONE', ADMIN_DEFAULT_TELEFONE),
                        vinculo=os.getenv('ADMIN_VINCULO', ADMIN_DEFAULT_VINCULO),
                        foto_path=os.getenv('ADMIN_FOTO_PATH', ADMIN_DEFAULT_FOTO),
                        is_admin=True,
                        is_active_db=True # Define como ativo por padrão
                    )

                    print("  - Definindo senha do administrador...")
                    admin.set_password(os.getenv('ADMIN_PASSWORD', ADMIN_DEFAULT_PASSWORD))
                    db.session.add(admin)

                    print("  - Criando usuário de demonstração...")
                    # Cria um usuário comum para demonstração
                    user_demo_exists = User.query.filter_by(email='demo@example.com').first()
                    if not user_demo_exists:
                        user = User(
                            name='Usuário Demonstração',
                            email='demo@example.com',
                            matricula='DEMO001',
                            cargo='Analista',
                            uf='DF',
                            telefone='(61) 88888-8888',
                            vinculo='SENAPPEN - Demonstração',
                            foto_path='default.png', # Usar um placeholder ou caminho relativo
                            is_admin=False,
                            is_active_db=True
                        )
                        user.set_password('demo123')
                        db.session.add(user)
                    else:
                        print("  - Usuário de demonstração já existe.")


                    print("  - Adicionando feriados nacionais para 2025 (se não existirem)...")
                    # Adiciona feriados nacionais para 2025, verificando se já existem
                    for feriado_data in FERIADOS_2025:
                        feriado_exists = Feriado.query.filter_by(data=feriado_data['data']).first()
                        if not feriado_exists:
                            feriado = Feriado(
                                data=feriado_data['data'],
                                descricao=feriado_data['descricao']
                            )
                            db.session.add(feriado)
                            print(f"    - Adicionado: {feriado_data['data'].strftime('%d/%m')} - {feriado_data['descricao']}")
                        # else:
                        #     print(f"    - Já existe: {feriado_data['data'].strftime('%d/%m')} - {feriado_data['descricao']}")


                    print("  - Realizando commit das alterações...")
                    db.session.commit()
                    print("[6/6] Banco de dados de produção inicializado com sucesso!")
                else:
                    print("[5/6] Usuário administrador já existe.")
                    print("[6/6] Banco de dados já inicializado anteriormente.")

                print("\n" + "-"*80)
                print("INICIALIZAÇÃO CONCLUÍDA COM SUCESSO")
                print("-"*80 + "\n")
                return True

            except Exception as e:
                # Em caso de erro, faz rollback e registra detalhes
                db.session.rollback()
                print("\n" + "!"*80)
                print(f"ERRO AO INICIALIZAR O BANCO DE DADOS: {e}")
                print("!"*80)
                print("\nDetalhes do erro:")
                print(traceback.format_exc())
                # Re-lança a exceção para que o erro seja capturado e registrado corretamente
                raise
    except Exception as e:
        # Captura erros na criação da aplicação ou outros erros não capturados
        print("\n" + "!"*80)
        print(f"ERRO CRÍTICO DURANTE A INICIALIZAÇÃO DO BANCO DE DADOS: {e}")
        print("!"*80)
        print("\nDetalhes do erro:")
        print(traceback.format_exc())
        # Re-lança a exceção para que o script termine com erro
        raise


# Executa a função apenas se este arquivo for executado diretamente
if __name__ == '__main__':
    try:
        # Tenta inicializar o banco de dados
        success = init_production_db()

        # Sai com código de sucesso se tudo correu bem
        if success:
            sys.exit(0)
        else:
            # Se init_production_db retornar False (não deve acontecer com a lógica atual)
            sys.exit(1)
    except Exception as e:
        # Em caso de erro fatal não capturado dentro da função
        print(f"\nERRO FATAL DURANTE A EXECUÇÃO DO SCRIPT: {e}")
        print(traceback.format_exc())
        # Saída com código de erro para indicar falha no build
        sys.exit(1)

