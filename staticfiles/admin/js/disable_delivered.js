document.addEventListener("DOMContentLoaded", function () {
    // Loop through each row in the table
    document.querySelectorAll("tr").forEach(row => {

        const statusSelect = row.querySelector("select[name$='-status']");
        const checkbox = row.querySelector("input.action-select");

        if (statusSelect && checkbox) {
            if (statusSelect.value === "delivered") {

                // Disable bulk action checkbox
                checkbox.disabled = true;

                // Dim the row visually
                row.style.opacity = "0.6";

                // Disable interactions (but allow clicking order link)
                row.style.pointerEvents = "none";

                // Re-enable order link only
                const link = row.querySelector("th > a");
                if (link) {
                    link.style.pointerEvents = "auto";
                }
            }
        }
    });
});