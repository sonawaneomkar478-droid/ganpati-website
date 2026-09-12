// Admin Dashboard Logic with WhatsApp PDF Receipt Integration
document.addEventListener('DOMContentLoaded', () => {
    
    // Tab switching with State Persistence (Remembers tab across refreshes)
    const navTabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    function activateTab(tabId) {
        if (!tabId) return;
        const targetBtn = Array.from(navTabs).find(t => t.dataset.tab === tabId);
        const targetContent = document.getElementById(tabId);
        if (targetBtn && targetContent) {
            navTabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            
            targetBtn.classList.add('active');
            targetContent.style.display = 'block';
            try {
                localStorage.setItem('admin_active_tab', tabId);
                history.replaceState(null, '', '#' + tabId);
            } catch(e) {}
        }
    }

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            activateTab(tab.dataset.tab);
        });
    });

    // Restore active tab from URL hash or localStorage on page load/refresh
    const savedTab = location.hash.replace('#', '') || localStorage.getItem('admin_active_tab');
    if (savedTab && document.getElementById(savedTab)) {
        activateTab(savedTab);
    }

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

    // Toggle QR Code Display in Manual Vargani Tab
    window.toggleManualPaymentView = function(val) {
        const qrBox = document.getElementById('manualQrBox');
        if (qrBox) {
            if (val && (val.includes('Online') || val.includes('QR') || val.includes('NetBanking'))) {
                qrBox.style.display = 'block';
            } else {
                qrBox.style.display = 'none';
            }
        }
    };

    // Add Manual Vargani Form (Cash / Online QR)
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
                    alert('✅ ' + (data.message || ('वर्गणी यशस्वीरित्या नोंदवली गेली! पावती नं: ' + data.receipt_no)));
                    manualForm.reset();
                    const qrBox = document.getElementById('manualQrBox');
                    if (qrBox) qrBox.style.display = 'none';
                    try { localStorage.setItem('admin_active_tab', 'cashTab'); } catch(e) {}
                    location.hash = 'cashTab';
                    location.reload();
                } else {
                    alert('❌ एरर: ' + data.message);
                }
            } catch (e) {
                alert('❌ नेटवर्क एरर');
            }
        });
    }

    // Front Page Edit Form
    const frontPageForm = document.getElementById('frontPageForm');
    if (frontPageForm) {
        frontPageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = frontPageForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerText = '⏳ मुख्य पान सेव्ह होत आहे...';
            }

            const formData = new FormData(frontPageForm);
            const photoInput = document.getElementById('fp_entrance_photo');
            if (photoInput && photoInput.files && photoInput.files[0] && typeof compressImageClient === 'function') {
                try {
                    if (submitBtn) submitBtn.innerText = '⚡ फोटो ऑप्टिमाइझ होत आहे...';
                    const compressed = await compressImageClient(photoInput.files[0], 1600, 0.82);
                    formData.set('entrance_photo', compressed);
                } catch(err) {
                    console.log('Compression fallback:', err);
                }
            }

            try {
                if (submitBtn) submitBtn.innerText = '☁️ माहिती सेव्ह होत आहे...';
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    alert('✅ मुख्य पानाची माहिती (Front Page Info) व फोटो यशस्वीरित्या अपडेट झाली!');
                    try { localStorage.setItem('admin_active_tab', 'frontPageTab'); } catch(e) {}
                    location.hash = 'frontPageTab';
                    location.reload();
                } else {
                    alert('❌ एरर: ' + data.message);
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerText = '💾 मुख्य पान बदला (Save Front Page Changes)';
                    }
                }
            } catch (e) {
                alert('❌ नेटवर्क एरर! फाईल साईज मोठी असू शकते, कृपया लहान फोटो वापरा.');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerText = '💾 मुख्य पान बदला (Save Front Page Changes)';
                }
            }
        });
    }

    // Settings & QR Code Update Form
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = settingsForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerText = '⏳ सेव्ह होत आहे...';
            }

            const formData = new FormData(settingsForm);
            const qrInput = document.getElementById('qr_code');
            if (qrInput && qrInput.files && qrInput.files[0] && typeof compressImageClient === 'function') {
                try {
                    if (submitBtn) submitBtn.innerText = '⚡ QR Code ऑप्टिमाइझ होत आहे...';
                    const compressedQr = await compressImageClient(qrInput.files[0], 1200, 0.85);
                    formData.set('qr_code', compressedQr);
                } catch(err) {
                    console.log('QR compression fallback:', err);
                }
            }

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    alert('✅ मंडळ माहिती व QR Code अपडेट झाला!');
                    try { localStorage.setItem('admin_active_tab', 'settingsTab'); } catch(e) {}
                    location.hash = 'settingsTab';
                    location.reload();
                } else {
                    alert('❌ एरर: ' + data.message);
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerText = '💾 माहिती सेव्ह करा (Save Settings)';
                    }
                }
            } catch (e) {
                alert('❌ नेटवर्क एरर! कृपया पुन्हा प्रयत्न करा.');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerText = '💾 माहिती सेव्ह करा (Save Settings)';
                }
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
