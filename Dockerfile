FROM python:3.10-slim

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

# Inicializa o banco de dados
RUN python init_db_production.py

# Expõe a porta que o aplicativo usará
EXPOSE 8080

# Comando para iniciar o aplicativo
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"]
