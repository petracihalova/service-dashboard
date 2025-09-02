document.addEventListener('DOMContentLoaded', function () {
    // Function to create a spinner element
    function createSpinner() {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        return spinner;
    }

    // Find all buttons with class="update-deployment-btn" or id="update_deployment_button"
    var updateDeploymentButtons = document.querySelectorAll('#update_deployment_button');

    // Add event listener to each button
    updateDeploymentButtons.forEach(function(button) {
        button.addEventListener("click", function (e) {
            if (this.dataset.clicked) {
                return;
            }
            this.dataset.clicked = "true";

            // Store original dimensions before changing content
            var originalWidth = this.offsetWidth;
            var originalHeight = this.offsetHeight;

            this.disabled = true;

            // Set fixed dimensions to prevent resizing
            this.style.width = originalWidth + "px";
            this.style.height = originalHeight + "px";
            this.style.minWidth = originalWidth + "px";
            this.style.minHeight = originalHeight + "px";

            // Set display flex to center spinner
            this.style.display = "flex";
            this.style.justifyContent = "center";
            this.style.alignItems = "center";

            // Clear content and add spinner
            this.textContent = "";
            this.appendChild(createSpinner());

            window.location.href = this.dataset.url;
        });
    });
});
