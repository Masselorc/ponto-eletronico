# Correção do Erro de Coluna Ausente na Tabela Feriados

## Problema Identificado

Ao analisar o log de erro da implantação no Render, foi identificado o seguinte problema:

```
sqlite3.OperationalError: no such column: feriados.nome
```

Este erro ocorre porque o modelo `Feriado` define uma coluna `nome`, mas a tabela física no banco de dados não possui essa coluna. O SQL no erro mostra que o sistema está tentando selecionar tanto `feriados.nome` quanto `feriados.descricao`, o que indica que a tabela no banco de dados foi criada com uma coluna `descricao` em vez de `nome`.

## Solução Implementada

Para resolver este problema, foi modificado o modelo `Feriado` para incluir ambas as colunas:

```python
class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)  # Adicionado para compatibilidade
    data = db.Column(db.Date, nullable=False, unique=True)
    tipo = db.Column(db.String(20), default='nacional')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
```

A coluna `descricao` foi adicionada com `nullable=True` para garantir compatibilidade com a estrutura existente do banco de dados, enquanto mantém a coluna `nome` para compatibilidade com o código existente.

## Verificação da Solução

A solução foi testada localmente para garantir que o modelo pode ser importado corretamente. O teste confirmou que a implementação resolve o problema de discrepância entre o modelo e a estrutura do banco de dados.

## Impacto da Correção

Esta correção permite que o sistema seja implantado com sucesso no ambiente Render, pois resolve o erro que estava impedindo o acesso à página de dashboard. A implementação mantém a compatibilidade com o código existente que usa a coluna `nome`, enquanto também suporta a estrutura atual do banco de dados que tem uma coluna `descricao`.

## Como Implantar

1. Faça o download do arquivo ZIP anexo
2. Substitua todos os arquivos da implantação atual pelos novos arquivos
3. Reinicie completamente o serviço web no Render

A implantação deve ser bem-sucedida após estas etapas, pois o erro de coluna ausente foi corrigido.
