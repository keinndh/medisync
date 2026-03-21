/* MediSync - Login Page JS */
window.API_BASE = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
  ? 'http://127.0.0.1:5000'
  : 'https://medisync-yvp7.onrender.com';

(function () {
    var form = document.getElementById('loginForm');
    var errEl = document.getElementById('loginError');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        errEl.style.display = 'none';

        var username = document.getElementById('username').value.trim();
        var password = document.getElementById('password').value;

        if (!username || !password) {
            errEl.textContent = 'Please enter both username and password.';
            errEl.style.display = 'block';
            return;
        }

        var btn = document.getElementById('loginBtn');
        btn.disabled = true;
        btn.textContent = 'Signing in...';

        try {
            var res = await fetch(window.API_BASE + '/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username, password: password })
            });
            var data = await res.json();
            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                errEl.textContent = data.error || 'Invalid credentials.';
                errEl.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        } catch (err) {
            errEl.textContent = 'Connection error. Please try again.';
            errEl.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });
})();
