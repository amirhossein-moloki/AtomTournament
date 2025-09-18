document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const usernameInput = document.getElementById('username');
            const passwordInput = document.getElementById('password');

            const username = usernameInput.value;
            const password = passwordInput.value;

            try {
                const response = await fetch('/auth/jwt/create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                });

                if (response.ok) {
                    const data = await response.json();
                    const accessToken = data.access;

                    if (accessToken) {
                        localStorage.setItem('accessToken', accessToken);
                        // Redirect to the dashboard
                        window.location.href = 'index.html';
                    } else {
                        alert('Login successful, but no access token received.');
                    }
                } else {
                    // Handle login failure
                    const errorData = await response.json();
                    const errorMessage = Object.values(errorData).join('\n');
                    alert(`Login failed:\n${errorMessage}`);
                }
            } catch (error) {
                console.error('Error during login:', error);
                alert('An error occurred during login. Please try again.');
            }
        });
    }
});
