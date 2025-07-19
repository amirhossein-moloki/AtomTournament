document.addEventListener("DOMContentLoaded", () => {
    // Registration Form
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(registerForm);
            const formData = new FormData(registerForm);
            const data = Object.fromEntries(formData.entries());

            if (data.password.length < 8) {
                displayError(registerForm, "Password must be at least 8 characters long.");
                return;
            }

            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/auth/users/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                alert("Registration successful!");
                window.location.href = "/login.html";
            } else {
                const errorData = await response.json();
                for (const key in errorData) {
                    displayError(registerForm, `${key}: ${errorData[key]}`);
                }
            }
        });
    }

    // Login Form
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(loginForm);
            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/auth/jwt/create/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                const { access } = await response.json();
                localStorage.setItem("accessToken", access);
                alert("Login successful!");
                window.location.href = "/index.html";
            } else {
                displayError(loginForm, "Invalid credentials.");
            }
        });
    }

    // OTP Login
    const sendOtpBtn = document.getElementById("send-otp-btn");
    const otpLoginForm = document.getElementById("otp-login-form");
    const otpVerifyForm = document.getElementById("otp-verify-form");
    if (sendOtpBtn) {
        sendOtpBtn.addEventListener("click", async () => {
            clearErrors(otpLoginForm);
            const email = document.getElementById("email-otp").value;
            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/api/users/send_otp/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({ email }),
            });

            if (response.ok) {
                otpLoginForm.style.display = "none";
                otpVerifyForm.style.display = "block";
            } else {
                displayError(otpLoginForm, "Failed to send OTP.");
            }
        });
    }

    if (otpVerifyForm) {
        otpVerifyForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(otpVerifyForm);
            const email = document.getElementById("email-otp").value;
            const otp = document.getElementById("otp").value;

            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/api/users/verify_otp/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({ email, otp }),
            });

            if (response.ok) {
                const { access } = await response.json();
                localStorage.setItem("accessToken", access);
                alert("Login successful!");
                window.location.href = "/index.html";
            } else {
                displayError(otpVerifyForm, "OTP verification failed.");
            }
        });
    }

    // Password Reset
    const resetPasswordForm = document.getElementById("reset-password-form");
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(resetPasswordForm);
            const formData = new FormData(resetPasswordForm);
            const data = Object.fromEntries(formData.entries());

            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/auth/users/reset_password/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                alert("Password reset link sent to your email.");
            } else {
                displayError(resetPasswordForm, "Failed to send password reset link.");
            }
        });
    }

    const resetPasswordConfirmForm = document.getElementById("reset-password-confirm-form");
    if (resetPasswordConfirmForm) {
        resetPasswordConfirmForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(resetPasswordConfirmForm);
            const formData = new FormData(resetPasswordConfirmForm);
            const data = Object.fromEntries(formData.entries());

            if (data.new_password.length < 8) {
                displayError(resetPasswordConfirmForm, "Password must be at least 8 characters long.");
                return;
            }

            const csrftoken = getCookie('csrftoken');
            const response = await fetch("/auth/users/reset_password_confirm/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                alert("Password reset successful!");
                window.location.href = "/login.html";
            } else {
                const errorData = await response.json();
                for (const key in errorData) {
                    displayError(resetPasswordConfirmForm, `${key}: ${errorData[key]}`);
                }
            }
        });
    }
});
