// Toggle password visibility
const togglePassword = document.getElementById('togglePassword');
const passwordInput = document.getElementById('id_password');

togglePassword.addEventListener('click', function (e) {
    e.preventDefault();
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
    this.querySelector('i').className = type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
});

// Form submission
document.getElementById('loginForm').addEventListener('submit', function (e) {

    const btn = this.querySelector('button[type="submit"]');

    // Show loading
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Entrando...';

});