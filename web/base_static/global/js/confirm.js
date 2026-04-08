document.addEventListener("DOMContentLoaded", function () {
  const confirmInput = document.getElementById("confirmInput");
  const confirmBtn = document.getElementById("confirmBtn");
  const confirmForm = document.getElementById("confirmForm");

  confirmInput.addEventListener("input", function () {
    if (this.value === clasName.trim()) {
      confirmBtn.disabled = false;
    } else {
      confirmBtn.disabled = true;
    }
  });

  confirmForm.addEventListener("submit", function (e) {
    if (confirmInput.value !== clasName.trim()) {
      e.preventDefault();
      alert("Digite o nome correto");
    }
  });
});
