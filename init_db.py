"""
Script para inicialização do banco de dados em produção com as colunas de afastamento.
Este script deve ser executado no ambiente de produção para garantir que o banco de dados
tenha todas as colunas necessárias para o funcionamento do sistema.
"""

import os
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from datetime import datetime
from dotenv import load_dotenv
from migrate_db import migrate

# Carrega variáveis de ambiente
load_dotenv()

# Cria a aplicação
app = create_app()

def init_db():
    """Inicializa o banco de dados com as tabelas e colunas necessárias"""
    with app.app_context():
        print("Verificando banco de dados...")
        
        # Verifica se o banco de dados já existe
        if os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')):
            print("Banco de dados já existe. Executando migração para adicionar novas colunas...")
            # Executa a migração para adicionar as colunas de afastamento
            migrate()
        else:
            print("Criando banco de dados...")
            # Cria todas as tabelas
            db.create_all()
            print("Banco de dados criado com sucesso!")
            
            # Verifica se já existe um usuário administrador
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                print("Criando usuário administrador padrão...")
                admin = User(
                    name='Administrador',
                    email='admin@example.com',
                    matricula='ADMIN001',
                    vinculo='SENAPPEN',
                    is_admin=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("Usuário administrador criado com sucesso!")
            else:
                print("Usuário administrador já existe.")
        
        print("Inicialização do banco de dados concluída!")

if __name__ == "__main__":
    init_db()
