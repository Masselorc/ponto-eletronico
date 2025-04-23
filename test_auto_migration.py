"""
Script para testar a migração automática do banco de dados.
Este script simula o ambiente de produção para verificar se a migração
das colunas afastamento e tipo_afastamento ocorre corretamente.
"""

import os
import sqlite3
import tempfile
import shutil
from app import create_app, db
from app.models.user import User
from app.models.ponto import Ponto
from datetime import date

def test_auto_migration():
    """Testa se a migração automática funciona corretamente"""
    print("Iniciando teste de migração automática...")
    
    # Cria um diretório temporário para o banco de dados de teste
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_db.sqlite')
    
    try:
        # Configura a variável de ambiente para o banco de dados de teste
        os.environ['DATABASE_URI'] = f'sqlite:///{db_path}'
        
        # Cria um banco de dados de teste sem as colunas de afastamento
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Cria a tabela users
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            matricula TEXT NOT NULL,
            vinculo TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            cargo TEXT,
            uf TEXT,
            telefone TEXT,
            foto TEXT
        )
        ''')
        
        # Cria a tabela pontos sem as colunas de afastamento
        cursor.execute('''
        CREATE TABLE pontos (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            data DATE NOT NULL,
            entrada TIME,
            saida_almoco TIME,
            retorno_almoco TIME,
            saida TIME,
            horas_trabalhadas FLOAT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Insere um usuário de teste
        cursor.execute('''
        INSERT INTO users (name, email, password_hash, matricula, vinculo, is_admin)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Usuário Teste', 'teste@example.com', 'hash', 'TEST001', 'SENAPPEN', 0))
        
        # Insere um registro de ponto de teste
        cursor.execute('''
        INSERT INTO pontos (user_id, data, entrada, saida)
        VALUES (?, ?, ?, ?)
        ''', (1, date.today().isoformat(), '08:00', '17:00'))
        
        conn.commit()
        conn.close()
        
        print("Banco de dados de teste criado sem as colunas de afastamento")
        
        # Cria a aplicação, o que deve executar a migração automática
        app = create_app()
        
        # Verifica se as colunas foram adicionadas
        with app.app_context():
            # Tenta acessar um registro com as novas colunas
            ponto = Ponto.query.filter_by(user_id=1).first()
            
            # Verifica se o atributo afastamento existe e pode ser acessado
            try:
                afastamento = ponto.afastamento
                print(f"Coluna 'afastamento' existe e tem valor: {afastamento}")
            except AttributeError:
                print("ERRO: Coluna 'afastamento' não foi adicionada corretamente")
                return False
            
            # Verifica se o atributo tipo_afastamento existe e pode ser acessado
            try:
                tipo_afastamento = ponto.tipo_afastamento
                print(f"Coluna 'tipo_afastamento' existe e tem valor: {tipo_afastamento}")
            except AttributeError:
                print("ERRO: Coluna 'tipo_afastamento' não foi adicionada corretamente")
                return False
            
            # Tenta atualizar os valores das novas colunas
            ponto.afastamento = True
            ponto.tipo_afastamento = "Teste de Migração Automática"
            db.session.commit()
            
            # Verifica se os valores foram salvos corretamente
            ponto_atualizado = Ponto.query.filter_by(user_id=1).first()
            if ponto_atualizado.afastamento != True or ponto_atualizado.tipo_afastamento != "Teste de Migração Automática":
                print("ERRO: Não foi possível atualizar os valores das novas colunas")
                return False
            
            print("Valores das novas colunas atualizados com sucesso!")
        
        print("Teste de migração automática concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        return False
    
    finally:
        # Limpa o diretório temporário
        shutil.rmtree(temp_dir)
        # Restaura a variável de ambiente
        if 'DATABASE_URI' in os.environ:
            del os.environ['DATABASE_URI']

if __name__ == "__main__":
    test_auto_migration()
