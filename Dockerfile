# Use a multi-stage build for a lean final image
FROM python:3.11-slim

# ── SYSTEM DEPENDENCIES ──
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── BACKEND SETUP ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── FRONTEND SETUP ──
COPY package.json package-lock.json ./
RUN npm install

# ── COPY SOURCE ──
COPY . .

# ── BUILD FRONTEND ──
RUN npm run build

# ── PERMISSIONS ──
RUN mkdir -p Backend/uploads && chmod 777 Backend/uploads

# ── EXPOSE ──
EXPOSE 7860

# ── START SCRIPT ──
CMD ["bash", "Dev0ps/start-huggingface.sh"]
