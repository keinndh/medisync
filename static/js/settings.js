/* MediSync - Settings JS */
(function () {
    // --- Load current profile ---
    async function loadProfile() {
        try {
            var res = await fetch('/api/me');
            var user = await res.json();
            document.getElementById('settingsName').value = user.full_name || '';
            document.getElementById('settingsUsername').value = user.username || '';
            if (user.profile_picture) {
                document.getElementById('settingsProfilePic').innerHTML = '<img src="' + user.profile_picture + '" alt="Profile">';
            }
        } catch (e) { /* ignore */ }
    }

    // --- Save profile ---
    document.getElementById('profileForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        var pw = document.getElementById('settingsPassword').value;
        var pwConfirm = document.getElementById('settingsPasswordConfirm').value;
        if (pw && pw !== pwConfirm) {
            showToast('Passwords do not match.', 'error');
            return;
        }
        var payload = {
            full_name: document.getElementById('settingsName').value.trim(),
            username: document.getElementById('settingsUsername').value.trim()
        };
        if (pw) payload.password = pw;

        try {
            var res = await fetch('/api/settings/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            if (res.ok) {
                showToast('Profile updated successfully.');
                document.getElementById('settingsPassword').value = '';
                document.getElementById('settingsPasswordConfirm').value = '';
                // Update header
                var nameEl = document.getElementById('headerUserName');
                if (nameEl) nameEl.textContent = data.full_name || data.username;
            } else { showToast(data.error || 'Failed to update.', 'error'); }
        } catch (e) { showToast('Connection error.', 'error'); }
    });

    // --- Upload profile picture ---
    document.getElementById('profilePicInput').addEventListener('change', async function () {
        var file = this.files[0];
        if (!file) return;
        var fd = new FormData();
        fd.append('picture', file);
        try {
            var res = await fetch('/api/settings/picture', { method: 'POST', body: fd });
            var data = await res.json();
            if (res.ok) {
                showToast('Profile picture updated.');
                document.getElementById('settingsProfilePic').innerHTML = '<img src="' + data.profile_picture + '" alt="Profile">';
                var headerPic = document.getElementById('headerProfilePic');
                if (headerPic) headerPic.innerHTML = '<img src="' + data.profile_picture + '" alt="Profile">';
            } else { showToast(data.error || 'Upload failed.', 'error'); }
        } catch (e) { showToast('Connection error.', 'error'); }
    });

    loadProfile();
})();
