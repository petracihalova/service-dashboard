/**
 * Consolidated Update Button Functionality
 * Replaces: update_button.js, update_deployment_button.js
 * Provides reusable button state management with loading spinners
 */

document.addEventListener('DOMContentLoaded', function () {
    // Function to create a spinner element
    function createSpinner() {
        const spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.style.marginRight = "10px";
        return spinner;
    }

    // Handle standard update button (#update_button)
    const updateButton = document.getElementById("update_button");
    if (updateButton) {
        updateButton.addEventListener("click", function (e) {
            e.preventDefault();

            if (this.dataset.clicked) {
                return;
            }
            this.dataset.clicked = "true";

            this.disabled = true;
            this.textContent = "";
            this.appendChild(createSpinner());
            this.appendChild(document.createTextNode("Loading"));

            // Navigate to URL from data-url attribute
            if (this.dataset.url) {
                window.location.href = this.dataset.url;
            } else {
                console.warn('No data-url attribute found for update button');
            }
        });
    }

    // Handle deployment update buttons (#update_deployment_button)
    const updateDeploymentButtons = document.querySelectorAll('#update_deployment_button');
    updateDeploymentButtons.forEach(function(button) {
        button.addEventListener("click", function (e) {
            e.preventDefault();

            if (this.dataset.clicked) {
                return;
            }
            this.dataset.clicked = "true";

            this.disabled = true;
            this.textContent = "";
            this.appendChild(createSpinner());
            this.appendChild(document.createTextNode("Loading"));

            // Navigate to URL from data-url attribute
            if (this.dataset.url) {
                window.location.href = this.dataset.url;
            } else {
                console.warn('No data-url attribute found for deployment update button');
            }
        });
    });

    // Handle generic update buttons (.update-btn)
    const genericUpdateButtons = document.querySelectorAll('.update-btn');
    genericUpdateButtons.forEach(function(button) {
        button.addEventListener("click", function (e) {
            e.preventDefault();

            if (this.dataset.clicked) {
                return;
            }
            this.dataset.clicked = "true";

            this.disabled = true;
            this.textContent = "";
            this.appendChild(createSpinner());
            this.appendChild(document.createTextNode("Loading"));

            // Navigate to URL from data-url attribute or href
            const url = this.dataset.url || this.href;
            if (url) {
                window.location.href = url;
            } else {
                console.warn('No URL found for generic update button');
            }
        });
    });
});
