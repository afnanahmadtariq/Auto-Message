function checkLogin() {
    console.log("Checking login status...");
    fetch("/whatsapp/check_login")
        .then(response => response.json())
        .then(data => {
            console.log("Login status:", data);
            if (data.logged_in) {
                window.location.href = "/whatsapp/dashboard";
            } else {
                setTimeout(checkLogin, 1000); // Poll every 3 seconds
            }
        })
        .catch(error => {
            console.error("Error checking login status:", error);
        });
}

checkLogin();