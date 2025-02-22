document.addEventListener('DOMContentLoaded', function () {
    // Function to create a spinner element
    function createSpinner() {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.style.marginRight = "10px";
        return spinner;
    }

    var updateButton = document.getElementById("update_button");
    // Add event listener to the button click event
    updateButton.addEventListener("click", function (e) {
        this.disabled = true;
        this.textContent = "";
        this.appendChild(createSpinner());
        this.appendChild(document.createTextNode("Loading"));

        window.location.href = this.dataset.url;
    });
});
