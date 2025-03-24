function showLoading(text) {
    document.getElementById("loading-overlay").style.display = "flex";
    document.getElementById("loading-text").innerText = text;
    document.querySelectorAll("button").forEach(btn => btn.disabled = true);
}

function hideLoading() {
    document.getElementById("loading-overlay").style.display = "none";
    document.querySelectorAll("button").forEach(btn => btn.disabled = false);
}

function loginWithGoogle() {
    showLoading("Redirecting to Google...");
    fetch("/auth/login/google", { method: "POST", headers: { "Content-Type": "application/json" } })
        .then(response => response.json())
        .then(data => {
            if (data.redirect) window.location.href = data.redirect;
            else { hideLoading(); alert(data.error || "Login failed."); }
        })
        .catch(error => { hideLoading(); console.error("Error:", error); alert("Login error."); });
}

document.getElementById("2faLoginForm").addEventListener("submit", function (event) {
    event.preventDefault();
    const identifier = document.getElementById("2fa_identifier").value;
    const token = document.getElementById("2fa_token").value;
    showLoading("Verifying 2FA token...");
    fetch("/auth/login/2fa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, token })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) alert(data.error);
            else {
                showLoading("Loading Whatsapp...");
                window.location.href = "/whatsapp/waiting";
            }
        })
        .catch(error => { hideLoading(); console.error("Error:", error); alert("Login error."); });
});