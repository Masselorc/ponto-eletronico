"""
ARQUIVO MODIFICADO - Abril 2025
Correção de importações e inicialização do banco de dados
Este arquivo foi corrigido para resolver problemas de importação e inicialização
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
from flask import Flask
from app import create_app, db
from app.models.user import User
from app.models.feriado import Feriado  # MODIFICAÇÃO: Importação corrigida do modelo Feriado

# MODIFICAÇÃO: Adicionado tratamento de exceções e logging detalhado
try:
    print("Iniciando script de inicialização do banco de dados para produção...")
    
    # Configuração do ambiente
    os.environ['FLASK_ENV'] = 'production'
    
    # Criação da aplicação
    print("Criando aplicação Flask...")
    app = create_app()
    
    # Contexto da aplicação
    print("Entrando no contexto da aplicação...")
    with app.app_context():
        print("Verificando se o banco de dados existe...")
        
        # Cria todas as tabelas se não existirem
        print("Criando tabelas do banco de dados...")
        db.create_all()
        
        # Verifica se já existe um usuário administrador
        print("Verificando se existe usuário administrador...")
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if not admin:
            print("Criando usuário administrador padrão...")
            admin = User(
                name='Administrador',
                email='admin@example.com',
                matricula='000000',
                cargo='Administrador',  # MODIFICAÇÃO: Campo adicionado
                uf='DF',               # MODIFICAÇÃO: Campo adicionado
                telefone='(00) 00000-0000',  # MODIFICAÇÃO: Campo adicionado
                foto_path='default.png',     # MODIFICAÇÃO: Campo adicionado
                vinculo='Servidor',
                is_admin=True,
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # MODIFICAÇÃO: Adicionado tratamento de exceções para a criação do usuário
            try:
                db.session.commit()
                print("Usuário administrador criado com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao criar usuário administrador: {str(e)}")
                print(traceback.format_exc())
                sys.exit(1)
        else:
            print("Usuário administrador já existe.")
        
        # Verifica se já existem feriados cadastrados
        print("Verificando se existem feriados cadastrados...")
        feriados_count = Feriado.query.count()
        
        if feriados_count == 0:
            print("Cadastrando feriados nacionais para 2024...")
            
            # Lista de feriados nacionais para 2024
            feriados_2024 = [
                {'data': datetime(2024, 1, 1), 'descricao': 'Confraternização Universal'},
                {'data': datetime(2024, 2, 12), 'descricao': 'Carnaval'},
                {'data': datetime(2024, 2, 13), 'descricao': 'Carnaval'},
                {'data': datetime(2024, 2, 14), 'descricao': 'Quarta-feira de Cinzas'},
                {'data': datetime(2024, 3, 29), 'descricao': 'Sexta-feira Santa'},
                {'data': datetime(2024, 3, 31), 'descricao': 'Páscoa'},
                {'data': datetime(2024, 4, 21), 'descricao': 'Tiradentes'},
                {'data': datetime(2024, 5, 1), 'descricao': 'Dia do Trabalho'},
                {'data': datetime(2024, 5, 30), 'descricao': 'Corpus Christi'},
                {'data': datetime(2024, 9, 7), 'descricao': 'Independência do Brasil'},
                {'data': datetime(2024, 10, 12), 'descricao': 'Nossa Senhora Aparecida'},
                {'data': datetime(2024, 11, 2), 'descricao': 'Finados'},
                {'data': datetime(2024, 11, 15), 'descricao': 'Proclamação da República'},
                {'data': datetime(2024, 12, 25), 'descricao': 'Natal'}
            ]
            
            # MODIFICAÇÃO: Adicionado feriados para 2025
            print("Cadastrando feriados nacionais para 2025...")
            feriados_2025 = [
                {'data': datetime(2025, 1, 1), 'descricao': 'Confraternização Universal'},
                {'data': datetime(2025, 3, 3), 'descricao': 'Carnaval'},
                {'data': datetime(2025, 3, 4), 'descricao': 'Carnaval'},
                {'data': datetime(2025, 3, 5), 'descricao': 'Quarta-feira de Cinzas'},
                {'data': datetime(2025, 4, 18), 'descricao': 'Sexta-feira Santa'},
                {'data': datetime(2025, 4, 20), 'descricao': 'Páscoa'},
                {'data': datetime(2025, 4, 21), 'descricao': 'Tiradentes'},
                {'data': datetime(2025, 5, 1), 'descricao': 'Dia do Trabalho'},
                {'data': datetime(2025, 6, 19), 'descricao': 'Corpus Christi'},
                {'data': datetime(2025, 9, 7), 'descricao': 'Independência do Brasil'},
                {'data': datetime(2025, 10, 12), 'descricao': 'Nossa Senhora Aparecida'},
                {'data': datetime(2025, 11, 2), 'descricao': 'Finados'},
                {'data': datetime(2025, 11, 15), 'descricao': 'Proclamação da República'},
                {'data': datetime(2025, 12, 25), 'descricao': 'Natal'}
            ]
            
            # Adiciona os feriados de 2024
            for feriado_data in feriados_2024:
                feriado = Feriado(
                    data=feriado_data['data'].date(),
                    descricao=feriado_data['descricao']
                )
                db.session.add(feriado)
            
            # Adiciona os feriados de 2025
            for feriado_data in feriados_2025:
                feriado = Feriado(
                    data=feriado_data['data'].date(),
                    descricao=feriado_data['descricao']
                )
                db.session.add(feriado)
            
            # MODIFICAÇÃO: Adicionado tratamento de exceções para a criação dos feriados
            try:
                db.session.commit()
                print(f"Feriados cadastrados com sucesso! Total: {len(feriados_2024) + len(feriados_2025)}")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao cadastrar feriados: {str(e)}")
                print(traceback.format_exc())
                sys.exit(1)
        else:
            print(f"Já existem {feriados_count} feriados cadastrados.")
        
        print("Inicialização do banco de dados concluída com sucesso!")

except Exception as e:
    print(f"ERRO CRÍTICO durante a inicialização do banco de dados: {str(e)}")
    print("Detalhes do erro:")
    print(traceback.format_exc())
    sys.exit(1)

# MODIFICAÇÃO: Fim do arquivo com comentário explícito
# Este arquivo foi corrigido em Abril 2025 para resolver problemas de importação
