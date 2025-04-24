import os
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from datetime import datetime, date
import traceback
import sys

# Função para inicializar o banco de dados em produção
def init_production_db():
    """
    Inicializa o banco de dados em ambiente de produção.
    Cria tabelas, usuários padrão e feriados de exemplo.
    """
    try:
        # Imprime informações de debug para ajudar a identificar problemas
        print("Iniciando inicialização do banco de dados de produção...")
        print(f"Python version: {sys.version}")
        print(f"Diretório atual: {os.getcwd()}")
        
        # Cria a aplicação com configurações de produção
        app = create_app()
        
        with app.app_context():
            try:
                # Cria todas as tabelas definidas nos modelos
                print("Criando tabelas no banco de dados...")
                db.create_all()
                
                # Verifica se já existe um usuário administrador
                print("Verificando se já existe um usuário administrador...")
                admin = User.query.filter_by(is_admin=True).first()
                
                if not admin:
                    print("Criando usuário administrador...")
                    # Cria um usuário administrador padrão usando variáveis de ambiente
                    admin = User(
                        name=os.getenv('ADMIN_NAME', 'Administrador'),
                        email=os.getenv('ADMIN_EMAIL', 'admin@example.com'),
                        matricula=os.getenv('ADMIN_MATRICULA', 'ADMIN001'),
                        cargo=os.getenv('ADMIN_CARGO', 'Administrador'),
                        uf=os.getenv('ADMIN_UF', 'DF'),
                        telefone=os.getenv('ADMIN_TELEFONE', '(61) 99999-9999'),
                        vinculo=os.getenv('ADMIN_VINCULO', 'SENAPPEN - Administração'),
                        foto_path=os.getenv('ADMIN_FOTO_PATH', 'default.png'),
                        is_admin=True
                    )
                    
                    print("Definindo senha do administrador...")
                    admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
                    db.session.add(admin)
                    
                    print("Criando usuário de demonstração...")
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
                    )
                    user.set_password('demo123')
                    db.session.add(user)
                    
                    print("Adicionando feriados de exemplo...")
                    # Adiciona alguns feriados de exemplo
                    feriados = [
                        Feriado(data=date(2025, 1, 1), descricao='Confraternização Universal'),
                        Feriado(data=date(2025, 4, 21), descricao='Tiradentes'),
                        Feriado(data=date(2025, 5, 1), descricao='Dia do Trabalho'),
                        Feriado(data=date(2025, 9, 7), descricao='Independência do Brasil'),
                        Feriado(data=date(2025, 10, 12), descricao='Nossa Senhora Aparecida'),
                        Feriado(data=date(2025, 11, 2), descricao='Finados'),
                        Feriado(data=date(2025, 11, 15), descricao='Proclamação da República'),
                        Feriado(data=date(2025, 12, 25), descricao='Natal')
                    ]
                    
                    for feriado in feriados:
                        db.session.add(feriado)
                    
                    print("Realizando commit das alterações...")
                    db.session.commit()
                    print('Banco de dados de produção inicializado com sucesso!')
                else:
                    print('Banco de dados já inicializado.')
            except Exception as e:
                db.session.rollback()
                print(f'Erro ao inicializar o banco de dados: {e}')
                print(traceback.format_exc())
                # Não propagar a exceção para permitir que o script continue
    except Exception as e:
        print(f'Erro ao criar aplicação: {e}')
        print(traceback.format_exc())

# Executa a função apenas se este arquivo for executado diretamente
if __name__ == '__main__':
    try:
        init_production_db()
    except Exception as e:
        print(f"Erro fatal durante a execução: {e}")
        print(traceback.format_exc())
        # Saída com código de erro para indicar falha
        sys.exit(1)
