import os
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade
# IMPORTANTE: Importação corrigida do modelo Feriado
from app.models.feriado import Feriado
from datetime import datetime, date

# VERSÃO CORRIGIDA - ABRIL 2025
# Função para inicializar o banco de dados em produção
def init_production_db():
    """
    Inicializa o banco de dados em ambiente de produção.
    Cria tabelas, usuários padrão e feriados de exemplo.
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Cria todas as tabelas definidas nos modelos
            db.create_all()
            
            # Verifica se já existe um usuário administrador
            admin = User.query.filter_by(is_admin=True).first()
            if not admin:
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
                admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
                db.session.add(admin)
                
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
                
                # ADICIONADO: Feriados de exemplo para o ano de 2025
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
                
                db.session.commit()
                print('Banco de dados de produção inicializado com sucesso!')
            else:
                print('Banco de dados já inicializado.')
        except Exception as e:
            print(f'Erro ao inicializar o banco de dados: {e}')
            # Não propagar a exceção para permitir que o script continue

# Ponto de entrada principal
if __name__ == '__main__':
    init_production_db()
