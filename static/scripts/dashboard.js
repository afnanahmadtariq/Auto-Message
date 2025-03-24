function showLoading(text) {
    document.getElementById("loading-overlay").style.display = "flex";
    document.getElementById("loading-text").innerText = text;
    document.querySelectorAll("button").forEach(btn => btn.disabled = true);
}

function hideLoading() {
    document.getElementById("loading-overlay").style.display = "none";
    document.querySelectorAll("button").forEach(btn => btn.disabled = false);
}

function selectContact(name, phone) {
    document.getElementById("phone").value = phone;
}

function searchContacts() {
    const query = document.getElementById("search").value;
    showLoading("Searching contacts...");
    fetch("/whatsapp/search_contacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            const results = document.getElementById("search-results");
            results.innerHTML = "";
            if (data.contacts) {
                data.contacts.forEach(contact => {
                    const li = document.createElement("li");
                    li.innerText = contact.name;
                    li.onclick = () => selectContact(contact.name, contact.phone);
                    results.appendChild(li);
                });
            } else alert(data.error);
        })
        .catch(error => { hideLoading(); console.error("Error:", error); });
}

document.getElementById("messageForm").addEventListener("submit", function (event) {
    event.preventDefault();
    const phone = document.getElementById("phone").value;
    const message = document.getElementById("message").value;
    const repeat = document.getElementById("repeat").value;
    showLoading("Sending message...");
    fetch("/whatsapp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, message, repeat })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            alert(data.status || data.error);
        })
        .catch(error => { hideLoading(); console.error("Error:", error); });
});

function logout() {
    showLoading("Logging out...");
    window.location.href = "/auth/logout";
}