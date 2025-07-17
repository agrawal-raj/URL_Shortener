document.addEventListener('DOMContentLoaded', function() {
    // Clipboard copy functionality
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const text = this.getAttribute('data-clipboard-text');
            navigator.clipboard.writeText(text).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = 'Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });
    
    // QR code generation (optional enhancement)
    const qrElements = document.querySelectorAll('.qr-code');
    if (qrElements.length > 0 && typeof QRCode !== 'undefined') {
        qrElements.forEach(element => {
            new QRCode(element, {
                text: element.dataset.url,
                width: 128,
                height: 128
            });
        });
    }
});