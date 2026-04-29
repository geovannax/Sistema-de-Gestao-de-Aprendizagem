function showNotificationPopup(tag, message) {
  // Determina tempo de exibição conforme o tipo
  const sleep = (tag === "Error" || tag === "Warning") ? 15000 : 5000;

  // Define a classe de cor baseada no tipo
  const colorMap = {
    "Error": "danger",
    "Warning": "warning",
    "Success": "success",
    "Info": "info"
  };
  const toastColor = colorMap[tag] || "info";

  // Cria o HTML da toast
  const toastHTML = `
    <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-header bg-${toastColor} text-white">
        <strong class="me-auto">${tag}</strong>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body bg-white rounded-5">
        ${message.replaceAll(". ", ".<br/>")}
      </div>
    </div>
  `;

  // Cria container se não existir
  let toastContainer = document.getElementById("toast-container");
  // Adiciona a toast ao container
  toastContainer.insertAdjacentHTML("beforeend", toastHTML);

  // Pega a últ toast criada
  const toastElement = toastContainer.lastElementChild;
  const toast = new bootstrap.Toast(toastElement, {
    autohide: true,
    delay: sleep
  });

  // Remove o elemento após desaparecer
  toastElement.addEventListener("hidden.bs.toast", () => {
    toastElement.remove();
  });

  toast.show();
}