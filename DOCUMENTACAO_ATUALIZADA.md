# Documentação do Sistema de Ponto Eletrônico

## Visão Geral

O Sistema de Ponto Eletrônico é uma aplicação web desenvolvida para gerenciar o registro de ponto de funcionários da SENAPPEN. O sistema permite que os funcionários registrem seus horários de entrada e saída do trabalho, bem como do início e final do almoço, além de registrar as atividades desenvolvidas diariamente.

## Funcionalidades Principais

- Registro de entrada, saída e horários de almoço
- Cálculo automático de banco de horas considerando apenas dias úteis
- Cadastro de funcionários com informações completas
- Registro de atividades diárias
- Visualização em calendário da carga horária
- Dois níveis de acesso: funcionários e cadastradores (administradores)
- Sistema de cadastro de usuários com upload de foto

## Níveis de Acesso

### Funcionários
- Podem registrar seus próprios pontos diários
- Podem visualizar apenas seus próprios dados
- Podem registrar suas atividades diárias
- Podem visualizar seu próprio banco de horas

### Cadastradores (Administradores)
- Podem excluir inserções erradas
- Podem realizar retificações
- Podem visualizar relatórios de todos os funcionários
- Podem cadastrar feriados e férias dos funcionários
- Têm acesso completo a todas as funcionalidades do sistema

## Cadastro de Usuários

O sistema agora conta com um mecanismo de cadastro de usuários acessível diretamente da tela de login. Para se cadastrar, o usuário deve fornecer as seguintes informações obrigatórias:

- Nome completo
- Matrícula
- Cargo
- UF (todas as unidades federativas do Brasil, incluindo o DF)
- E-mail
- Telefone (com DDD)
- Tipo de vínculo com a SENAPPEN (Mobilizado, Colaborador Eventual, PPF, Terceirizado ou Estagiário)
- Foto (formato JPG ou PNG)
- Senha

## Banco de Horas

O sistema calcula automaticamente o banco de horas dos funcionários, considerando:
- Jornada de 8 horas diárias
- Apenas dias úteis (excluindo feriados e finais de semana)
- Equivalência de 1:1 para horas extras (1 hora extra = 1 hora no banco)

## Relatórios

O sistema gera relatórios mensais por funcionário, permitindo o acompanhamento detalhado da carga horária trabalhada e das atividades desenvolvidas.

## Visualização em Calendário

Os usuários podem visualizar sua carga horária em formato de calendário, com opções de visualização diária ou semanal.

## Cadastrador Original

O sistema já vem configurado com um cadastrador original com acesso completo a todas as funcionalidades:

- Nome: Marcelo Rocha Cortez
- Matrícula: 221.935-2
- Cargo: Policial Penal
- UF: Rio Grande do Norte
- E-mail: cortmr@gmail.com
- Telefone: (84)98101-7326
- Tipo de vínculo: Mobilizado

## Requisitos Técnicos

- Navegador web moderno (Chrome, Firefox, Edge, Safari)
- Conexão com a internet
- Câmera ou arquivo de imagem para upload de foto no cadastro

## Instruções de Uso

1. Acesse a página de login do sistema
2. Se já possui cadastro, insira seu e-mail e senha
3. Se não possui cadastro, clique em "Cadastre-se aqui" e preencha o formulário com todos os dados obrigatórios
4. Após o login, você será direcionado para o dashboard principal
5. Utilize o menu de navegação para acessar as diferentes funcionalidades do sistema

## Suporte

Em caso de dúvidas ou problemas, entre em contato com o administrador do sistema (cadastrador original).
