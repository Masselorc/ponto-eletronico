from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado

app = create_app()

# Cria um contexto de aplicação
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
        db.session.commit()
        print('Usuário administrador criado com sucesso!')
    else:
        print('Usuário administrador já existe.')
    
    print('Banco de dados inicializado com sucesso!')
