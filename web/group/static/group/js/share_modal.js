function getInitials(name) {
    return name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

function updatePlaceholder() {
    const select = document.querySelector('#id_users');

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
    let selectElement = $('#id_users');
    let usersData = {};
    
    // Parsear dados do select
    try {
        usersData = JSON.parse(selectElement.attr('data-users') || '{}');
    } catch (e) {
        console.error('Erro ao parsear dados de usuários', e);
    }
    
    $(document).on('select2:select', function (e) {
        let data = e.params.data;
        let userId = data.id;
        let userData = usersData[userId] || {};
        let fullName = userData.fullname || data.text;
        let colorIndex = Math.floor(Math.random() * 10) + 1;

        $('.shared-users-list').append(`
            <div class="shared-user-item" id="user-${userId}">
                <input type="hidden" name="users" value="${userId}">
                <div class="shared-user-avatar" data-color="${colorIndex}">
                    ${getInitials(fullName)}
                </div>
                <div class="shared-user-info">
                    <div class="shared-user-name">${fullName}</div>
                    <div class="shared-user-email">${data.text}</div>
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
    let select = $('#id_users');
    let values = select.val() || [];

    values = values.filter(v => v != userId);

    select.val(values).trigger('change');
});


// Limpar todos os usuários ao fechar modal
$('#shareModal').on('hide.bs.modal', function () {
    // Remove todos os itens da lista
    $('.shared-users-list').empty();
    
    // Limpa o select2
    $('#id_users').val(null).trigger('change');
});
