import os
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from datetime import datetime, date

app = create_app()

# Função para inicializar o banco de dados em produção
def init_production_db():
    with app.app_context():
        # Cria todas as tabelas definidas nos modelos
        db.create_all()
        
        # Verifica se já existe um usuário administrador
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            # Cria um usuário administrador padrão
            admin = User(
                name='Administrador',
                email='admin@example.com',
                matricula='ADMIN001',
                vinculo='SENAPPEN - Administração',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Cria um usuário comum para demonstração
            user = User(
                name='Usuário Demonstração',
                email='demo@example.com',
                matricula='DEMO001',
                vinculo='SENAPPEN - Demonstração',
                is_admin=False
            )
            user.set_password('demo123')
            db.session.add(user)
            
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
            
            db.session.commit()
            print('Banco de dados de produção inicializado com sucesso!')
        else:
            print('Banco de dados já inicializado.')

if __name__ == '__main__':
    init_production_db()
