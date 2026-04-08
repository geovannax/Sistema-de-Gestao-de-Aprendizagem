document.addEventListener("DOMContentLoaded", function () {
  const input = document.getElementById("id_shared_with_autocomplete");
  if (!input) return;

  const container = document.createElement("div");
  container.className = "sharing-autocomplete-container";
  input.parentNode.insertBefore(container, input);
  input.style.display = "none";

  const tagsContainer = document.createElement("div");
  tagsContainer.className = "sharing-tags-container";
  container.appendChild(tagsContainer);

  const inputWrapper = document.createElement("div");
  inputWrapper.className = "sharing-input-wrapper";
  const newInput = document.createElement("input");
  newInput.type = "text";
  newInput.className = "form-control py-2";
  newInput.placeholder = input.placeholder;
  inputWrapper.appendChild(newInput);
  container.appendChild(inputWrapper);

  const suggestionsBox = document.createElement("div");
  suggestionsBox.className = "sharing-suggestions";
  container.appendChild(suggestionsBox);

  let selectedUsers = new Map();

  newInput.addEventListener("input", async function () {
    const query = this.value.trim();
    if (query.length < 2) {
      suggestionsBox.innerHTML = "";
      return;
    }

    try {
      const response = await fetch(
        `/group/api/users/autocomplete/?q=${encodeURIComponent(query)}`,
      );
      const data = await response.json();

      suggestionsBox.innerHTML = "";
      data.results.forEach((user) => {
        if (!selectedUsers.has(user.id)) {
          const suggestion = document.createElement("div");
          suggestion.className = "sharing-suggestion";
          suggestion.innerHTML = `
            <div class="suggestion-name">${user.text}</div>
            <div class="suggestion-email">${user.email}</div>
          `;
          suggestion.addEventListener("click", function () {
            selectedUsers.set(user.id, user);
            renderTags();
            updateHiddenInput();
            newInput.value = "";
            suggestionsBox.innerHTML = "";
          });
          suggestionsBox.appendChild(suggestion);
        }
      });
    } catch (error) {
      console.error("Erro:", error);
    }
  });

  function renderTags() {
    tagsContainer.innerHTML = "";
    selectedUsers.forEach((user, id) => {
      const tag = document.createElement("span");
      tag.className = "sharing-tag";
      tag.innerHTML = `${user.text} <button type="button" class="remove-tag" data-user-id="${id}">×</button>`;
      tagsContainer.appendChild(tag);
    });
  }

  function updateHiddenInput() {
    const ids = Array.from(selectedUsers.keys()).join(",");
    input.value = ids;
  }

  tagsContainer.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-tag")) {
      e.preventDefault();
      selectedUsers.delete(parseInt(e.target.dataset.userId));
      renderTags();
      updateHiddenInput();
    }
  });

  renderTags();
});
