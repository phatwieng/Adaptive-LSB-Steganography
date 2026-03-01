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
        if (!el) return;
        const txt = el.querySelector('.result-text');
        if (txt) txt.textContent = msg;
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
        let html = '<div class="analysis-section">' + this._renderStealthScore(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderQualityMetrics(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderComparison(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderPixelDiffs(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderSpatialDist(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderHistogramStats(a) + '</div>';
        html += '<div class="analysis-section">' + this._renderAdvanced(a) + '</div>';
        html += '<div id="histogram-charts"></div>';
        html += '<div class="analysis-section">' + this._renderLSBAnalysis(a.bit_plane_analysis) + '</div>';
        
        el.innerHTML = html;
        this.toggleResult(id, true);
        if (a.histogram_original && a.histogram_stego) {
            setTimeout(() => this.renderHistograms(a), 100);
        }
    }

    _renderStealthScore(a) {
        const sm = a.stealth_metrics || {};
        const rs = (sm.rs_estimate * 100).toFixed(2);
        const spa = (sm.spa_estimate * 100).toFixed(2);
        const chi = (sm.chi_square_risk * 100).toFixed(2);
        
        return `
        <h2>Forensic Steganalysis Diagnostics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h4>RS Analysis</h4>
                <div class="value">${rs}<span class="unit">%</span></div>
                <div class="quality-indicator" style="background:${sm.rs_estimate < 0.05 ? '#2ecc71' : '#e74c3c'} !important;">
                    ${sm.rs_estimate < 0.05 ? 'SECURE' : 'DETECTION RISK'}
                </div>
            </div>
            <div class="stat-card">
                <h4>Sample Pair (SPA)</h4>
                <div class="value">${spa}<span class="unit">%</span></div>
                <div class="quality-indicator" style="background:${sm.spa_estimate < 0.05 ? '#2ecc71' : '#e74c3c'} !important;">
                    ${sm.spa_estimate < 0.05 ? 'SECURE' : 'DETECTION RISK'}
                </div>
            </div>
            <div class="stat-card">
                <h4>Chi-Square Risk</h4>
                <div class="value">${chi}<span class="unit">%</span></div>
                <div class="quality-indicator" style="background:${sm.chi_square_risk < 0.5 ? '#2ecc71' : '#e74c3c'} !important;">
                    ${sm.chi_square_risk < 0.5 ? 'LOW' : 'HIGH'}
                </div>
            </div>
            <div class="stat-card">
                <h4>Stealth Score</h4>
                <div class="value">${sm.stealth_score?.toFixed(1)}<span class="unit">/100</span></div>
            </div>
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
            return `<h3 style="margin: 20px 0 10px; font-family: var(--mono); font-size: 0.8rem; color: var(--yellow);">${ch.toUpperCase()} BIT PLANES</h3><div class="bit-planes-grid">${cards}</div>`;
        }).join('');
        return `<h2>Bit Plane Analysis</h2>${sections}`;
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
        
        // Wrap everything in a single analysis-section to fix "hanging" content
        ctx.innerHTML = '<div class="analysis-section"><h2>Spectral Histogram Analysis</h2><div id="hist-container" style="display:flex; flex-direction:column; gap:25px;"></div></div>';
        const container = document.getElementById('hist-container');
        
        const channels = [
            { id: 'red', name: 'Red Channel', color: '#ff4444' },
            { id: 'green', name: 'Green Channel', color: '#44ff44' },
            { id: 'blue', name: 'Blue Channel', color: '#4444ff' }
        ];

        channels.forEach(ch => {
            const chartDiv = document.createElement('div');
            chartDiv.className = 'chart-container';
            chartDiv.style.cssText = 'background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); border-left: 2px solid ' + ch.color + '; padding: 16px 12px 12px; border-radius: 4px;';
            chartDiv.innerHTML = `<h4 style="margin-bottom:12px; color:#ccc; font-size:0.8rem; letter-spacing:0.12em;">${ch.name.toUpperCase()}</h4><canvas id="hist-${ch.id}" style="height:160px;"></canvas>`;
            container.appendChild(chartDiv);

            const config = {
                type: 'line',
                data: {
                    labels: Array.from({length: 256}, (_, i) => i),
                    datasets: [
                        { label: 'Original', data: a.histogram_original[ch.id], borderColor: '#cccccc', borderWidth: 1, fill: false, pointRadius: 0 },
                        { label: 'Stego', data: a.histogram_stego[ch.id], borderColor: ch.color, borderWidth: 1.5, fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: { padding: { left: 4, right: 16, top: 8, bottom: 4 } },
                    scales: {
                        y: {
                            display: true,
                            title: { display: true, text: 'PIXEL DENSITY', color: '#999', font: { size: 9, weight: 'bold' } },
                            grid: { color: 'rgba(255,255,255,0.07)', lineWidth: 1 },
                            border: { color: 'rgba(255,255,255,0.15)' },
                            ticks: { color: '#888', font: { size: 8 }, maxTicksLimit: 6 }
                        },
                        x: {
                            display: true,
                            title: { display: true, text: 'INTENSITY (0-255)', color: '#999', font: { size: 9, weight: 'bold' } },
                            grid: { color: 'rgba(255,255,255,0.07)', lineWidth: 1 },
                            border: { color: 'rgba(255,255,255,0.15)' },
                            ticks: { color: '#888', font: { size: 9 }, maxTicksLimit: 16 }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            align: 'end',
                            labels: { color: '#bbb', font: { size: 10 }, boxWidth: 10, usePointStyle: true }
                        }
                    }
                }
            };
            new Chart(document.getElementById(`hist-${ch.id}`), config);
        });
    }
}

export default new UIManager();