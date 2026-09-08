// Admin Dashboard Logic with WhatsApp PDF Receipt Integration
document.addEventListener('DOMContentLoaded', () => {
    
    // Tab switching
    const navTabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            
            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.tab);
            if (target) target.style.display = 'block';
        });
    });

    // Verify Vargani & Open WhatsApp PDF Link
    window.verifyAndSendWA = async (id) => {
        if (!confirm('ही वर्गणी पडताळायची (Confirm) आहे का? Confirm केल्यावर WhatsApp वर पावती मेसेज पाठवला जाईल.')) return;
        
        try {
            const res = await fetch(`/api/vargani/verify/${id}`, { method: 'PUT' });
            const data = await res.json();
            if (data.success) {
                alert('✅ वर्गणी Confirm झाली! आता WhatsApp उघडत आहे...');
                if (data.wa_url) {
                    window.open(data.wa_url, '_blank');
                }
                location.reload();
            } else {
                alert('❌ एरर: ' + data.message);
            }
        } catch (e) {
            alert('❌ नेटवर्क एरर');
        }
    };

    // Delete Vargani Action
    window.deleteVargani = async (id) => {
        if (!confirm('नक्की ही नोंद डिलीट करायची आहे का?')) return;

        try {
            const res = await fetch(`/api/vargani/delete/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                alert('✅ नोंद डिलीट झाली.');
                location.reload();
            } else {
                alert('❌ एरर: ' + data.message);
            }
        } catch (e) {
            alert('❌ नेटवर्क एरर');
        }
    };

    // Add Manual Cash Vargani Form
    const manualForm = document.getElementById('manualVarganiForm');
    if (manualForm) {
        manualForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(manualForm);
            const dataObj = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/api/vargani/manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataObj)
                });
                const data = await res.json();
                if (data.success) {
                    alert('✅ रोख वर्गणी नोंदवली गेली! पावती नं: ' + data.receipt_no);
                    manualForm.reset();
                    location.reload();
                } else {
                    alert('❌ एरर: ' + data.message);
                }
            } catch (e) {
                alert('❌ नेटवर्क एरर');
            }
        });
    }

    // Settings & QR Code Update Form
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(settingsForm);

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    alert('✅ मंडळ माहिती व QR Code अपडेट झाला!');
                    location.reload();
                } else {
                    alert('❌ एरर: ' + data.message);
                }
            } catch (e) {
                alert('❌ नेटवर्क एरर');
            }
        });
    }

    // Search and Filter Table
    const searchInput = document.getElementById('searchVargani');
    const statusFilter = document.getElementById('filterStatus');

    const fetchFilteredRecords = async () => {
        const search = searchInput ? searchInput.value : '';
        const status = statusFilter ? statusFilter.value : 'All';

        const res = await fetch(`/api/vargani/list?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`);
        const data = await res.json();
        
        if (data.success) {
            renderTable(data.records);
        }
    };

    if (searchInput) searchInput.addEventListener('input', fetchFilteredRecords);
    if (statusFilter) statusFilter.addEventListener('change', fetchFilteredRecords);

    function renderTable(records) {
        const tbody = document.getElementById('varganiTableBody');
        if (!tbody) return;

        if (records.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#888; padding: 2rem;">कोणतीही वर्गणी नोंद सापडली नाही.</td></tr>';
            return;
        }

        tbody.innerHTML = records.map(r => `
            <tr>
                <td><strong>${r.receipt_no}</strong></td>
                <td>${r.name}<br><small style="color:#64748b;">${r.mobile}</small></td>
                <td>${r.address || '-'}</td>
                <td><strong style="color:var(--primary);">₹${r.amount}</strong></td>
                <td>${r.payment_mode}<br><small style="font-size:0.8rem; color:#64748b;">${r.transaction_id || ''}</small></td>
                <td>
                    ${r.status === 'Verified' ? 
                        '<span class="badge-status badge-verified">✅ Verified</span>' : 
                        (r.status === 'Pending Cash' ? '<span class="badge-status" style="background:#fee2e2; color:#991b1b;">🔔 Pending Cash</span>' : '<span class="badge-status badge-pending">⏳ Pending</span>')}
                </td>
                <td>
                    <a href="/receipt/${r.receipt_no}" class="btn-action-sm" target="_blank" style="color:#2563eb;">📄 पावती</a>
                    ${r.status !== 'Verified' ? `<button onclick="verifyAndSendWA('${r._id}')" class="btn-wa-action">💬 Confirm & WhatsApp</button>` : ''}
                    <button onclick="deleteVargani('${r._id}')" class="btn-action-sm" style="color:#dc2626; cursor:pointer;">🗑️ Delete</button>
                </td>
            </tr>
        `).join('');
    }
});
