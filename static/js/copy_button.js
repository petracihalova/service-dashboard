document.addEventListener('DOMContentLoaded', function () {
    var copyButton = document.getElementById("copy_button");
    var contentToCopy = document.getElementById("releaseNotes");

    copyButton.addEventListener("click", async function () {
        try {
            var clipboardItem = new ClipboardItem({
                'text/html': new Blob([contentToCopy.innerHTML], { type: 'text/html' })
            });

            await navigator.clipboard.write([clipboardItem]);

        } catch (err) {
            console.error('Failed to copy content: ', err);
        }
    });
});
