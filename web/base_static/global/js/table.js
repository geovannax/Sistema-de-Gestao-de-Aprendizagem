document.querySelectorAll('tr.clickable-row').forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function(e) {
        // Verifica se o clique foi em um botão, link ou dentro deles
        const isClickableElement = e.target.closest('a, button, [role="button"]');
        if (!isClickableElement) {
            window.location.href = this.dataset.href;
        }
    });
});
