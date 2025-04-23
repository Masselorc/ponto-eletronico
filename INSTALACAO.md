# Requisitos
- Python 3.6+
- pip (gerenciador de pacotes Python)
- Servidor web (para produção)

# Instalação

## 1. Clone o repositório ou extraia os arquivos

```bash
git clone <url-do-repositorio>
cd ponto-eletronico
```

Ou extraia os arquivos do arquivo zip para uma pasta chamada `ponto-eletronico`.

## 2. Crie um ambiente virtual Python (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

## 3. Instale as dependências

```bash
pip install -r requirements.txt
```

## 4. Configure as variáveis de ambiente

Edite o arquivo `.env` na raiz do projeto:

```
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URI=sqlite:///ponto_eletronico.db
DEBUG=False
```

Para maior segurança em produção, gere uma chave secreta aleatória:

```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

## 5. Inicialize o banco de dados

```bash
python create_db.py
```

Isso criará o banco de dados SQLite e um usuário administrador padrão:
- Email: admin@example.com
- Senha: admin123

**Importante:** Altere a senha do administrador após o primeiro login!

## 6. Execute o aplicativo

### Para desenvolvimento:

```bash
python run.py
```

### Para produção:

Recomendamos usar Gunicorn como servidor WSGI:

```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Ou com uWSGI:

```bash
pip install uwsgi
uwsgi --http 0.0.0.0:5000 --module wsgi:app
```

## 7. Acesse o aplicativo

Abra um navegador e acesse:

```
http://localhost:5000
```

# Estrutura do Projeto

```
ponto-eletronico/
├── app/                    # Pacote principal da aplicação
│   ├── controllers/        # Controladores (rotas)
│   ├── forms/              # Formulários
│   ├── models/             # Modelos de dados
│   ├── static/             # Arquivos estáticos (CSS, JS)
│   ├── templates/          # Templates HTML
│   └── __init__.py         # Inicialização da aplicação
├── migrations/             # Migrações do banco de dados
├── .env                    # Variáveis de ambiente
├── create_db.py            # Script para criar o banco de dados
├── requirements.txt        # Dependências do projeto
├── run.py                  # Script para executar em desenvolvimento
└── wsgi.py                 # Ponto de entrada para servidores WSGI
```

# Backup e Manutenção

## Backup do Banco de Dados

Para fazer backup do banco de dados SQLite:

```bash
cp ponto_eletronico.db ponto_eletronico_backup_$(date +%Y%m%d).db
```

## Atualização

1. Faça backup do banco de dados
2. Atualize os arquivos do código-fonte
3. Instale quaisquer novas dependências: `pip install -r requirements.txt`
4. Reinicie o servidor
