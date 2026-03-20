/* MediSync - Inventory JS */
(function () {
    var allMedicines = [];

    // --- Load Stats ---
    async function loadInvStats() {
        try {
            var res = await fetch('/api/dashboard/stats');
            var data = await res.json();
            document.getElementById('invStatTotal').textContent = data.total_items;
            document.getElementById('invStatExpiring').textContent = data.about_to_expire;
            document.getElementById('invStatExpired').textContent = data.expired;
            document.getElementById('invStatDispensed').textContent = data.dispensed;
            document.getElementById('invStatDiscarded').textContent = data.discarded;
        } catch (e) { /* ignore */ }
    }

    // --- Load Categories (for autocomplete) ---
    async function loadCategories() {
        try {
            var res = await fetch('/api/medicines/categories');
            var cats = await res.json();
            
            // Setup filter autocomplete
            setupCategoryAutocomplete('invCategoryInput', 'invCategoryDropdown', cats, function() {
                loadMedicines();
            });
            
            // Setup form autocomplete
            setupCategoryAutocomplete('medCategory', 'medCategoryDropdown', cats);
            
        } catch (e) { /* ignore */ }
    }

    function setupCategoryAutocomplete(inputId, dropdownId, cats, onSelect) {
        const input = document.getElementById(inputId);
        const dropdown = document.getElementById(dropdownId);
        if (!input || !dropdown) return;
        let debounce;

        input.addEventListener('input', function() {
            clearTimeout(debounce);
            const q = this.value.trim().toLowerCase();
            if (!q) { dropdown.classList.remove('show'); if(onSelect) onSelect(); return; }
            debounce = setTimeout(function() {
                const matches = cats.filter(c => c.toLowerCase().includes(q));
                if (!matches.length) { dropdown.classList.remove('show'); return; }
                dropdown.innerHTML = matches.map(c => `<div class="autocomplete-item" data-val="${escapeHtml(c)}">${escapeHtml(c)}</div>`).join('');
                dropdown.classList.add('show');
                dropdown.querySelectorAll('.autocomplete-item').forEach(el => {
                    el.addEventListener('mousedown', (e) => {
                        e.preventDefault();
                        input.value = el.dataset.val;
                        dropdown.classList.remove('show');
                        if (onSelect) onSelect();
                    });
                });
            }, 200);
        });
        input.addEventListener('blur', () => setTimeout(() => dropdown.classList.remove('show'), 200));
    }

    // --- Load Medicines ---
    async function loadMedicines() {
        var params = new URLSearchParams();
        
        // Universal search
        var uSearch = document.getElementById('invUniversalSearch').value.trim();
        if (uSearch) params.set('search', uSearch);

        // Dynamic Filter
        var type = document.getElementById('invFilterType').value;
        if (type === 'status') {
            var s = document.getElementById('invStatusSelect').value;
            if (s) params.set('status', s);
        } else if (type === 'category') {
            var c = document.getElementById('invCategoryInput').value.trim();
            if (c) params.set('category', c);
        } else if (type === 'date_added') {
            var d = document.getElementById('invDateFilter').value;
            if (d) params.set('date_added', d);
        } else if (type === 'sort') {
            var sort = document.getElementById('invSortBy').value;
            params.set('sort', sort);
        }

        try {
            var res = await fetch('/api/medicines?' + params.toString());
            allMedicines = await res.json();
            renderTable();
        } catch (e) {
            document.getElementById('inventoryBody').innerHTML = '<tr class="empty-row"><td colspan="11">Failed to load inventory</td></tr>';
        }
    }

    function renderTable() {
        var tbody = document.getElementById('inventoryBody');
        if (!allMedicines.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="12">No medicines found</td></tr>';
            return;
        }
        tbody.innerHTML = allMedicines.map(function (m) {
            var actions = '<div class="actions">' +
                '<button class="btn btn-outline btn-sm" onclick="editMedicine(' + m.id + ')">Edit</button>' +
                '<button class="btn btn-yellow btn-sm" onclick="discardMedicine(' + m.id + ')">Discard</button>' +
                '<button class="btn btn-danger btn-sm" onclick="deleteMedicine(' + m.id + ')">Delete</button>' +
                '</div>';
            var daysHtml = '-';
            if (m.days_remaining !== null) {
                if (m.status === 'Expired') daysHtml = '<span style="color:var(--red);font-weight:700;">' + m.days_remaining + '</span>';
                else if (m.status === 'Near Expiry') daysHtml = '<span style="color:var(--orange);font-weight:700;">' + m.days_remaining + '</span>';
                else if (m.status === 'Active') daysHtml = '<span style="color:var(--primary);font-weight:700;">' + m.days_remaining + '</span>';
                else daysHtml = '<span style="color:var(--text);font-weight:700;">' + m.days_remaining + '</span>';
            }
            return '<tr><td>' + escapeHtml(m.stock_number) + '</td><td>' + escapeHtml(m.article_name) +
                '</td><td>' + escapeHtml(m.description_dosage) + '</td><td>' + escapeHtml(m.unit_of_measurement) +
                '</td><td>' + m.quantity +
                '</td><td>' + escapeHtml(m.category) + '</td><td>' + formatDate(m.expiration_date) +
                '</td><td>' + daysHtml + '</td><td>' + escapeHtml(m.remarks) + '</td><td>' + statusBadge(m.status) +
                '</td><td>' + actions + '</td></tr>';
        }).join('');
    }

    // --- Toolbar Event Listeners ---
    const invFilterType = document.getElementById('invFilterType');
    const invSearchWrapper = document.getElementById('invSearchWrapper');
    const invStatusWrapper = document.getElementById('invStatusWrapper');
    const invCategoryWrapper = document.getElementById('invCategoryWrapper');
    const invDateWrapper = document.getElementById('invDateWrapper');
    const invSortWrapper = document.getElementById('invSortWrapper');

    invFilterType.addEventListener('change', function() {
        const val = this.value;
        [invSearchWrapper, invStatusWrapper, invCategoryWrapper, invDateWrapper, invSortWrapper].forEach(w => w.style.display = 'none');
        
        if (val === 'status') invStatusWrapper.style.display = 'block';
        else if (val === 'category') invCategoryWrapper.style.display = 'block';
        else if (val === 'date_added') invDateWrapper.style.display = 'block';
        else if (val === 'sort') invSortWrapper.style.display = 'block';
        
        loadMedicines();
    });

    var debounceTimer;
    document.getElementById('invUniversalSearch').addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(loadMedicines, 400);
    });
    document.getElementById('invStatusSelect').addEventListener('change', loadMedicines);
    document.getElementById('invDateFilter').addEventListener('change', loadMedicines);
    document.getElementById('invSortBy').addEventListener('change', loadMedicines);

    // --- Export Dropdown ---
    var exportDropdown = document.getElementById('exportDropdown');
    document.getElementById('exportBtn').addEventListener('click', function (e) {
        e.stopPropagation();
        exportDropdown.classList.toggle('show');
    });
    document.addEventListener('click', function () { exportDropdown.classList.remove('show'); });

    // --- Export ---
    document.getElementById('exportCsvBtn').addEventListener('click', function () {
        window.location.href = '/api/inventory/export/csv';
        exportDropdown.classList.remove('show');
    });
    document.getElementById('exportPdfBtn').addEventListener('click', function () {
        window.location.href = '/api/inventory/export/pdf';
        exportDropdown.classList.remove('show');
    });
    document.getElementById('printBtn').addEventListener('click', function () {
        exportDropdown.classList.remove('show');
        window.print();
    });

    // --- Add Medicine Modal ---
    document.getElementById('addMedBtn').addEventListener('click', function () {
        resetMedForm();
        document.getElementById('medModalTitle').textContent = 'Add Medicine';
        document.getElementById('medSubmitBtn').textContent = 'Add Medicine';
        document.getElementById('medStock').disabled = false;
        document.getElementById('medQty').disabled = false;
        openModal('medModal');
    });

    function resetMedForm() {
        document.getElementById('medEditId').value = '';
        document.getElementById('medForm').reset();
    }

    // --- Submit Medicine ---
    document.getElementById('medSubmitBtn').addEventListener('click', async function () {
        var editId = document.getElementById('medEditId').value;
        var payload = {
            stock_number: document.getElementById('medStock').value.trim(),
            article_name: document.getElementById('medName').value.trim(),
            description_dosage: document.getElementById('medDosage').value.trim(),
            unit_of_measurement: document.getElementById('medUnit').value,
            category: document.getElementById('medCategory').value.trim(),
            expiration_date: document.getElementById('medExpDate').value,
            remarks: document.getElementById('medRemarks').value.trim()
        };
        
        if (!editId) {
            payload.quantity = document.getElementById('medQty').value;
        }

        if (!payload.stock_number || !payload.article_name || !payload.unit_of_measurement) {
            showToast('Please fill in required fields.', 'error');
            return;
        }

        try {
            var url = editId ? '/api/medicines/' + editId : '/api/medicines';
            var method = editId ? 'PUT' : 'POST';
            var res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            if (res.ok) {
                showToast(editId ? 'Medicine updated successfully.' : 'Medicine added successfully.');
                closeModal('medModal');
                loadMedicines();
                loadInvStats();
            } else {
                showToast(data.error || 'Failed to save medicine.', 'error');
            }
        } catch (e) {
            showToast('Connection error.', 'error');
        }
    });

    // --- Edit Medicine ---
    window.editMedicine = function (id) {
        var med = allMedicines.find(function (m) { return m.id === id; });
        if (!med) return;
        document.getElementById('medEditId').value = med.id;
        document.getElementById('medStock').value = med.stock_number;
        document.getElementById('medStock').disabled = true;
        document.getElementById('medName').value = med.article_name;
        document.getElementById('medDosage').value = med.description_dosage || '';
        document.getElementById('medUnit').value = med.unit_of_measurement;
        document.getElementById('medQty').value = med.quantity;
        document.getElementById('medQty').disabled = true;
        document.getElementById('medCategory').value = med.category || '';
        document.getElementById('medExpDate').value = med.expiration_date || '';
        document.getElementById('medRemarks').value = med.remarks || '';
        document.getElementById('medModalTitle').textContent = 'Edit Medicine';
        document.getElementById('medSubmitBtn').textContent = 'Update Medicine';
        openModal('medModal');
    };

    // --- Restock Medicine ---
    document.getElementById('restockMedBtn').addEventListener('click', function() {
        var sel = document.getElementById('restockMedSelect');
        sel.innerHTML = '<option value="">Choose medicine to restock...</option>';
        var activeMeds = allMedicines.filter(m => (m.status === 'Active' || m.status === 'Near Expiry' || m.status === 'Expired') && !m.is_restock);
        
        // Group available medicines by name to reduce clutter (optional but nice), but since uniqueness is by stock_number, we show unique items.
        // Wait, the prompt says "separate row in the inventory" doing restocking. So they pick from existing.
        activeMeds.forEach(function (m) {
            var opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.article_name + ' (' + m.stock_number + ')';
            sel.appendChild(opt);
        });
        
        document.getElementById('restockForm').reset();
        document.getElementById('restockStock').value = '';
        document.getElementById('restockCategory').value = '';
        document.getElementById('restockDosage').value = '';
        document.getElementById('restockUnit').value = '';
        openModal('restockModal');
    });

    document.getElementById('restockMedSelect').addEventListener('change', function() {
        var medId = parseInt(this.value);
        var med = allMedicines.find(function (m) { return m.id === medId; });
        if (med) {
            document.getElementById('restockStock').value = med.stock_number;
            document.getElementById('restockCategory').value = med.category || '';
            document.getElementById('restockDosage').value = med.description_dosage || '';
            document.getElementById('restockUnit').value = med.unit_of_measurement;
        } else {
            document.getElementById('restockStock').value = '';
            document.getElementById('restockCategory').value = '';
            document.getElementById('restockDosage').value = '';
            document.getElementById('restockUnit').value = '';
        }
    });

    document.getElementById('restockSubmitBtn').addEventListener('click', async function() {
        var medId = document.getElementById('restockMedSelect').value;
        var qty = document.getElementById('restockQty').value;
        var expDate = document.getElementById('restockExpDate').value;
        
        if (!medId || !qty) {
            showToast('Please select a medicine and enter quantity.', 'error');
            return;
        }

        try {
            var res = await fetch('/api/medicines/' + medId + '/restock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ quantity: qty, expiration_date: expDate })
            });
            var data = await res.json();
            if (res.ok) {
                showToast('Medicine restocked successfully.');
                closeModal('restockModal');
                loadMedicines();
                loadInvStats();
            } else {
                showToast(data.error || 'Failed to restock.', 'error');
            }
        } catch (e) {
            showToast('Connection error.', 'error');
        }
    });

    // --- Discard Medicine ---
    window.discardMedicine = function (id) {
        document.getElementById('discardMedId').value = id;
        document.getElementById('discardReason').value = '';
        openModal('discardModal');
    };
    document.getElementById('discardConfirmBtn').addEventListener('click', async function () {
        var id = document.getElementById('discardMedId').value;
        var reason = document.getElementById('discardReason').value.trim();
        if (!reason) { showToast('Please provide a reason.', 'error'); return; }
        try {
            var res = await fetch('/api/medicines/' + id + '/discard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: reason })
            });
            if (res.ok) {
                showToast('Medicine discarded.');
                closeModal('discardModal');
                loadMedicines();
                loadInvStats();
            } else { showToast('Failed to discard.', 'error'); }
        } catch (e) { showToast('Connection error.', 'error'); }
    });

    // --- Delete Medicine ---
    window.deleteMedicine = function (id) {
        document.getElementById('deleteMedId').value = id;
        document.getElementById('deleteReason').value = '';
        openModal('deleteModal');
    };
    document.getElementById('deleteConfirmBtn').addEventListener('click', async function () {
        var id = document.getElementById('deleteMedId').value;
        var reason = document.getElementById('deleteReason').value.trim();
        if (!reason) { showToast('Please provide a reason.', 'error'); return; }
        try {
            var res = await fetch('/api/medicines/' + id, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: reason })
            });
            if (res.ok) {
                showToast('Medicine deleted.');
                closeModal('deleteModal');
                loadMedicines();
                loadInvStats();
            } else { showToast('Failed to delete.', 'error'); }
        } catch (e) { showToast('Connection error.', 'error'); }
    });

    // --- Block Click Popups ---
    document.querySelectorAll('[data-block]').forEach(function (el) {
        el.addEventListener('click', function () {
            var type = this.dataset.block;
            showInvBlockPopup(type);
        });
    });

    async function showInvBlockPopup(type) {
        var titles = {
            total: 'Total Items', about_to_expire: 'About to Expire',
            expired: 'Expired Items', dispensed: 'Dispensed Items', discarded: 'Discarded Items'
        };
        document.getElementById('invBlockModalTitle').textContent = titles[type] || 'Items';
        try {
            var res = await fetch('/api/dashboard/block/' + type);
            var items = await res.json();
            var thead = document.getElementById('invBlockTableHead');
            var tbody = document.getElementById('invBlockTableBody');
            if (type === 'dispensed') {
                thead.innerHTML = '<tr><th>Dispenser</th><th>Medicine</th><th>Qty</th><th>Recipient</th><th>Center</th><th>Date</th></tr>';
                tbody.innerHTML = items.length ? items.map(function (d) {
                    return '<tr><td>' + escapeHtml(d.dispenser_name) + '</td><td>' + escapeHtml(d.medicine_name) +
                        '</td><td>' + d.quantity_dispensed + '</td><td>' + escapeHtml(d.recipient_name) +
                        '</td><td>' + escapeHtml(d.center_name) + '</td><td>' + formatDateTime(d.date_time) + '</td></tr>';
                }).join('') : '<tr class="empty-row"><td colspan="6">No items</td></tr>';
            } else {
                thead.innerHTML = '<tr><th>Stock #</th><th>Article</th><th>Unit</th><th>Qty</th><th>Category</th><th>Exp. Date</th><th>Days</th><th>Status</th></tr>';
                tbody.innerHTML = items.length ? items.map(function (m) {
                    var popDays = '-';
                    if (m.days_remaining !== null) {
                        if (m.status === 'Expired') popDays = '<span style="color:var(--coral);font-weight:700;">' + m.days_remaining + '</span>';
                        else if (m.status === 'Near Expiry') popDays = '<span style="color:var(--yellow);font-weight:700;">' + m.days_remaining + '</span>';
                        else if (m.status === 'Active') popDays = '<span style="color:var(--primary);font-weight:700;">' + m.days_remaining + '</span>';
                        else popDays = '<span style="color:var(--text);font-weight:700;">' + m.days_remaining + '</span>';
                    }
                    return '<tr><td>' + escapeHtml(m.stock_number) + '</td><td>' + escapeHtml(m.article_name) +
                        '</td><td>' + escapeHtml(m.unit_of_measurement) + '</td><td>' + m.quantity + '</td><td>' +
                        escapeHtml(m.category) + '</td><td>' + formatDate(m.expiration_date) + '</td><td>' + popDays + '</td><td>' +
                        statusBadge(m.status) + '</td></tr>';
                }).join('') : '<tr class="empty-row"><td colspan="8">No items</td></tr>';
            }
            openModal('invBlockModal');
        } catch (e) { showToast('Failed to load data.', 'error'); }
    }

    // Init
    loadMedicines();
    loadInvStats();
    loadCategories();
})();
