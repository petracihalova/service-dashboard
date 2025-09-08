/**
 * Release Notes Selection functionality
 */

// Global variables to store data - avoid redeclaration errors
if (typeof prData === 'undefined') {
    var prData = [];
}
if (typeof deploymentData === 'undefined') {
    var deploymentData = {};
}

document.addEventListener('DOMContentLoaded', function() {
    try {
        // Get data from JSON script tags
        prData = JSON.parse(document.getElementById('pr-data').textContent);
        deploymentData = JSON.parse(document.getElementById('deployment-data').textContent);

        const radioInputs = document.querySelectorAll('input[name="up_to_pr"]');
        const prItems = document.querySelectorAll('.pr-item');

        // Add event listeners to radio buttons
        radioInputs.forEach(radio => {
            radio.addEventListener('change', function() {
                updateSelection(parseInt(this.value));
            });
        });

        // Initialize with the default selection (last PR)
        const defaultChecked = document.querySelector('input[name="up_to_pr"]:checked');
        if (defaultChecked) {
            updateSelection(parseInt(defaultChecked.value));
        }

        // Add event listener for copy button
        const copyButton = document.querySelector('[onclick="copyTargetCommit()"]');
        if (copyButton) {
            copyButton.removeAttribute('onclick');
            copyButton.addEventListener('click', copyTargetCommit);
        }
    } catch (error) {
        console.error('Error initializing PR selection:', error);
    }
});

function updateSelection(selectedPrNumber) {
    try {
        // Find the index of the selected PR
        const selectedIndex = prData.findIndex(pr => pr.number === selectedPrNumber);

        if (selectedIndex === -1) return;

        // Update visual highlighting
        const prItems = document.querySelectorAll('.pr-item');
        prItems.forEach((item, index) => {
            if (index <= selectedIndex) {
                item.classList.add('bg-light', 'border-primary');
                item.classList.remove('bg-white');
            } else {
                item.classList.remove('bg-light', 'border-primary');
                item.classList.add('bg-white');
            }
        });

        // Update the summary information
        const selectedCount = selectedIndex + 1;
        document.getElementById('selected-count').textContent = selectedCount;
        document.getElementById('pr-count').textContent = selectedCount;

        // Update target commit
        const selectedPr = prData[selectedIndex];
        const targetCommit = selectedPr.merge_commit_sha ? selectedPr.merge_commit_sha.substring(0, 7) : deploymentData.commit_stage.substring(0, 7);
        document.getElementById('target-commit').textContent = targetCommit;

        // Update diff link
        const diffLink = `${deploymentData.repo_link}/compare/${deploymentData.commit_prod}...${selectedPr.merge_commit_sha || deploymentData.commit_stage}`;
        document.getElementById('diff-link').setAttribute('href', diffLink);
    } catch (error) {
        console.error('Error in updateSelection:', error);
    }
}

function copyTargetCommit() {
    const targetCommit = document.getElementById('target-commit').textContent;
    navigator.clipboard.writeText(targetCommit).then(() => {
        // Show a brief success indication
        const button = event.target;
        const originalText = button.innerHTML;
        button.innerHTML = '✓';
        button.classList.add('btn-success');
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
        }, 1000);
    });
}
