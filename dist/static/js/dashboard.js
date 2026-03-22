/* MediSync - Dashboard JS */
(function () {
    // --- Carousel ---
    var currentSlide = 0;
    var totalSlides = 5;
    var track = document.getElementById('carouselTrack');
    var dots = document.querySelectorAll('.carousel-dot');

    function goToSlide(index) {
        if (index < 0) index = totalSlides - 1;
        if (index >= totalSlides) index = 0;
        currentSlide = index;
        track.style.transform = 'translateX(-' + (currentSlide * 100) + '%)';
        dots.forEach(function (d, i) {
            d.classList.toggle('active', i === currentSlide);
        });
    }

    document.getElementById('carouselPrev').addEventListener('click', function () { goToSlide(currentSlide - 1); });
    document.getElementById('carouselNext').addEventListener('click', function () { goToSlide(currentSlide + 1); });
    dots.forEach(function (dot) {
        dot.addEventListener('click', function () { goToSlide(parseInt(this.dataset.index)); });
    });

    // Auto-slide
    var autoSlide = setInterval(function () { goToSlide(currentSlide + 1); }, 5000);
    var wrapper = document.querySelector('.carousel-wrapper');
    if (wrapper) {
        wrapper.addEventListener('mouseenter', function () { clearInterval(autoSlide); });
        wrapper.addEventListener('mouseleave', function () {
            autoSlide = setInterval(function () { goToSlide(currentSlide + 1); }, 5000);
        });
    }

    // --- Load Stats ---
    async function loadStats() {
        try {
            var res = await fetch(window.API_BASE + '/api/dashboard/stats');
            var data = await res.json();
            document.getElementById('statTotal').textContent = data.total_items;
            document.getElementById('statExpiring').textContent = data.about_to_expire;
            document.getElementById('statExpired').textContent = data.expired;
            document.getElementById('statDispensed').textContent = data.dispensed;
            document.getElementById('statDiscarded').textContent = data.discarded;
        } catch (e) { /* ignore */ }
    }

    // --- Block Click -> Popup ---
    document.querySelectorAll('.stat-block').forEach(function (block) {
        block.addEventListener('click', function () {
            var type = this.dataset.block;
            showBlockPopup(type);
        });
    });

    async function showBlockPopup(type) {
        var titles = {
            total: 'Total Items', about_to_expire: 'About to Expire',
            expired: 'Expired Items', dispensed: 'Dispensed Items', discarded: 'Discarded Items'
        };
        document.getElementById('blockModalTitle').textContent = titles[type] || 'Items';

        try {
            var res = await fetch(window.API_BASE + '/api/dashboard/block/' + type);
            var items = await res.json();
            var thead = document.getElementById('blockTableHead');
            var tbody = document.getElementById('blockTableBody');

            if (type === 'dispensed') {
                thead.innerHTML = '<tr><th>Dispenser</th><th>Medicine</th><th>Qty</th><th>Recipient</th><th>Center</th><th>Date</th></tr>';
                tbody.innerHTML = items.length ? items.map(function (d) {
                    return '<tr><td>' + escapeHtml(d.dispenser_name) + '</td><td>' + escapeHtml(d.medicine_name) +
                        '</td><td>' + d.quantity_dispensed + '</td><td>' + escapeHtml(d.recipient_name) +
                        '</td><td>' + escapeHtml(d.center_name) + '</td><td>' + formatDateTime(d.date_time) + '</td></tr>';
                }).join('') : '<tr class="empty-row"><td colspan="6">No items found</td></tr>';
            } else {
                thead.innerHTML = '<tr><th>Stock #</th><th>Article</th><th>Unit</th><th>Qty</th><th>Generic Name</th><th>Exp. Date</th><th>Status</th></tr>';
                tbody.innerHTML = items.length ? items.map(function (m) {
                    return '<tr><td>' + escapeHtml(m.stock_number) + '</td><td>' + escapeHtml(m.article_name) +
                        '</td><td>' + escapeHtml(m.unit_of_measurement) + '</td><td>' + m.quantity +
                        '</td><td>' + escapeHtml(m.category) + '</td><td>' + formatDate(m.expiration_date) +
                        '</td><td>' + statusBadge(m.status) + '</td></tr>';
                }).join('') : '<tr class="empty-row"><td colspan="7">No items found</td></tr>';
            }
            openModal('blockModal');
        } catch (e) { showToast('Failed to load data', 'error'); }
    }

    // --- Recently Added Table ---
    async function loadRecent() {
        try {
            var res = await fetch(window.API_BASE + '/api/dashboard/recent');
            var items = await res.json();
            var tbody = document.getElementById('recentBody');
            if (!items.length) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No recent medicines</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(function (m) {
                var batchStatus = m.is_restock ? '<span class="badge badge-edited">Restocked</span>' : (m.is_new_batch ? '<span class="badge badge-created">Created</span>' : '<span class="badge badge-edited">Edited</span>');
                return '<tr><td>' + escapeHtml(m.stock_number) + '</td><td>' + escapeHtml(m.article_name) +
                    '</td><td>' + escapeHtml(m.description_dosage) + '</td><td>' + escapeHtml(m.unit_of_measurement) +
                    '</td><td>' + m.quantity +
                    '</td><td>' + escapeHtml(m.category) + '</td><td>' + formatDateTime(m.date_added) +
                    '</td><td>' + batchStatus + '</td></tr>';
            }).join('');
        } catch (e) {
            document.getElementById('recentBody').innerHTML = '<tr class="empty-row"><td colspan="9">Failed to load data</td></tr>';
        }
    }

    loadStats();
    loadRecent();
})();
