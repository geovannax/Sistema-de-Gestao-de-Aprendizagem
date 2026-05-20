/**
 * Controla a visibilidade do empty state baseado na presença de <li> em #page-aside
*/
function toggleEmptyState() {
    const aside = document.getElementById('page-aside');
    const emptyState = document.getElementById('empty-state-aside');
    
    if (!aside || !emptyState) return;
    
    const hasItems = aside.querySelectorAll('li').length > 0;
    
    if (hasItems) {
        emptyState.classList.add('d-none');
    } else {
        emptyState.classList.remove('d-none');
    }
}

// Verificar ao carregar
document.addEventListener('DOMContentLoaded', toggleEmptyState);

// Observar mudanças na lista para atualizar em tempo real
const observer = new MutationObserver(() => {
    toggleEmptyState();
});

const pageAside = document.getElementById('page-aside');
if (pageAside) {
    observer.observe(pageAside, {
        childList: true,  // Detecta adição/remoção de filhos
        subtree: true     // Observa toda a árvore
    });
}