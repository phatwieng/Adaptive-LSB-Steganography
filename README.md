---
title: Adaptive LSB Steganography
emoji: 🛡️
colorFrom: yellow
colorTo: black
sdk: docker
app_port: 7860
pinned: false
---

# ── Steganography Suite ──

A High-Security Adaptive Steganography Suite designed for professional-grade data concealment within images. Optimized for **gigapixel processing (up to 32k x 32k)** with absolute data integrity.

## ── CORE ARCHITECTURE ──

*   **Adaptive Embedding Engine**: Analyzes local pixel complexity (edges, textures, color zones) to dynamically hide data where it is least detectable.
*   **Secure Pipeline**:
    1.  **AES-256 Encryption**: Ensures data confidentiality.
    2.  **Hamming(7,4) ECC**: Adds error correction redundancy.
    3.  **Deterministic LCG Mapping**: Platform-independent data path synchronization.
*   **Zero-RAM Streaming**: Uses memory-mapping to handle 1.5GB+ files without system crashes.

## ── KEY FUNCTIONS ──

### 1. Encode (Concealment)
*   **Multi-Language**: Full UTF-8 support (Thai, Arabic, etc.).
*   **Format Intelligence**: Automatically forces Lossless PNG for standard images and Raw BMP for huge images (>16k).
*   **Adaptive Masking**: Protects sensitive color zones (skin tones, foliage).

### 2. Decode (Extraction)
*   **Perfect Symmetry**: Mirrored extraction retrieves data via the exact same path.
*   **Exact Truncation**: Extracts precise payload length using a deterministic 32-bit header.

### 3. Deep Analysis (Steganalysis)
*   **Stochastic Sampling**: Analyzes 128 random full-res blocks for fast, accurate metrics on huge images.
*   **Advanced Metrics**: PSNR (64-bit), MSE, and SSIM.
*   **Chi-Square Risk**: Granular LSB-pairing attack detection.
*   **Visual Diagnostics**: Bit-Plane slicing and Spectral Histograms.

## ── DEPLOYMENT ──

### Local Development
1.  Install dependencies: `pip install -r requirements.txt` and `npm install`.
2.  Start servers: `npm run start:dev`.
3.  Access at `http://localhost:3000`.

### Docker / Hugging Face
This project is container-ready. Use the provided `Dockerfile` for deployment to Hugging Face Spaces or any Docker-compatible hosting.

---
*Developed for high-resolution security research.*
