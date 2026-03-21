/* MediSync - Activity Logs JS */
(function () {
    var debounce;
    var currentAction = '';

    // --- Select Elements ---
    const universalSearch = document.getElementById('logUniversalSearch');
    const filterType = document.getElementById('logFilterType');
    const searchWrapper = document.getElementById('logSearchWrapper');
    const searchInput = document.getElementById('logSearchInput');
    const medicineWrapper = document.getElementById('logMedicineWrapper');
    const medicineInput = document.getElementById('logMedicineInput');
    const medicineDropdown = document.getElementById('logMedicineDropdown');
    const dateWrapper = document.getElementById('logDateWrapper');
    const dateFrom = document.getElementById('logDateFrom');
    const dateTo = document.getElementById('logDateTo');

    // --- Tab Filters ---
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentAction = this.dataset.action;
            loadLogs();
        });
    });

    // --- Filter Type Change ---
    filterType.addEventListener('change', function() {
        const val = this.value;
        searchWrapper.style.display = 'none';
        medicineWrapper.style.display = 'none';
        dateWrapper.style.display = 'none';

        if (val === 'date_range') {
            dateWrapper.style.display = 'flex';
        } else if (val === 'medicine') {
            medicineWrapper.style.display = 'block';
        } else if (val) {
            searchWrapper.style.display = 'flex';
            searchInput.placeholder = 'Search ' + val + '...';
        }
        loadLogs();
    });

    // --- Event Listeners ---
    [universalSearch, searchInput].forEach(el => {
        el.addEventListener('input', () => {
            clearTimeout(debounce);
            debounce = setTimeout(loadLogs, 400);
        });
    });

    [dateFrom, dateTo].forEach(el => {
        el.addEventListener('change', loadLogs);
    });

    // --- Medicine Autocomplete ---
    function setupMedAutocomplete() {
        let medDebounce;
        medicineInput.addEventListener('input', function() {
            clearTimeout(medDebounce);
            const q = this.value.trim();
            if (!q) {
                medicineDropdown.classList.remove('show');
                loadLogs();
                return;
            }
            medDebounce = setTimeout(async () => {
                try {
                    const res = await fetch(window.API_BASE + '/api/medicines/search?q=' + encodeURIComponent(q));
                    const items = await res.json();
                    if (!items.length) {
                        medicineDropdown.classList.remove('show');
                        return;
                    }
                    medicineDropdown.innerHTML = items.map(item => `<div class="autocomplete-item" data-val="${escapeHtml(item)}">${escapeHtml(item)}</div>`).join('');
                    medicineDropdown.classList.add('show');
                    
                    medicineDropdown.querySelectorAll('.autocomplete-item').forEach(el => {
                        el.addEventListener('mousedown', (e) => {
                            e.preventDefault();
                            medicineInput.value = el.dataset.val;
                            medicineDropdown.classList.remove('show');
                            loadLogs();
                        });
                    });
                } catch (e) {}
            }, 200);
        });

        medicineInput.addEventListener('blur', () => {
            setTimeout(() => medicineDropdown.classList.remove('show'), 200);
        });
        
        medicineInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') loadLogs();
        });
    }
    setupMedAutocomplete();

    // --- Load Logs ---
    async function loadLogs() {
        const params = new URLSearchParams();
        if (currentAction) params.set('action', currentAction);
        
        // Universal search
        const uSearch = universalSearch.value.trim();
        if (uSearch) params.set('search', uSearch);

        // Targeted filters
        const type = filterType.value;
        if (type === 'date_range') {
            if (dateFrom.value) params.set('date_from', dateFrom.value);
            if (dateTo.value) params.set('date_to', dateTo.value);
        } else if (type === 'medicine') {
            if (medicineInput.value.trim()) params.set('medicine', medicineInput.value.trim());
        } else if (type) {
            if (searchInput.value.trim()) params.set(type, searchInput.value.trim());
        }

        try {
            const res = await fetch(window.API_BASE + '/api/logs?' + params.toString());
            const logs = await res.json();
            const tbody = document.getElementById('logsBody');
            
            if (!logs.length) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No logs found</td></tr>';
                return;
            }

            tbody.innerHTML = logs.map((l, i) => {
                // Formatting details to look "more detailed"
                let detailsHtml = escapeHtml(l.details);
                // Highlight keywords if possible
                if (l.action === 'Dispense') {
                    detailsHtml = `<span style="color:var(--primary-dark); font-weight:600;">${detailsHtml}</span>`;
                } else if (l.action === 'Delete') {
                    detailsHtml = `<span style="color:var(--coral-dark); font-weight:500;">${detailsHtml}</span>`;
                }

                return `<tr>
                    <td style="color:var(--text-muted); font-weight:600;">#${l.id}</td>
                    <td style="white-space:nowrap;">${formatDateTime(l.timestamp)}</td>
                    <td>${statusBadge(l.action)}</td>
                    <td style="font-weight:600;">${escapeHtml(l.performed_by)}</td>
                    <td style="line-height:1.4;">${detailsHtml}</td>
                </tr>`;
            }).join('');
        } catch (e) {
            document.getElementById('logsBody').innerHTML = '<tr class="empty-row"><td colspan="5">Error loading logs</td></tr>';
        }
    }

    loadLogs();
})();
