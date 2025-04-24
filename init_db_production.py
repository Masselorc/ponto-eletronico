#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inicialização do Banco de Dados para Ambiente de Produção
==================================================================

VERSÃO: 2.0.0 (Abril 2025)
AUTOR: Equipe de Desenvolvimento
REVISÃO: Correção de erros críticos para deploy no Render

Este script é responsável por inicializar o banco de dados em ambiente de produção.
Ele cria as tabelas necessárias, usuários padrão e dados iniciais como feriados.

IMPORTANTE: Este arquivo foi corrigido para resolver o erro de propriedade 'is_active'
que estava impedindo a inicialização do banco de dados no ambiente Render.
"""

import os
import sys
import traceback
from datetime import datetime, date

# Importações da aplicação
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado  # Importação corrigida do modelo Feriado

# Configurações e constantes
ADMIN_DEFAULT_NAME = 'Administrador'
ADMIN_DEFAULT_EMAIL = 'admin@example.com'
ADMIN_DEFAULT_MATRICULA = 'ADMIN001'
ADMIN_DEFAULT_PASSWORD = 'admin123'
ADMIN_DEFAULT_CARGO = 'Administrador'
ADMIN_DEFAULT_UF = 'DF'
ADMIN_DEFAULT_TELEFONE = '(61) 99999-9999'
ADMIN_DEFAULT_VINCULO = 'SENAPPEN - Administração'
ADMIN_DEFAULT_FOTO = 'default.png'

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


def init_production_db():
    """
    Inicializa o banco de dados em ambiente de produção.
    
    Esta função realiza as seguintes operações:
    1. Cria todas as tabelas definidas nos modelos
    2. Verifica se já existe um usuário administrador
    3. Se não existir, cria um usuário administrador padrão
    4. Cria um usuário de demonstração
    5. Adiciona feriados nacionais para o ano atual
    
    Retorna:
        bool: True se a inicialização foi bem-sucedida, False caso contrário
    
    Raises:
        Exception: Qualquer erro durante o processo de inicialização
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
        print("[1/5] Criando aplicação Flask...")
        app = create_app()
        
        with app.app_context():
            try:
                # Cria todas as tabelas definidas nos modelos
                print("[2/5] Criando tabelas no banco de dados...")
                db.create_all()
                
                # Verifica se já existe um usuário administrador
                print("[3/5] Verificando se já existe um usuário administrador...")
                admin = User.query.filter_by(is_admin=True).first()
                
                if not admin:
                    print("[4/5] Criando usuário administrador e dados iniciais...")
                    
                    # CORREÇÃO IMPORTANTE: Não definir a propriedade 'is_active'
                    # A propriedade 'is_active' é herdada de UserMixin (flask_login)
                    # e não possui um setter, portanto não deve ser definida diretamente.
                    
                    # Cria um usuário administrador padrão usando variáveis de ambiente
                    admin = User(
                        name=os.getenv('ADMIN_NAME', ADMIN_DEFAULT_NAME),
                        email=os.getenv('ADMIN_EMAIL', ADMIN_DEFAULT_EMAIL),
                        matricula=os.getenv('ADMIN_MATRICULA', ADMIN_DEFAULT_MATRICULA),
                        cargo=os.getenv('ADMIN_CARGO', ADMIN_DEFAULT_CARGO),
                        uf=os.getenv('ADMIN_UF', ADMIN_DEFAULT_UF),
                        telefone=os.getenv('ADMIN_TELEFONE', ADMIN_DEFAULT_TELEFONE),
                        vinculo=os.getenv('ADMIN_VINCULO', ADMIN_DEFAULT_VINCULO),
                        foto_path=os.getenv('ADMIN_FOTO_PATH', ADMIN_DEFAULT_FOTO),
                        is_admin=True
                        # NÃO definir is_active aqui - é uma propriedade somente leitura
                    )
                    
                    print("  - Definindo senha do administrador...")
                    admin.set_password(os.getenv('ADMIN_PASSWORD', ADMIN_DEFAULT_PASSWORD))
                    db.session.add(admin)
                    
                    print("  - Criando usuário de demonstração...")
                    # Cria um usuário comum para demonstração
                    user = User(
                        name='Usuário Demonstração',
                        email='demo@example.com',
                        matricula='DEMO001',
                        cargo='Analista',
                        uf='DF',
                        telefone='(61) 88888-8888',
                        vinculo='SENAPPEN - Demonstração',
                        foto_path='default.png',
                        is_admin=False
                        # NÃO definir is_active aqui - é uma propriedade somente leitura
                    )
                    user.set_password('demo123')
                    db.session.add(user)
                    
                    print("  - Adicionando feriados nacionais para 2025...")
                    # Adiciona feriados nacionais para 2025
                    for feriado_data in FERIADOS_2025:
                        feriado = Feriado(
                            data=feriado_data['data'],
                            descricao=feriado_data['descricao']
                        )
                        db.session.add(feriado)
                    
                    print("  - Realizando commit das alterações...")
                    db.session.commit()
                    print("[5/5] Banco de dados de produção inicializado com sucesso!")
                else:
                    print("[5/5] Banco de dados já inicializado anteriormente.")
                
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
            sys.exit(1)
    except Exception as e:
        # Em caso de erro fatal, registra e sai com código de erro
        print(f"\nERRO FATAL DURANTE A EXECUÇÃO: {e}")
        print(traceback.format_exc())
        # Saída com código de erro para indicar falha
        sys.exit(1)
