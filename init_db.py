"""
Script para inicialização do banco de dados em produção com as colunas de afastamento.
Este script deve ser executado no ambiente de produção para garantir que o banco de dados
tenha todas as colunas necessárias para o funcionamento do sistema.
"""

import os
import sys
from pathlib import Path
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from datetime import datetime
from dotenv import load_dotenv
from app.utils.backup import backup_database

# Carrega variáveis de ambiente
load_dotenv()

# Cria a aplicação
app = create_app()

def init_db():
    """Inicializa o banco de dados com as tabelas e colunas necessárias"""
    with app.app_context():
        print("Verificando banco de dados...")
        
        # Obtém o caminho do banco de dados a partir da configuração
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Verifica se é um banco SQLite
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            
            # Se o caminho for relativo, converte para absoluto
            if not os.path.isabs(db_path):
                # Obtém o caminho base da aplicação
                base_path = Path(app.root_path).parent
                db_path = os.path.join(base_path, db_path)
            
            # Normaliza o caminho
            db_path = os.path.normpath(db_path)
            
            # Verifica se o diretório existe
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Diretório do banco de dados criado: {db_dir}")
            
            # Verifica se o banco de dados já existe
            if os.path.exists(db_path):
                print("Banco de dados já existe. Criando backup antes da migração...")
                # Cria backup do banco de dados
                backup_database(app)
            else:
                print("Criando banco de dados...")
                # Cria todas as tabelas
                db.create_all()
                print("Banco de dados criado com sucesso!")
                
                # Verifica se já existe um usuário administrador
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
                admin = User.query.filter_by(email=admin_email).first()
                if not admin:
                    print("Criando usuário administrador padrão...")
                    admin = User(
                        name=os.getenv('ADMIN_NAME', 'Administrador'),
                        email=admin_email,
                        matricula=os.getenv('ADMIN_MATRICULA', 'ADMIN001'),
                        cargo=os.getenv('ADMIN_CARGO', 'Administrador'),
                        uf=os.getenv('ADMIN_UF', 'DF'),
                        telefone=os.getenv('ADMIN_TELEFONE', '(61) 99999-9999'),
                        vinculo=os.getenv('ADMIN_VINCULO', 'SENAPPEN'),
                        foto_path=os.getenv('ADMIN_FOTO_PATH', 'default.png'),
                        is_admin=True
                    )
                    admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
                    db.session.add(admin)
                    db.session.commit()
                    print("Usuário administrador criado com sucesso!")
                else:
                    print("Usuário administrador já existe.")
        else:
            print(f"Usando banco de dados não-SQLite: {db_uri}")
            # Para outros bancos de dados, apenas cria as tabelas
            db.create_all()
            print("Tabelas criadas com sucesso!")
        
        print("Inicialização do banco de dados concluída!")

if __name__ == "__main__":
    init_db()
