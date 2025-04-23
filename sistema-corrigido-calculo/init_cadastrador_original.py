import os
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto, Atividade, Feriado
from datetime import datetime, date
import shutil

app = create_app()

def init_cadastrador_original():
    with app.app_context():
        # Cria todas as tabelas definidas nos modelos
        db.create_all()
        
        # Verifica se já existe um usuário administrador
        admin = User.query.filter_by(email='cortmr@gmail.com').first()
        if not admin:
            # Copia a foto do cadastrador original para o diretório de uploads
            upload_folder = os.path.join(app.root_path, 'static/uploads/fotos')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Nome do arquivo de destino
            foto_filename = 'marcelo_original.png'
            foto_path = os.path.join(upload_folder, foto_filename)
            
            # Copia a foto do upload para o diretório de fotos
            shutil.copy('/home/ubuntu/upload/marcelo.png', foto_path)
            
            # Cria o cadastrador original
            admin = User(
                name='Marcelo Rocha Cortez',
                email='cortmr@gmail.com',
                matricula='221.935-2',
                cargo='Policial Penal',
                uf='RN',
                telefone='(84)98101-7326',
                vinculo='Mobilizado',
                foto_path='uploads/fotos/' + foto_filename,
                is_admin=True  # Cadastrador original é administrador
            )
            admin.set_password('smdmf182')
            db.session.add(admin)
            
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
            print('Cadastrador original criado com sucesso!')
        else:
            print('Cadastrador original já existe.')

if __name__ == '__main__':
    init_cadastrador_original()
