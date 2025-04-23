"""
Script de migração para adicionar colunas de afastamento à tabela pontos.
Este script deve ser executado no ambiente de produção para corrigir o erro:
'sqlite3.OperationalError: no such column: pontos.afastamento'
"""

import sqlite3
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Obtém o caminho do banco de dados da variável de ambiente ou usa o padrão
DB_PATH = os.environ.get('DATABASE_URL', 'instance/ponto_eletronico.db')
# Remove o prefixo sqlite:/// se existir
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH[10:]

def migrate():
    """Adiciona as colunas afastamento e tipo_afastamento à tabela pontos"""
    print(f"Conectando ao banco de dados: {DB_PATH}")
    
    # Verifica se o arquivo do banco de dados existe
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return False
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verifica se as colunas já existem
        cursor.execute("PRAGMA table_info(pontos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Adiciona a coluna afastamento se não existir
        if 'afastamento' not in columns:
            print("Adicionando coluna 'afastamento' à tabela pontos...")
            cursor.execute("ALTER TABLE pontos ADD COLUMN afastamento BOOLEAN DEFAULT 0")
            print("Coluna 'afastamento' adicionada com sucesso!")
        else:
            print("Coluna 'afastamento' já existe.")
        
        # Adiciona a coluna tipo_afastamento se não existir
        if 'tipo_afastamento' not in columns:
            print("Adicionando coluna 'tipo_afastamento' à tabela pontos...")
            cursor.execute("ALTER TABLE pontos ADD COLUMN tipo_afastamento VARCHAR(100)")
            print("Coluna 'tipo_afastamento' adicionada com sucesso!")
        else:
            print("Coluna 'tipo_afastamento' já existe.")
        
        # Commit das alterações
        conn.commit()
        print("Migração concluída com sucesso!")
        
        # Fecha a conexão
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Erro ao executar a migração: {e}")
        return False

if __name__ == "__main__":
    migrate()
