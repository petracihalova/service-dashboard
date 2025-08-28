
const createButton = document.getElementById("create_jira_ticket");
const repoName = createButton.getAttribute("data-repo-name");

createButton.addEventListener("click", function (event) {
    event.preventDefault();

    createButton.disabled = true;

    const dataToSend = {
        repo_name: repoName
    };
    console.log("Handler online");

    fetch("/jira-tickets/create_jira_ticket", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(dataToSend)
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById("flash-messages").innerHTML =
                `<div class="flash-message alert alert-success alert-dismissible fade show">
                    ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
        })
        .catch(error => console.error("Err:", error))
        .finally(() => {
            createButton.disabled = false;
        });
});
