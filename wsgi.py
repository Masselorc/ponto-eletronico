import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração para garantir que as variáveis de ambiente estejam disponíveis no Render
os.environ.setdefault('SECRET_KEY', os.getenv('SECRET_KEY', 'chave_secreta_do_aplicativo'))
os.environ.setdefault('DATABASE_URI', os.getenv('DATABASE_URI', 'sqlite:///ponto_eletronico.db'))
os.environ.setdefault('DEBUG', os.getenv('DEBUG', 'False'))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
