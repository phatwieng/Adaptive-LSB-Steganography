class UIManager {
    constructor() {
        this.activeTab = 'encode';
        this.charts = {};
    }

    /* ── UI HELPERS ── */
    toggleLoading(id, show) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('show', show);
    }

    toggleResult(id, show) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('show', show);
    }

    showAlert(id, msg, type) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = msg;
        el.className = `alert show alert-${type}`;
        setTimeout(() => el.classList.remove('show'), 5000);
    }

    updateFileUpload(div, file) {
        if (!div) return;
        const text = div.querySelector('.file-upload-text');
        if (file) {
            div.classList.add('has-file');
            text.innerHTML = `<strong>${file.name}</strong> (${this.formatBytes(file.size)})`;
        } else {
            div.classList.remove('has-file');
            text.textContent = 'Click to select or drag & drop';
        }
    }

    previewImage(file, id) {
        const el = document.getElementById(id);
        if (!el || !file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            el.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            el.classList.add('show');
        };
        reader.readAsDataURL(file);
    }

    formatBytes(bytes) {
        if (!bytes) return '0 B';
        const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
    }

    /* ── TABS ── */
    switchTab(id) {
        document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === id));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === `${id}-tab`));
        this.activeTab = id;
    }

    /* ── RENDERING ── */
    displayMessage(msg, id) {
        const el = document.getElementById(id);
        const txt = el.querySelector('.result-text');
        txt.textContent = msg;
        this.toggleResult(id, true);
    }

    displayCapacity(c, id) {
        const el = document.getElementById(id);
        el.innerHTML = `
        <div class="analysis-section">
            <h2>Capacity Analysis</h2>
            <div class="stats-grid">
                <div class="stat-card"><h4>Max Payload</h4><div class="value">${this.formatBytes(c.max_capacity_chars)}</div></div>
                <div class="stat-card"><h4>Dimensions</h4><div class="value">${c.width} <span class="unit">×</span> ${c.height}</div></div>
                <div class="stat-card"><h4>Precision</h4><div class="value">${c.capacity_type.toUpperCase()}</div></div>
            </div>
        </div>`;
        this.toggleResult(id, true);
    }

    displayAnalysis(a, id) {
        const el = document.getElementById(id);
        let html = this._renderStealthScore(a);
        html += this._renderQualityMetrics(a);
        html += this._renderComparison(a);
        html += this._renderPixelDiffs(a);
        html += this._renderSpatialDist(a);
        html += this._renderHistogramStats(a);
        html += this._renderAdvanced(a);
        html += '<div id="histogram-charts"></div>';
        html += this._renderLSBAnalysis(a.bit_plane_analysis);
        
        el.innerHTML = html;
        this.toggleResult(id, true);
        if (a.histogram_original && a.histogram_stego) {
            setTimeout(() => this.renderHistograms(a), 100);
        }
    }

    _renderStealthScore(a) {
        const sm = a.stealth_metrics || {};
        const risk = (sm.chi_square_risk * 100).toFixed(2);
        return `
        <div class="stats-grid">
            <div class="stat-card"><h4>Stealth Score</h4><div class="value">${sm.stealth_score?.toFixed(1)}<span class="unit">/100</span></div></div>
            <div class="stat-card"><h4>Chi-Square Risk</h4><div class="value">${risk}<span class="unit">%</span></div><div class="quality-indicator">${risk < 50 ? 'Safe' : 'High'}</div></div>
            <div class="stat-card"><h4>Freq Fidelity</h4><div class="value">${sm.frequency_fidelity?.toFixed(4)}</div><div class="quality-indicator">Excellent</div></div>
        </div>`;
    }

    _renderQualityMetrics(a) {
        return `
        <div class="analysis-section">
            <h2>Image Quality Metrics</h2>
            <div class="stats-grid">
                <div class="stat-card"><h4>PSNR</h4><div class="value">${a.psnr?.toFixed(2)}<span class="unit">dB</span></div></div>
                <div class="stat-card"><h4>MSE</h4><div class="value">${a.mse?.toFixed(6)}</div></div>
                <div class="stat-card"><h4>SSIM</h4><div class="value">${a.ssim?.toFixed(4)}</div></div>
            </div>
        </div>`;
    }

    _renderComparison(a) {
        return `
        <div class="analysis-section">
            <h2>Image Comparison</h2>
            <div class="image-grid">
                <div class="image-item"><h4>Original</h4><img src="data:image/png;base64,${a.original_image}"></div>
                <div class="image-item"><h4>Stego Result</h4><img src="data:image/png;base64,${a.stego_image}"></div>
            </div>
        </div>`;
    }

    _renderPixelDiffs(a) {
        const d = a.pixel_differences?.overall || {};
        return `
        <div class="analysis-section">
            <h2>Pixel Differences</h2>
            <div class="stats-grid">
                <div class="mini-stat"><span class="label">Changed Pixels</span><span class="value">${d.percent_changed?.toFixed(4)}%</span></div>
                <div class="mini-stat"><span class="label">Total Variation Diff</span><span class="value">${(d.total_variation_diff * 100).toFixed(6)}%</span></div>
                <div class="mini-stat"><span class="label">Mean Difference</span><span class="value">${d.mean_difference?.toFixed(6)}</span></div>
                <div class="mini-stat"><span class="label">Std Deviation</span><span class="value">${d.std_difference?.toFixed(6) || 0}</span></div>
            </div>
        </div>`;
    }

    _renderSpatialDist(a) {
        if (!a.spatial_distribution) return '';
        let rows = Object.entries(a.spatial_distribution).map(([name, data]) => `
            <div class="mini-stat"><span class="label">${name}</span><span class="value">${data.percent_changed.toFixed(4)}% | U:${data.uniformity.toFixed(4)}</span></div>
        `).join('');
        return `<div class="analysis-section"><h2>Spatial Distribution</h2><div class="stats-grid">${rows}</div></div>`;
    }

    _renderHistogramStats(a) {
        const s = a.histogram_statistics?.red || a.histogram_statistics || {};
        return `
        <div class="analysis-section">
            <h2>Histogram Statistics</h2>
            <div class="stats-grid">
                <div class="mini-stat"><span class="label">KL Divergence</span><span class="value">${(s.kl_divergence || 0).toFixed(6)}</span></div>
                <div class="mini-stat"><span class="label">Difference</span><span class="value">${(s.histogram_difference || 0).toFixed(4)}</span></div>
                <div class="mini-stat"><span class="label">Entropy Orig</span><span class="value">${(s.entropy_original || 0).toFixed(4)}</span></div>
                <div class="mini-stat"><span class="label">Entropy Stego</span><span class="value">${(s.entropy_stego || 0).toFixed(4)}</span></div>
            </div>
        </div>`;
    }

    _renderAdvanced(a) {
        const n = a.noise_analysis || {};
        return `
        <div class="analysis-section">
            <h2>Advanced Analysis</h2>
            <div class="stats-grid">
                <div class="mini-stat"><span class="label">SNR</span><span class="value">${n.snr?.toFixed(2)}dB</span></div>
                <div class="mini-stat"><span class="label">Noise Std</span><span class="value">${n.noise_std?.toFixed(6)}</span></div>
                <div class="mini-stat"><span class="label">Correlation</span><span class="value">${a.correlation_analysis?.overall_correlation?.toFixed(6)}</span></div>
            </div>
        </div>`;
    }

    _renderLSBAnalysis(bpa) {
        if (!bpa) return '';
        let sections = Object.entries(bpa).map(([ch, bits]) => {
            let cards = Object.entries(bits).map(([num, data]) => `
                <div class="bit-plane-card">
                    <h4>${num.toUpperCase()}</h4>
                    <img src="data:image/png;base64,${data.image}">
                    <div class="mini-stat"><span class="value">${data.entropy.toFixed(3)}</span></div>
                </div>`).join('');
            return `<div class="analysis-section lsb-section"><h2>${ch.toUpperCase()}</h2><div class="bit-planes-grid">${cards}</div></div>`;
        }).join('');
        return `<div class="analysis-section"><h2>Bit Plane Analysis</h2>${sections}</div>`;
    }

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
    }

    renderHistograms(a) {
        const ctx = document.getElementById('histogram-charts');
        if (!ctx) return;
        
        ctx.innerHTML = '<h2>Spectral Histogram Analysis</h2><div class="image-grid" id="hist-container"></div>';
        const container = document.getElementById('hist-container');
        
        const channels = [
            { id: 'red', name: 'Red Channel', color: '#ff4444' },
            { id: 'green', name: 'Green Channel', color: '#44ff44' },
            { id: 'blue', name: 'Blue Channel', color: '#4444ff' }
        ];

        channels.forEach(ch => {
            const chartDiv = document.createElement('div');
            chartDiv.className = 'chart-container';
            chartDiv.innerHTML = `<h4 style="margin-bottom:10px; color:#aaa; font-size:0.65rem;">${ch.name.toUpperCase()}</h4><canvas id="hist-${ch.id}"></canvas>`;
            container.appendChild(chartDiv);

            const config = {
                type: 'line',
                data: {
                    labels: Array.from({length: 256}, (_, i) => i),
                    datasets: [
                        { label: 'Original', data: a.histogram_original[ch.id], borderColor: '#444', borderWidth: 1.5, fill: false, pointRadius: 0 },
                        { label: 'Stego', data: a.histogram_stego[ch.id], borderColor: ch.color, borderWidth: 1.5, fill: false, pointRadius: 0 }
                    ]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: { 
                        y: { display: false },
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#666', font: { size: 8 } } }
                    }, 
                    plugins: { legend: { display: false } } 
                }
            };
            new Chart(document.getElementById(`hist-${ch.id}`), config);
        });
    }
}

export default new UIManager();
