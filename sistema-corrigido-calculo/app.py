import os
from app import create_app

application = create_app()
app = application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    application.run(host='0.0.0.0', port=port)
