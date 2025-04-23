# Correção do Erro de Conflito na Definição da Tabela 'feriados'

## Problema Identificado

Ao analisar o log de erro da implantação no Render, foi identificado o seguinte problema:

```
sqlalchemy.exc.InvalidRequestError: Table 'feriados' is already defined for this MetaData instance.  Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
```

Este erro ocorre porque a tabela 'feriados' já está definida em algum lugar do código, e quando tentamos defini-la novamente no arquivo `feriado.py`, ocorre um conflito. Isso é comum em aplicações Flask com SQLAlchemy quando:

1. Há múltiplas definições da mesma tabela em diferentes partes do código
2. O aplicativo é reiniciado várias vezes durante o desenvolvimento
3. Existem migrações ou scripts que definem a mesma tabela

## Solução Implementada

Para resolver este problema, foi adicionado o parâmetro `extend_existing=True` à definição da tabela no modelo Feriado:

```python
class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    # ... restante do código ...
```

O parâmetro `extend_existing=True` informa ao SQLAlchemy que, se a tabela já estiver definida, ele deve estender a definição existente em vez de tentar criar uma nova, evitando assim o conflito.

## Verificação da Solução

A solução foi testada localmente para garantir que o módulo pode ser importado corretamente. O teste confirmou que a implementação resolve o problema de conflito na definição da tabela.

## Impacto da Correção

Esta correção permite que o sistema seja implantado com sucesso no ambiente Render, pois resolve o erro que estava impedindo a inicialização do aplicativo. A implementação não afeta o funcionamento do modelo Feriado, apenas resolve o conflito de definição da tabela.

## Como Implantar

1. Faça o download do arquivo ZIP anexo
2. Substitua todos os arquivos da implantação atual pelos novos arquivos
3. Reinicie completamente o serviço web no Render

A implantação deve ser bem-sucedida após estas etapas, pois o erro de conflito na definição da tabela foi corrigido.
