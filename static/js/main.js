// Public Front Page Logic
document.addEventListener('DOMContentLoaded', () => {
    // Quick Amount Buttons
    const quickBtns = document.querySelectorAll('.btn-quick');
    const amountInput = document.getElementById('amount');

    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (amountInput) {
                amountInput.value = btn.dataset.amount;
                amountInput.focus();
            }
        });
    });

    // Vargani Form Submission
    const varganiForm = document.getElementById('varganiForm');
    const submitBtn = document.getElementById('submitBtn');
    const formMsg = document.getElementById('formMsg');

    if (varganiForm) {
        varganiForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            submitBtn.disabled = true;
            submitBtn.innerHTML = '⏳ नोंदणी होत आहे...';
            formMsg.style.display = 'none';

            const formData = new FormData(varganiForm);

            try {
                const response = await fetch('/api/vargani/submit', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    alert('🚩 गणेशोत्सव वर्गणी संकलन 🚩\n\nआपली वर्गणी नोंदणी यशस्वीरित्या झाली आहे!\n\nमंडळाने पडताळणी (Check) केल्यावर तुम्हाला व्हॉट्सॲपवर अधिकृत पावती पाठवण्यात येईल.\n\nधन्यवाद! गणपती बाप्पा मोरया! 🚩');
                    
                    if (typeof closeVarganiModal === 'function') closeVarganiModal();
                    varganiForm.reset();
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '🚩 वर्गणी नोंदणी करा ➔';

                    setTimeout(() => {
                        location.reload();
                    }, 500);
                } else {
                    formMsg.className = 'alert alert-danger';
                    formMsg.innerHTML = `❌ ${data.message}`;
                    formMsg.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '🚩 वर्गणी नोंदणी करा ➔';
                }
            } catch (error) {
                formMsg.className = 'alert alert-danger';
                formMsg.innerHTML = '❌ सर्व्हरशी संपर्क होऊ शकला नाही. पुन्हा प्रयत्न करा.';
                formMsg.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.innerHTML = '🚩 वर्गणी नोंदणी करा ➔';
            }
        });
    }

    // Copy UPI ID
    const copyUpiBtn = document.getElementById('copyUpiBtn');
    if (copyUpiBtn) {
        copyUpiBtn.addEventListener('click', () => {
            const upiId = document.getElementById('upiIdText').innerText;
            navigator.clipboard.writeText(upiId).then(() => {
                alert('UPI ID कॉपी झाला: ' + upiId);
            });
        });
    }
});
