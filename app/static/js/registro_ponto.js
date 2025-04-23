// Funções para o registro de ponto
document.addEventListener('DOMContentLoaded', function() {
    // Atualiza o relógio a cada segundo
    function atualizarRelogio() {
        const agora = new Date();
        const horas = agora.getHours().toString().padStart(2, '0');
        const minutos = agora.getMinutes().toString().padStart(2, '0');
        const segundos = agora.getSeconds().toString().padStart(2, '0');
        const relogio = document.getElementById('relogio');
        if (relogio) {
            relogio.textContent = `${horas}:${minutos}:${segundos}`;
        }
    }
    
    // Atualiza o relógio imediatamente e depois a cada segundo
    atualizarRelogio();
    setInterval(atualizarRelogio, 1000);
    
    // Botões para preencher com horário atual
    const botoesHoraAtual = document.querySelectorAll('.btn-hora-atual');
    botoesHoraAtual.forEach(function(botao) {
        botao.addEventListener('click', function() {
            const targetField = this.getAttribute('data-target');
            const agora = new Date();
            const horas = agora.getHours().toString().padStart(2, '0');
            const minutos = agora.getMinutes().toString().padStart(2, '0');
            document.getElementById(targetField).value = `${horas}:${minutos}`;
        });
    });
    
    // Controle de exibição dos campos de afastamento
    const checkAfastamento = document.getElementById('check_afastamento');
    if (checkAfastamento) {
        const divTipoAfastamento = document.getElementById('div_tipo_afastamento');
        const divHorarios = document.getElementById('div_horarios');
        const botoesHoraAtual = document.querySelectorAll('.btn-hora-atual');
        
        // Campos de horário
        const camposHorario = [
            document.getElementById('hora_entrada_input'),
            document.getElementById('hora_saida_almoco_input'),
            document.getElementById('hora_retorno_almoco_input'),
            document.getElementById('hora_saida_input')
        ];
        
        // Função para atualizar a visibilidade e estado dos campos
        function atualizarCampos() {
            if (checkAfastamento.checked) {
                // Mostra o tipo de afastamento
                divTipoAfastamento.style.display = 'block';
                
                // Esconde a seção de horários
                divHorarios.style.display = 'none';
                
                // Desabilita os campos de horário e limpa os valores
                camposHorario.forEach(campo => {
                    if (campo) {
                        campo.disabled = true;
                        campo.value = '';
                    }
                });
                
                // Desabilita os botões de hora atual
                botoesHoraAtual.forEach(botao => {
                    botao.disabled = true;
                    botao.classList.add('disabled');
                });
            } else {
                // Esconde o tipo de afastamento
                divTipoAfastamento.style.display = 'none';
                
                // Mostra a seção de horários
                divHorarios.style.display = 'flex';
                
                // Habilita os campos de horário
                camposHorario.forEach(campo => {
                    if (campo) {
                        campo.disabled = false;
                    }
                });
                
                // Habilita os botões de hora atual
                botoesHoraAtual.forEach(botao => {
                    botao.disabled = false;
                    botao.classList.remove('disabled');
                });
            }
        }
        
        // Executa na inicialização
        atualizarCampos();
        
        // Adiciona evento de mudança ao checkbox
        checkAfastamento.addEventListener('change', atualizarCampos);
    }
});
