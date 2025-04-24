#!/bin/bash

# Script para testar a aplicação corrigida
echo "Iniciando testes da aplicação corrigida..."

# Criar ambiente virtual
echo "Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Inicializar banco de dados
echo "Inicializando banco de dados..."
python init_db.py

# Executar testes básicos
echo "Executando testes básicos..."

# Teste 1: Verificar se a aplicação inicia corretamente
echo "Teste 1: Verificando inicialização da aplicação..."
python -c "from app import create_app; app = create_app(); print('Aplicação inicializada com sucesso!')" || { echo "Falha ao inicializar a aplicação"; exit 1; }

# Teste 2: Verificar se o modelo Feriado está corretamente definido
echo "Teste 2: Verificando modelo Feriado..."
python -c "from app.models.feriado import Feriado; from datetime import date; f = Feriado(descricao='Teste', data=date.today()); print(f.nome); print('Modelo Feriado OK!')" || { echo "Falha no modelo Feriado"; exit 1; }

# Teste 3: Verificar se o cálculo de horas trabalhadas está correto
echo "Teste 3: Verificando cálculo de horas trabalhadas..."
python -c "from app.models.ponto import Ponto; from datetime import datetime, date; p = Ponto(data=date.today(), entrada=datetime.combine(date.today(), datetime.min.time().replace(hour=8, minute=0)), saida_almoco=datetime.combine(date.today(), datetime.min.time().replace(hour=12, minute=0)), retorno_almoco=datetime.combine(date.today(), datetime.min.time().replace(hour=13, minute=0)), saida=datetime.combine(date.today(), datetime.min.time().replace(hour=17, minute=0))); p.calcular_horas_trabalhadas(); print(f'Horas trabalhadas: {p.horas_trabalhadas}'); assert p.horas_trabalhadas == 8.0, 'Cálculo incorreto'; print('Cálculo de horas OK!')" || { echo "Falha no cálculo de horas trabalhadas"; exit 1; }

# Teste 4: Verificar se o backup do banco de dados funciona
echo "Teste 4: Verificando backup do banco de dados..."
python -c "from app import create_app; from app.utils.backup import backup_database; app = create_app(); with app.app_context(): result = backup_database(app); print(f'Backup realizado: {result}'); assert result == True, 'Falha no backup'; print('Backup OK!')" || { echo "Falha no backup do banco de dados"; exit 1; }

# Teste 5: Verificar se o Flask-Migrate está configurado corretamente
echo "Teste 5: Verificando configuração do Flask-Migrate..."
python -c "from app import create_app, migrate; app = create_app(); print('Flask-Migrate configurado corretamente!')" || { echo "Falha na configuração do Flask-Migrate"; exit 1; }

echo "Todos os testes concluídos com sucesso!"
echo "A aplicação corrigida está funcionando corretamente."

# Desativar ambiente virtual
deactivate
