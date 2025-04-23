// Atualiza o relógio em tempo real
function atualizarRelogio() {
    const agora = new Date();
    const horas = agora.getHours().toString().padStart(2, '0');
    const minutos = agora.getMinutes().toString().padStart(2, '0');
    const segundos = agora.getSeconds().toString().padStart(2, '0');
    
    document.getElementById('relogio').textContent = `${horas}:${minutos}:${segundos}`;
}

// Inicializa tooltips do Bootstrap
function inicializarTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Função para confirmar exclusão
function confirmarExclusao(event, mensagem) {
    if (!confirm(mensagem || 'Tem certeza que deseja excluir este item?')) {
        event.preventDefault();
        return false;
    }
    return true;
}

// Quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa tooltips
    inicializarTooltips();
    
    // Atualiza o relógio a cada segundo se o elemento existir
    if (document.getElementById('relogio')) {
        atualizarRelogio();
        setInterval(atualizarRelogio, 1000);
    }
    
    // Adiciona confirmação para botões de exclusão
    const botoesExcluir = document.querySelectorAll('.btn-excluir');
    botoesExcluir.forEach(function(botao) {
        botao.addEventListener('click', function(event) {
            return confirmarExclusao(event, botao.getAttribute('data-confirm-message'));
        });
    });
    
    // Fecha alertas automaticamente após 5 segundos
    const alertas = document.querySelectorAll('.alert');
    alertas.forEach(function(alerta) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alerta);
            bsAlert.close();
        }, 5000);
    });
});
