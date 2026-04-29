
function updateFormValues(btn) {
    // Remove o alerta existente, se houver
    const existingAlert = document.getElementById('option-alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    const totalForms = document.querySelectorAll('#options-container .option-form').length;
    // Atualiza o TOTAL_FORMS do formset
    document.getElementById('id_options-TOTAL_FORMS').value = totalForms + 1;
    // Atualiza os valores enviados pelo htmx
    btn.setAttribute('hx-vals', JSON.stringify({
        total_forms: totalForms
    }));
}

function optionsAlertError(message) {

    const existingAlert = document.getElementById('option-alert');
    if (existingAlert) {
        existingAlert.remove();
    }
   
    // Criar alerta usando JavaScript vanilla (sem React)
    const alert = document.createElement('div');
    alert.id = 'option-alert';
    alert.className = 'alert text-danger';
    alert.textContent = message;
    
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.after(alert);

    // Remover o alerta automaticamente após 10 segundos
    setTimeout(() => alert.remove(), 10000);
}

function removeOptionForm(button) {
    const optionsContainer = document.getElementById('options-container');
    const visibleForms = optionsContainer.querySelectorAll('.option-form:not([style*="display: none"])');
    
    if (visibleForms.length <= 2) {
        optionsAlertError('A atividade deve conter pelo menos 2 opções.');
        return;
    }

    // Encontra o formulário pai
    const optionForm = button.closest('.option-form');
    
    // Encontra e marca o checkbox DELETE como checked
    const deleteCheckbox = optionForm.querySelector('[name$="-DELETE"]');
    if (deleteCheckbox) {
        deleteCheckbox.checked = true;
    }
    
    // Se is_correct estiver marcado, desmarcar
    const isCorrectCheckbox = optionForm.querySelector('[name$="-is_correct"]');
    if (isCorrectCheckbox && isCorrectCheckbox.checked) {
        isCorrectCheckbox.checked = false;
    }

    // Oculta o formulário em vez de remover
    optionForm.style.display = 'none';
        
}

function validateMultipleChoice() {
    const optionsContainer = document.getElementById('options-container');

    // Se não houver container, não é um formulário de múltipla escolha
    if (!optionsContainer) {
        return true;
    }
    
    const visibleForms = optionsContainer.querySelectorAll('.option-form:not([style*="display: none"])');
    
    const correctCheckboxes = Array.from(visibleForms).filter(form => {
        const cb = form.querySelector('input[name$="-is_correct"]');
        return cb && cb.checked;
    });
        
    if (correctCheckboxes.length === 0) {        
        optionsAlertError('Selecione a alternativa correta.');
        return false;
    } else if (correctCheckboxes.length > 1) {
        optionsAlertError('Apenas uma alternativa pode ser correta.');
        return false;
    }
    
    return true;
}

// Intercepta a requisição HTMX ANTES de enviar
document.addEventListener('htmx:beforeRequest', function(evt) {
   
    const element = evt.detail.elt; // Elemento que disparou
    
    // Valida APENAS se for o botão de submit do formulário
    if (element.id === 'btnSubmit') {
        if (!validateMultipleChoice()) {
            evt.preventDefault();
        }
    }
});