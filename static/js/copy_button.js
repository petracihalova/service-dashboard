document.addEventListener('DOMContentLoaded', function () {
    var copyButton = document.getElementById("copy_button");
    var contentToCopy = document.getElementById("releaseNotes");

    if (!copyButton || !contentToCopy) {
        return; // Elements not found, exit gracefully
    }

    // Check if already initialized to prevent duplicate listeners
    if (copyButton.hasAttribute('data-initialized')) {
        return;
    }
    copyButton.setAttribute('data-initialized', 'true');

    copyButton.addEventListener("click", async function () {
        try {
            var clipboardItem = new ClipboardItem({
                'text/html': new Blob([contentToCopy.innerHTML], { type: 'text/html' })
            });

            await navigator.clipboard.write([clipboardItem]);

            // Show success toast using global function from layout.js
            showToast('Release notes copied to clipboard successfully!', 'success');

        } catch (err) {
            // Show error toast using global function from layout.js
            showToast('Failed to copy to clipboard. Please try selecting and copying the text manually.', 'error');
        }
    });
});
