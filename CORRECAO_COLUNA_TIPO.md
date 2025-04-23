# Correção para o Problema da Coluna 'tipo' Ausente na Tabela 'feriados'

## Problema Identificado

Após corrigir o problema da coluna 'nome' ausente na tabela 'feriados', surgiu um novo erro:

```
sqlite3.OperationalError: no such column: feriados.tipo
```

Este erro ocorre porque o modelo `Feriado` define uma coluna `tipo`, mas essa coluna não existe fisicamente na tabela 'feriados' no banco de dados. O SQL no erro mostra que o sistema está tentando selecionar a coluna `feriados.tipo` que não existe.

## Solução Implementada

Para resolver este problema, modificamos o modelo `Feriado` para remover a definição direta da coluna `tipo` e substituí-la por uma propriedade Python simples:

```python
class Feriado(db.Model):
    __tablename__ = 'feriados'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    _nome = db.Column('descricao', db.String(255), nullable=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    # Removendo a definição direta da coluna 'tipo' que não existe no banco
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Propriedade para 'tipo' que retorna um valor padrão já que não existe no banco
    @property
    def tipo(self):
        return 'nacional'  # Valor padrão para todos os feriados
```

Esta abordagem:

1. **Remove a definição da coluna física**: Eliminamos a linha `tipo = db.Column(db.String(20), default='nacional')` que estava causando o erro.

2. **Adiciona uma propriedade Python**: Implementamos um método `tipo()` decorado com `@property` que simplesmente retorna o valor padrão 'nacional'.

3. **Mantém compatibilidade com o código existente**: Todo o código que usa `feriado.tipo` continuará funcionando, pois a propriedade Python fornece o valor esperado.

## Diferença em Relação à Solução Anterior

Para a coluna 'nome', usamos uma propriedade híbrida do SQLAlchemy para mapear para a coluna física 'descricao' que existe no banco de dados. Para a coluna 'tipo', usamos uma abordagem diferente porque:

1. Não há uma coluna física equivalente no banco de dados para mapear.
2. O valor 'nacional' é um padrão razoável para todos os feriados.
3. Uma propriedade Python simples é suficiente quando não precisamos persistir o valor no banco.

## Como Implantar

1. Faça o download do arquivo ZIP anexo
2. Substitua todos os arquivos da implantação atual pelos novos arquivos
3. Reinicie completamente o serviço web no Render

A implantação deve ser bem-sucedida após estas etapas, pois o erro de coluna ausente foi resolvido de forma adequada.
