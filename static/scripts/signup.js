function showLoading(text) {
    document.getElementById("loading-overlay").style.display = "flex";
    document.getElementById("loading-text").innerText = text;
    document.querySelectorAll("button").forEach(btn => btn.disabled = true);
}

function hideLoading() {
    document.getElementById("loading-overlay").style.display = "none";
    document.querySelectorAll("button").forEach(btn => btn.disabled = false);
}

function signupWithGoogle() {
    showLoading("Redirecting to Google...");
    fetch("/auth/signup/google", { method: "POST", headers: { "Content-Type": "application/json" } })
        .then(response => response.json())
        .then(data => {
            if (data.redirect) window.location.href = data.redirect;
            else { hideLoading(); alert(data.error || "Signup failed."); }
        })
        .catch(error => { hideLoading(); console.error("Error:", error); alert("Signup error."); });
}

document.getElementById("2faSignupForm").addEventListener("submit", function (event) {
    event.preventDefault();
    const identifier = document.getElementById("2fa_identifier").value;
    showLoading("Generating 2FA QR code...");
    fetch("/auth/signup/2fa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) alert(data.error);
            else {
                document.getElementById("2faSetup").style.display = "block";
                document.getElementById("2faSecret").innerText = data.secret;
                document.getElementById("2faQrCode").src = `data:image/png;base64,${data.qr_code}`;
            }
        })
        .catch(error => { hideLoading(); console.error("Error:", error); alert("Signup error."); });
});

document.getElementById("2faVerifyForm").addEventListener("submit", function (event) {
    event.preventDefault();
    const token = document.getElementById("2fa_token").value;
    showLoading("Verifying 2FA token...");
    fetch("/auth/verify_2fa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) alert(data.error);
            else window.location.href = "/whatsapp/waiting";
        })
        .catch(error => { hideLoading(); console.error("Error:", error); alert("Verification error."); });
});