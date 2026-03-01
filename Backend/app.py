from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import io, os, tempfile, base64, sys
import numpy as np
import logging
from werkzeug.utils import secure_filename
from PIL import Image

# ── CORE FUNCTIONS ──
from Functions.Stego import encode_message, decode_message, get_image_stats
from Analyze.image_analyzer import comprehensive_analysis

# ── CONFIGURATION ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(BASE_DIR, "flask_errors.log")), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── IMAGE SETTINGS ──
Image.MAX_IMAGE_PIXELS = 2000000000
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024 * 1024 # 50 GB
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp", "tiff", "tif"}
HEADER_BYTES = 4
upload_sessions = {}

# ── UTILS ──
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def estimate_encrypted_size(text):
    return len(text.encode("utf-8")) + 32 # AES/Hamming overhead

def image_to_base64(path):
    with Image.open(path) as img:
        img.thumbnail((256, 256))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

def sanitize_data(data):
    if isinstance(data, dict): return {k: sanitize_data(v) for k, v in data.items()}
    if isinstance(data, list): return [sanitize_data(v) for v in data]
    if isinstance(data, (float, np.floating)): return 0.0 if np.isnan(data) or np.isinf(data) else float(data)
    if isinstance(data, (np.integer, np.uint8, np.int64)): return int(data)
    return data

# ── ROUTES: STATIC ──
@app.route("/")
def index():
    for f in ["dist", "Frontend"]:
        p = os.path.join(PROJECT_ROOT, f, "index.html")
        if os.path.exists(p): return send_file(p)
    return jsonify({"error": "Frontend not found"}), 404

@app.route("/<path:path>")
def serve_static(path):
    for f in ["dist", "Frontend"]:
        d = os.path.join(PROJECT_ROOT, f)
        if os.path.exists(os.path.join(d, path)): return send_from_directory(d, path)
    return jsonify({"error": "File not found"}), 404

# ── API: UPLOAD ──
@app.route("/api/upload-chunk", methods=["POST"])
def upload_chunk():
    try:
        chunk = request.files["chunk"]
        idx, total = int(request.form["index"]), int(request.form["total"])
        sid, fname = request.form["sessionId"], secure_filename(request.form["filename"])
        
        tdir = os.path.join(UPLOAD_FOLDER, sid)
        os.makedirs(tdir, exist_ok=True)
        
        with open(os.path.join(tdir, f"chunk_{idx}"), "wb") as f: f.write(chunk.read())
        
        if idx == total - 1:
            out_path = os.path.join(UPLOAD_FOLDER, f"{sid}_{fname}")
            with open(out_path, "wb") as f:
                for i in range(total):
                    cp = os.path.join(tdir, f"chunk_{i}")
                    with open(cp, "rb") as cf: f.write(cf.read())
                    os.remove(cp)
            os.rmdir(tdir)
            upload_sessions[sid] = {"path": out_path, "filename": fname}
            return jsonify({"success": True, "complete": True})
        return jsonify({"success": True, "complete": False})
    except Exception as e:
        logger.error(f"Chunk error: {e}")
        return jsonify({"error": str(e)}), 500

# ── API: ACTIONS ──
@app.route("/api/encode-final", methods=["POST"])
def encode_final():
    try:
        ipath, msg, pwd = request.json['filePath'], request.json['message'], request.json['password']
        ipath = os.path.join(UPLOAD_FOLDER, ipath)
        
        if not os.path.exists(ipath): return jsonify({"error": "File not found"}), 404

        ext = os.path.splitext(ipath)[1].lower()
        opath = os.path.join(os.path.dirname(ipath), f"encoded{ext}")

        stats = get_image_stats(ipath, real_capacity=True)
        if (estimate_encrypted_size(msg) + HEADER_BYTES) * 8 > stats["practical_max_bits"]:
            return jsonify({"error": "Capacity exceeded"}), 400

        encode_message(ipath, msg, pwd, opath)
        
        # Format detection
        if not os.path.exists(opath):
            bpath = os.path.splitext(opath)[0] + ".bmp"
            if os.path.exists(bpath): opath = bpath

        res = send_file(opath, as_attachment=True, download_name=os.path.basename(opath))
        
        @res.call_on_close
        def cleanup():
            import shutil
            try: os.remove(ipath); os.remove(opath)
            except: pass
        return res
    except Exception as e:
        logger.exception("Final encode error")
        return jsonify({"error": str(e)}), 500

@app.route("/api/decode", methods=["POST"])
def decode():
    try:
        f, pwd = request.files["image"], request.form["password"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1]) as tmp:
            f.save(tmp.name)
            msg = decode_message(tmp.name, pwd)
            os.remove(tmp.name)
            
        if msg.startswith("Error:"): return jsonify({"success": False, "error": msg}), 400
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/capacity", methods=["POST"])
def capacity():
    try:
        f = request.files["image"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1]) as tmp:
            f.save(tmp.name)
            stats = get_image_stats(tmp.name, real_capacity=True)
            os.remove(tmp.name)
        return jsonify({"success": True, "capacity": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze", methods=["POST"])
def analyze():
    with tempfile.TemporaryDirectory() as tdir:
        try:
            paths = {}
            for k in ["original", "stego"]:
                f = request.files[k]
                paths[k] = os.path.join(tdir, f"{k}.png")
                f.save(paths[k])

            results = comprehensive_analysis(paths["original"], paths["stego"])
            if "error" in results: return jsonify({"success": False, "error": results["error"]}), 500

            results.update({
                "original_image": image_to_base64(paths["original"]),
                "stego_image": image_to_base64(paths["stego"]),
                "success": True
            })
            return jsonify(sanitize_data(results))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)), host="0.0.0.0", threaded=True)
