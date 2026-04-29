document.addEventListener("DOMContentLoaded", function () {

    function calculateProgress(e) {

        const form = e.currentTarget;

        const progressBar = document.getElementById("progressBar");
        const progressText = document.getElementById("progressText");

        const fields = form.querySelectorAll("input, textarea, select");

        let total = 0;
        let filled = 0;

        const handledRadioGroups = new Set();

        fields.forEach(field => {

            if (
                field.type === "hidden" ||
                field.type === "submit" ||
                field.type === "button" ||
                field.name === "csrfmiddlewaretoken" ||
                field.name === "invalidCheck"
            ) return;

            // RADIO (1 por grupo)
            if (field.type === "radio") {

                if (handledRadioGroups.has(field.name)) return;

                handledRadioGroups.add(field.name);
                total++;

                const checked = form.querySelector(`input[name="${field.name}"]:checked`);
                if (checked) filled++;

                return;
            }

            // CHECKBOX
            if (field.type === "checkbox") {
                total++;
                if (field.checked) filled++;
                return;
            }

            // INPUT NORMAL
            total++;

            if (field.value && field.value.trim() !== "") {
                filled++;
            }
        });

        const percent = total === 0 ? 0 : Math.round((filled / total) * 100);

        progressBar.style.width = percent + "%";
        progressText.innerText = percent + "%";

    }

    const submitBtn = document.getElementById("btnSubmit");

    const form = submitBtn?.closest("form");

    form.addEventListener("input", calculateProgress);
    form.addEventListener("change", calculateProgress);

    calculateProgress({ currentTarget: form }); 
});