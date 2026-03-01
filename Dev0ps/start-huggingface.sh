#!/bin/bash

# ── STARTUP ──
# Hugging Face needs the server on port 7860
# We run the Flask backend on 7860 and serve the built Frontend static files
export PORT=7860
export FLASK_ENV=production

echo "Starting Steganography Suite on Port $PORT..."
python Backend/app.py
