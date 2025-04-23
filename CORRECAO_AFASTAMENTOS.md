# Correções na Funcionalidade de Férias e Afastamentos

## Problema Identificado

O sistema apresentava dois problemas relacionados à funcionalidade de "Férias ou outros afastamentos":

1. **Problema na interface de registro**: Quando o usuário marcava a opção de "Férias ou outros afastamentos", os campos de horários (entrada, saída e almoço) não eram corretamente desabilitados na interface.

2. **Problema na exibição no calendário**: Os dias marcados como férias ou afastamentos não eram exibidos corretamente no calendário, continuando a aparecer como "Sem registro" em vez de mostrar o tipo de afastamento.

## Soluções Implementadas

### 1. Correção na Interface de Registro de Ponto

- Criado um arquivo JavaScript dedicado (`registro_ponto.js`) para gerenciar o comportamento da interface
- Implementada lógica robusta para desabilitar completamente os campos de horário quando a opção de afastamento é marcada
- Adicionadas verificações para garantir que os elementos existam antes de manipulá-los
- Implementada a desativação visual dos botões "Usar horário atual" quando o afastamento é marcado
- Adicionada a limpeza automática dos valores dos campos de horário ao marcar afastamento
- Melhorada a interface com textos explicativos e formatação mais clara

### 2. Aprimoramento da Exibição no Calendário

- Criado um estilo específico para os afastamentos com a classe "afastamento-badge"
- Adicionados ícones intuitivos para cada tipo de afastamento:
  - Férias: ícone de guarda-sol
  - Licença Médica: ícone de procedimentos médicos
  - Licença Maternidade/Paternidade: ícone de bebê
  - Abono: ícone de calendário com check
  - Outros afastamentos: ícone de usuário com relógio
- Melhorada a lógica de exibição para garantir que os afastamentos sejam exibidos corretamente
- Adicionado um contador de dias de afastamento no resumo do mês
- Ajustado o cálculo de dias trabalhados e horas para excluir os dias de afastamento

## Benefícios das Correções

1. **Melhor experiência do usuário**: Interface mais intuitiva e feedback visual claro
2. **Prevenção de erros**: Impossibilidade de registrar horários em dias de afastamento
3. **Visualização aprimorada**: Identificação clara dos dias de afastamento no calendário
4. **Estatísticas mais precisas**: Separação correta entre dias trabalhados e dias de afastamento
5. **Organização melhorada**: Categorização visual dos diferentes tipos de afastamento

## Como Utilizar

1. **Para registrar um afastamento**:
   - Acesse a página "Registro de Ponto"
   - Selecione a data desejada
   - Marque a opção "Férias ou outros afastamentos"
   - Selecione o tipo de afastamento no menu suspenso
   - Clique em "Registrar Horários"

2. **Para visualizar os afastamentos**:
   - Acesse a página "Calendário"
   - Os dias de afastamento serão exibidos com um badge roxo indicando o tipo
   - No resumo do mês, você verá a contagem de dias de afastamento
