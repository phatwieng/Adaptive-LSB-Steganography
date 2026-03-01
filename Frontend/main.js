import uiManager from './ui.js';

const API_BASE = '';

document.addEventListener('DOMContentLoaded', () => {
    console.log('LSB Steganography Initialized');
    initializeTabs();
    initializeFileUploads();
    initializeForms();
});

/* ── TAB NAVIGATION ── */
function initializeTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            uiManager.switchTab(tab.getAttribute('data-tab'));
        });
    });
}

/* ── FILE UPLOADS ── */
function initializeFileUploads() {
    const uploads = [
        { uploadId: 'encode-image-upload', inputId: 'encode-image-input' },
        { uploadId: 'decode-image-upload', inputId: 'decode-image-input' },
        { uploadId: 'capacity-image-upload', inputId: 'capacity-image-input' },
        { uploadId: 'analyze-original-upload', inputId: 'analyze-original-input', previewId: null },
        { uploadId: 'analyze-stego-upload', inputId: 'analyze-stego-input', previewId: null }
    ];

    uploads.forEach(({ uploadId, inputId, previewId }) => {
        const uploadDiv = document.getElementById(uploadId);
        const input = document.getElementById(inputId);
        if (!uploadDiv || !input) return;

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            uiManager.updateFileUpload(uploadDiv, file);
            if (previewId && file) uiManager.previewImage(file, previewId);
        });

        uploadDiv.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadDiv.style.borderColor = '#f5c800';
        });

        uploadDiv.addEventListener('dragleave', () => {
            uploadDiv.style.borderColor = '';
        });

        uploadDiv.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadDiv.style.borderColor = '';
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });
    });
}

/* ── FORM HANDLERS ── */
function initializeForms() {
    document.getElementById('encode-form').addEventListener('submit', handleEncode);
    document.getElementById('decode-form').addEventListener('submit', handleDecode);
    document.getElementById('capacity-form').addEventListener('submit', handleCapacity);
    document.getElementById('analyze-form').addEventListener('submit', handleAnalyze);
}

/* ── ACTION: ENCODE ── */
async function handleEncode(e) {
    e.preventDefault();
    const imageInput = document.getElementById('encode-image-input');
    const message = document.getElementById('encode-message').value;
    const password = document.getElementById('encode-password').value;

    if (!imageInput.files[0] || !message || !password) {
        uiManager.showAlert('encode-alert', 'All fields required', 'error');
        return;
    }

    uiManager.toggleLoading('encode-loading', true);
    uiManager.toggleResult('encode-result', false);

    try {
        // Step 1: Chunked Upload
        const file = imageInput.files[0];
        const sessionId = Math.random().toString(36).substring(7);
        const chunkSize = 5 * 1024 * 1024;
        const totalChunks = Math.ceil(file.size / chunkSize);

        for (let i = 0; i < totalChunks; i++) {
            const chunk = file.slice(i * chunkSize, (i + 1) * chunkSize);
            const formData = new FormData();
            formData.append('chunk', chunk);
            formData.append('index', i);
            formData.append('total', totalChunks);
            formData.append('sessionId', sessionId);
            formData.append('filename', file.name);

            const res = await fetch(`${API_BASE}/api/upload-chunk`, { method: 'POST', body: formData });
            if (!res.ok) throw new Error('Upload failed');
        }

        // Step 2: Finalize Encoding
        const finalRes = await fetch(`${API_BASE}/api/encode-final`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId, message, password, filePath: sessionId + '_' + file.name })
        });

        if (!finalRes.ok) throw new Error((await finalRes.json()).error || 'Processing failed');

        const blob = await finalRes.blob();
        const disp = finalRes.headers.get('Content-Disposition');
        let filename = 'encoded_image.png';
        if (disp && disp.includes('filename=')) {
            filename = disp.split('filename=')[1].split(';')[0].replace(/['"]/g, '').trim();
        }

        uiManager.downloadBlob(blob, filename);
        uiManager.showAlert('encode-alert', 'Success! Image encoded and downloaded.', 'success');
        document.getElementById('encode-form').reset();
        uiManager.updateFileUpload(document.getElementById('encode-image-upload'), null);

    } catch (err) {
        console.error('Encode Error:', err);
        uiManager.showAlert('encode-alert', err.message, 'error');
    } finally {
        uiManager.toggleLoading('encode-loading', false);
    }
}

/* ── ACTION: DECODE ── */
async function handleDecode(e) {
    e.preventDefault();
    const imageInput = document.getElementById('decode-image-input');
    const password = document.getElementById('decode-password').value;

    if (!imageInput.files[0] || !password) {
        uiManager.showAlert('decode-alert', 'Image and password required', 'error');
        return;
    }

    uiManager.toggleLoading('decode-loading', true);
    uiManager.toggleResult('decode-result', false);

    try {
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        formData.append('password', password);

        const res = await fetch(`${API_BASE}/api/decode`, { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok || !data.success) throw new Error(data.error || 'Decoding failed');

        uiManager.displayMessage(data.message, 'decode-result');
        uiManager.showAlert('decode-alert', 'Message extracted successfully', 'success');

    } catch (err) {
        console.error('Decode Error:', err);
        uiManager.showAlert('decode-alert', err.message, 'error');
    } finally {
        uiManager.toggleLoading('decode-loading', false);
    }
}

/* ── ACTION: CAPACITY ── */
async function handleCapacity(e) {
    e.preventDefault();
    const imageInput = document.getElementById('capacity-image-input');

    if (!imageInput.files[0]) {
        uiManager.showAlert('capacity-alert', 'Please select an image', 'error');
        return;
    }

    uiManager.toggleLoading('capacity-loading', true);
    uiManager.toggleResult('capacity-result', false);

    try {
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);

        const res = await fetch(`${API_BASE}/api/capacity`, { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok || !data.success) throw new Error(data.error || 'Capacity check failed');

        uiManager.displayCapacity(data.capacity, 'capacity-result');
        uiManager.showAlert('capacity-alert', 'Capacity analysis complete', 'success');

    } catch (err) {
        console.error('Capacity Error:', err);
        uiManager.showAlert('capacity-alert', err.message, 'error');
    } finally {
        uiManager.toggleLoading('capacity-loading', false);
    }
}

/* ── ACTION: ANALYZE ── */
async function handleAnalyze(e) {
    e.preventDefault();
    const originalInput = document.getElementById('analyze-original-input');
    const stegoInput = document.getElementById('analyze-stego-input');

    if (!originalInput.files[0] || !stegoInput.files[0]) {
        uiManager.showAlert('analyze-alert', 'Both images required', 'error');
        return;
    }

    uiManager.toggleLoading('analyze-loading', true);
    uiManager.toggleResult('analyze-result', false);
    document.getElementById('analyze-result').innerHTML = '<div id="histogram-charts"></div>';

    try {
        const formData = new FormData();
        formData.append('original', originalInput.files[0]);
        formData.append('stego', stegoInput.files[0]);

        const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: formData });
        const text = await res.text();
        
        let data;
        try {
            data = JSON.parse(text);
        } catch (jsonErr) {
            throw new Error(`Server returned invalid response (HTTP ${res.status})`);
        }

        if (!res.ok || !data.success) throw new Error(data.error || 'Analysis failed');

        uiManager.displayAnalysis(data, 'analyze-result');
        uiManager.showAlert('analyze-alert', 'Deep analysis complete', 'success');

    } catch (err) {
        console.error('Analysis Error:', err);
        uiManager.showAlert('analyze-alert', err.message, 'error');
    } finally {
        uiManager.toggleLoading('analyze-loading', false);
    }
}

window.app = { uiManager, handleEncode, handleDecode, handleCapacity, handleAnalyze };
console.log('App handlers initialized');
