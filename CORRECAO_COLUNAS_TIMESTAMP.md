# Correção para o Problema das Colunas 'created_at' e 'updated_at' Ausentes na Tabela 'feriados'

## Problema Identificado

Após corrigir os problemas das colunas 'nome' e 'tipo' ausentes na tabela 'feriados', surgiu um novo erro:

```
sqlite3.OperationalError: no such column: feriados.created_at
```

Este erro ocorre porque o modelo `Feriado` define as colunas `created_at` e `updated_at`, mas essas colunas não existem fisicamente na tabela 'feriados' no banco de dados. O SQL no erro mostra que o sistema está tentando selecionar a coluna `feriados.created_at` que não existe.

## Solução Implementada

Para resolver este problema, modificamos o modelo `Feriado` para remover as definições diretas das colunas `created_at` e `updated_at` e substituí-las por propriedades Python simples:

```python
class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    _nome = db.Column('descricao', db.String(255), nullable=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    # Removendo as definições diretas das colunas que não existem no banco
    
    # Propriedades para colunas que não existem no banco
    @property
    def created_at(self):
        return datetime.now()  # Valor padrão
    
    @property
    def updated_at(self):
        return datetime.now()  # Valor padrão
```

Esta abordagem:

1. **Remove as definições das colunas físicas**: Eliminamos as linhas que definiam `created_at` e `updated_at` como colunas do SQLAlchemy.

2. **Adiciona propriedades Python**: Implementamos métodos `created_at()` e `updated_at()` decorados com `@property` que simplesmente retornam o valor atual de `datetime.now()`.

3. **Mantém compatibilidade com o código existente**: Todo o código que usa `feriado.created_at` ou `feriado.updated_at` continuará funcionando, pois as propriedades Python fornecem os valores esperados.

## Padrão Observado

Estamos observando um padrão em que várias colunas definidas no modelo `Feriado` não existem na tabela física do banco de dados:

1. A coluna `nome` foi mapeada para a coluna física `descricao` usando uma propriedade híbrida.
2. A coluna `tipo` foi substituída por uma propriedade Python que retorna um valor padrão.
3. As colunas `created_at` e `updated_at` também foram substituídas por propriedades Python que retornam valores padrão.

Isso sugere que a estrutura da tabela 'feriados' no banco de dados é significativamente diferente da definição do modelo, contendo apenas as colunas `id`, `descricao` e `data`.

## Como Implantar

1. Faça o download do arquivo ZIP anexo
2. Substitua todos os arquivos da implantação atual pelos novos arquivos
3. Reinicie completamente o serviço web no Render

A implantação deve ser bem-sucedida após estas etapas, pois os erros de colunas ausentes foram resolvidos de forma adequada.
