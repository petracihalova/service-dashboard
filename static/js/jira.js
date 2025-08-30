
(function() {
    // Prevent duplicate declarations when script loads multiple times
    if (typeof window.jiraScriptLoaded !== 'undefined') {
        return;
    }
    window.jiraScriptLoaded = true;

    // No custom CSS needed - using Bootstrap's built-in spinner-border class

    const createButton = document.getElementById("create_jira_ticket");
    if (!createButton) {
        return; // Exit early if button doesn't exist
    }

    const repoName = createButton.getAttribute("data-repo-name");

    createButton.addEventListener("click", function (event) {
        event.preventDefault();

        // Show loading state with spinner
        const originalHtml = createButton.innerHTML;
        createButton.disabled = true;
        createButton.innerHTML = '<div class="spinner-border spinner-border-sm me-1" role="status"></div> Creating...';

        const dataToSend = {
            repo_name: repoName
        };

        fetch("/jira-tickets/create_jira_ticket", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(dataToSend)
        })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    // Extract ticket URL from HTML message
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = data.message;
                    const linkElement = tempDiv.querySelector('a[href]');

                    if (linkElement && linkElement.href) {
                        // Show success modal with ticket link
                        const modal = new bootstrap.Modal(document.getElementById('jiraSuccessModal'));
                        const ticketLink = document.getElementById('jiraTicketLink');
                        const ticketText = document.getElementById('jiraTicketText');

                        ticketLink.href = linkElement.href;
                        ticketText.textContent = `Open JIRA Ticket (${linkElement.textContent})`;

                        modal.show();
                    } else {
                        // Show success toast if no URL found in message
                        showToast('JIRA ticket created successfully!', 'success');
                    }
                } else {
                    // Show success toast as fallback
                    showToast('JIRA ticket created successfully!', 'success');
                }
            })
            .catch(error => {
                // Show error toast
                showToast('Failed to create JIRA ticket. Please try again.', 'error');
            })
            .finally(() => {
                // Reset button to original state
                createButton.disabled = false;
                createButton.innerHTML = originalHtml;
            });
    });
})();
