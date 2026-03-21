/* MediSync - Analytics JS */
(function () {
    // --- Load Expired ---
    async function loadExpired() {
        try {
            var res = await fetch(window.API_BASE + '/api/analytics/expired');
            var items = await res.json();
            document.getElementById('expiredCount').textContent = items.length;
            var tbody = document.getElementById('expiredBody');
            if (!items.length) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No expired medicines</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(function (m) {
                var days = m.days_remaining !== null ? m.days_remaining : '-';
                return '<tr><td>' + escapeHtml(m.article_name) + '</td><td>' + escapeHtml(m.category) +
                    '</td><td>' + escapeHtml(m.unit_of_measurement) + '</td><td>' + m.quantity +
                    '</td><td>' + formatDate(m.expiration_date) + '</td><td style="color:var(--coral);font-weight:700;">' + days +
                    '</td><td>' + statusBadge(m.status) + '</td></tr>';
            }).join('');
        } catch (e) { /* ignore */ }
    }

    // --- Load About to Expire ---
    async function loadExpiring() {
        try {
            var res = await fetch(window.API_BASE + '/api/analytics/expiring');
            var items = await res.json();
            document.getElementById('expiringCount').textContent = items.length;
            var tbody = document.getElementById('expiringBody');
            if (!items.length) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No medicines about to expire</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(function (m) {
                var days = m.days_remaining !== null ? m.days_remaining : '-';
                return '<tr><td>' + escapeHtml(m.article_name) + '</td><td>' + escapeHtml(m.category) +
                    '</td><td>' + escapeHtml(m.unit_of_measurement) + '</td><td>' + m.quantity +
                    '</td><td>' + formatDate(m.expiration_date) + '</td><td style="color:var(--yellow);font-weight:700;">' + days +
                    '</td><td>' + statusBadge(m.status) + '</td></tr>';
            }).join('');
        } catch (e) { /* ignore */ }
    }

    // --- Pie Chart ---
    async function loadChart() {
        try {
            var res = await fetch(window.API_BASE + '/api/analytics/status-chart');
            var data = await res.json();
            drawPieChart(data);
        } catch (e) { /* ignore */ }
    }

    function drawPieChart(data) {
        var canvas = document.getElementById('statusChart');
        var ctx = canvas.getContext('2d');
        var total = data.values.reduce(function (a, b) { return a + b; }, 0);
        var cx = canvas.width / 2;
        var cy = canvas.height / 2;
        var radius = Math.min(cx, cy) - 10;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (total === 0) {
            ctx.beginPath();
            ctx.arc(cx, cy, radius, 0, Math.PI * 2);
            ctx.fillStyle = '#E2E2EA';
            ctx.fill();
            ctx.fillStyle = '#9999AD';
            ctx.font = '600 14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No data', cx, cy);
            return;
        }

        var startAngle = -Math.PI / 2;
        data.values.forEach(function (val, i) {
            if (val === 0) return;
            var sliceAngle = (val / total) * Math.PI * 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = data.colors[i];
            ctx.fill();

            // Label
            var midAngle = startAngle + sliceAngle / 2;
            var labelR = radius * 0.65;
            var lx = cx + labelR * Math.cos(midAngle);
            var ly = cy + labelR * Math.sin(midAngle);
            var pct = Math.round((val / total) * 100);
            if (pct > 5) {
                ctx.fillStyle = '#fff';
                ctx.font = '700 13px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(pct + '%', lx, ly);
            }

            startAngle += sliceAngle;
        });

        // Inner circle (donut)
        ctx.beginPath();
        ctx.arc(cx, cy, radius * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.fillStyle = '#2B2B43';
        ctx.font = '800 20px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(total, cx, cy - 8);
        ctx.font = '500 11px Inter, sans-serif';
        ctx.fillStyle = '#9999AD';
        ctx.fillText('Total', cx, cy + 12);

        // Legend
        var legend = document.getElementById('chartLegend');
        legend.innerHTML = data.labels.map(function (label, i) {
            return '<div class="legend-item"><div class="legend-color" style="background:' + data.colors[i] +
                '"></div>' + label + '<span class="legend-value">(' + data.values[i] + ')</span></div>';
        }).join('');
    }

    loadExpired();
    loadExpiring();
    loadChart();
})();
