"""
Script para testar a migração do banco de dados e verificar se as colunas foram adicionadas corretamente.
"""

import sqlite3
import os
from dotenv import load_dotenv
import sys

# Adiciona o diretório atual ao path para importar o script de migração
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from migrate_db import migrate

# Carrega variáveis de ambiente
load_dotenv()

# Obtém o caminho do banco de dados da variável de ambiente ou usa o padrão
DB_PATH = os.environ.get('DATABASE_URL', 'instance/ponto_eletronico.db')
# Remove o prefixo sqlite:/// se existir
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH[10:]

def test_migration():
    """Testa se a migração foi bem-sucedida e se as colunas existem no banco de dados"""
    print("Iniciando teste de migração...")
    
    # Executa a migração
    success = migrate()
    if not success:
        print("Falha na migração. Abortando teste.")
        return False
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verifica se as colunas existem
        cursor.execute("PRAGMA table_info(pontos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Verifica a coluna afastamento
        if 'afastamento' not in columns:
            print("ERRO: Coluna 'afastamento' não foi adicionada corretamente.")
            return False
        else:
            print("OK: Coluna 'afastamento' existe na tabela.")
        
        # Verifica a coluna tipo_afastamento
        if 'tipo_afastamento' not in columns:
            print("ERRO: Coluna 'tipo_afastamento' não foi adicionada corretamente.")
            return False
        else:
            print("OK: Coluna 'tipo_afastamento' existe na tabela.")
        
        # Tenta inserir um registro com as novas colunas
        print("Testando inserção de dados com as novas colunas...")
        try:
            cursor.execute("""
                INSERT INTO pontos (user_id, data, afastamento, tipo_afastamento)
                VALUES (1, '2025-04-23', 1, 'Teste de Migração')
            """)
            conn.commit()
            print("OK: Inserção de dados com as novas colunas bem-sucedida.")
            
            # Limpa o registro de teste
            cursor.execute("DELETE FROM pontos WHERE tipo_afastamento = 'Teste de Migração'")
            conn.commit()
            print("OK: Limpeza do registro de teste concluída.")
        except sqlite3.Error as e:
            print(f"ERRO ao inserir dados: {e}")
            return False
        
        # Fecha a conexão
        conn.close()
        print("Teste de migração concluído com sucesso!")
        return True
        
    except sqlite3.Error as e:
        print(f"Erro durante o teste: {e}")
        return False

if __name__ == "__main__":
    test_migration()
