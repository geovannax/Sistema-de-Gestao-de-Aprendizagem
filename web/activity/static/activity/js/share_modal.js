function getInitials(name) {
    return name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

function updatePlaceholder() {
    const select = document.querySelector('#id_groups');

    if (!select) return;

    const basePlaceholder = select.getAttribute('data-placeholder') || 'Buscar...';

    const hasUsers = document.querySelectorAll('#selected-users .shared-user-item').length > 0;

    const field = document.querySelector('.select2-search__field');

    if (!field) return;

    field.placeholder = hasUsers
        ? 'Adicionar mais...'
        : basePlaceholder;
}

function getRandomColor() {
    return Math.floor(Math.random() * 10) + 1; // Números de 1 a 10
}

$(document).ready(function() {
    let selectElement = $('#id_groups');
    let usersData = {};

    const params = new URLSearchParams(window.location.search);
    if (params.get('open_share_modal') === '1') {
        const shareModal = document.getElementById('shareModal');
        if (shareModal) {
            bootstrap.Modal.getOrCreateInstance(shareModal).show();
            params.delete('open_share_modal');
            const cleanUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}${window.location.hash}`;
            window.history.replaceState({}, '', cleanUrl);
        }
    }
    
    // Parsear dados do select
    try {
        usersData = JSON.parse(selectElement.attr('data-groups') || '{}');
    } catch (e) {
        console.error('Erro ao parsear dados de grupos', e);
    }
    
    $(document).on('select2:select', function (e) {
        let data = e.params.data;
        let userId = data.id;
        let userData = usersData[userId] || {};
        let group = userData.group || data.text;
        let description = userData.description || '';
        let colorIndex = Math.floor(Math.random() * 10) + 1;

        $('.shared-users-list').append(`
            <div class="shared-user-item" id="user-${userId}">
                <input type="hidden" name="groups" value="${userId}">
                <div class="shared-user-avatar" data-color="${colorIndex}">
                    ${getInitials(group)}
                </div>
                <div class="shared-user-info">
                    <div class="shared-user-name">${group}</div>
                    <div class="shared-user-email">${description}</div>
                </div>
                <div class="btn btn-outline-danger btn-sm shared-user-remove rounded-5 px-3" data-id="${userId}">
                    <i class="bi bi-trash"></i>
                </div>
            </div>
        `);

        selectElement.val(null).trigger('change');
        updatePlaceholder();
    });
});

$(document).on('click', '.shared-user-remove', function () {

    let item = $(this).closest('.shared-user-item');
    let userId = item.attr('id')?.replace('user-', '');

    // remove da UI
    item.remove();

    // 🔥 opcional: garantir limpeza no select2 (segurança)
    let select = $('#id_groups');
    let values = select.val() || [];

    values = values.filter(v => v != userId);

    select.val(values).trigger('change');
});


// Limpar todos os usuários ao fechar modal
$('#shareModal').on('hide.bs.modal', function () {
    // Remove todos os itens da lista
    $('.shared-users-list').empty();
    
    // Limpa o select2
    $('#id_groups').val(null).trigger('change');
});
