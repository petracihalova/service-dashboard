document.addEventListener('DOMContentLoaded', function () {
    var updateButton = document.getElementById("update_button");

    // Function to set Update button text to "Loading" and get the spinner visible
    function setLoadingState() {
        updateButton.textContent = "";
        updateButton.appendChild(createSpinner());
        updateButton.appendChild(document.createTextNode("Loading"));
        updateButton.disabled = true;

        // Construct the URL with the parameter and navigate to it
        var url = "open_pr?reload_data=true";
        window.location.href = url;
    }

    // Function to create a spinner element
    function createSpinner() {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.style.marginRight = "10px";
        return spinner;
    }

    // Attach the setLoadingState function to the button click event
    updateButton.addEventListener("click", () => {
        setLoadingState();
    });
});