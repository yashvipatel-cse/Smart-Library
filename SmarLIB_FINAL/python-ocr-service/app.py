"""
Smart Library — Python OCR Service  (v5 — FIXED)
─────────────────────────────────────────────────
Routes:
  POST /process-image  ← frontend sends shelf photo
  GET  /health         ← frontend health check

Changes from v4:
  - CORS properly configured (no console errors)
  - Reads from unified `books` table via books.csv (book_number column)
  - Full-image OCR fallback when YOLO finds 0 boxes
  - Tesseract auto-detects OS path
"""

"""
Smart Library — Python OCR Service + RFID (FINAL v6)
"""

import csv
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from model import process_image

app = Flask(__name__)

# 🔥 ADD (for frontend live RFID)
last_rfid = None

# ── CORS ─────────────────────────────────────────
CORS(app, resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "OPTIONS"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── FULL SUBJECT MAP ─────────────────────────────
SUBJECT_MAP = {
    "Mathematics": ("Rack-1", "A1"),
    "Physics": ("Rack-2", "A2"),
    "Chemistry (B.Sc)": ("Rack-3", "A3"),
    "chemistry (B.Sc)": ("Rack-3", "A3"),
    "Chemistry (M.Sc)": ("Rack-3", "A3"),
    "Biotechnology (B.Sc)": ("Rack-4", "B1"),
    "Biotechnology (M.Sc)": ("Rack-4", "B1"),
    "B.Sc. (Microbiology)": ("Rack-4", "B1"),
    "Statistics, Biometry": ("Rack-4", "B1"),
    "Computer Engineering (B.Tech)": ("Rack-5", "B2"),
    "BCA": ("Rack-5", "B2"),
    "Bachelor of Computer Application": ("Rack-5", "B2"),
    "Computer": ("Rack-5", "B2"),
    "Data Science (B.Sc)": ("Rack-5", "B2"),
    "B.Sc. (Data Science)": ("Rack-5", "B2"),
    "Data Science (M.Sc)": ("Rack-5", "B2"),
    "Mechanical Engineering (B.Tech)": ("Rack-6", "B3"),
    "Chemical Engineering (B.Tech)": ("Rack-7", "C1"),
    "Civil Engineering (B.Tech)": ("Rack-8", "C2"),
    "Fire And Environment, Health, Safety (B.Tech)": ("Rack-8", "C2"),
    "Fire & safety engineering, Hydraulics engineering": ("Rack-8", "C2"),
    "Fire & safety engineering, Industrial safety, and occupational health and safety": ("Rack-8", "C2"),
    "Management (MBA)": ("Rack-9", "C3"),
    "Management (BBA)": ("Rack-9", "C3"),
    "Management (BBA-BA)": ("Rack-9", "C3"),
    "Management (B com)": ("Rack-9", "C3"),
    "Management (Bcom)": ("Rack-9", "C3"),
    "School of Management": ("Rack-9", "C3"),
    "General Collection": ("Rack-10", "D1"),
    "Soft & Technical Skills": ("Rack-10", "D1"),
    "Law": ("Rack-10", "D1"),
    "Start-up (SSIP)": ("Rack-11", "D2"),
}

# ── LOAD BOOKS ───────────────────────────────────
def load_book_lookup():
    lookup = {}
    here = os.path.dirname(__file__)

    candidates = [
        os.path.join(here, "..", "backend", "books.csv"),
        os.path.join(here, "books.csv"),
    ]

    csv_path = next((p for p in candidates if os.path.exists(p)), None)

    if not csv_path:
        print("❌ books.csv not found")
        return lookup

    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader)

            for row in reader:
                if not row or not row[0].strip():
                    continue

                code = row[0].strip().upper()
                title = row[1].strip() if len(row) > 1 else ""
                author = row[2].strip() if len(row) > 2 else ""
                subject = row[9].strip() if len(row) > 9 else ""

                title = re.sub(r'^Normal view MARC view ISBD view\s*', "", title).strip()

                rack, shelf = SUBJECT_MAP.get(subject, ("Rack-1", "A1"))

                lookup[code] = {
                    "title": title,
                    "author": author,
                    "subject": subject,
                    "rack": rack,
                    "expectedShelf": shelf,
                }

        print(f"✅ Loaded {len(lookup)} books")

    except Exception as e:
        print("❌ CSV ERROR:", e)

    return lookup


BOOK_LOOKUP = load_book_lookup()

# ── OCR ROUTE ────────────────────────────────────
@app.route("/process-image", methods=["POST", "OPTIONS"])
def process():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    safe = re.sub(r"[^\w.\-]", "_", file.filename or "upload.jpg")
    path = os.path.join(UPLOAD_FOLDER, safe)
    file.save(path)

    result = process_image(path, BOOK_LOOKUP)
    return jsonify(result)

# ── HEALTH ROUTE ─────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "books_loaded": len(BOOK_LOOKUP),
        "version": "v6 + RFID",
    })

# ── RFID ROUTE ───────────────────────────────────
@app.route("/rfid", methods=["POST"])
def receive_rfid():
    try:
        global last_rfid
        data = request.json
        uid = (data.get("uid") or "").upper()

        last_rfid = uid  # 🔥 store latest UID

        print("📡 RFID Card Scanned:", uid)

        if uid in BOOK_LOOKUP:
            book = BOOK_LOOKUP[uid]
            print("✅ Book Found:", book["title"])

            return jsonify({
                "status": "found",
                "uid": uid,
                "book": book
            })
        else:
            print("❌ Unknown RFID")

            return jsonify({
                "status": "not_found",
                "uid": uid
            })

    except Exception as e:
        print("RFID ERROR:", e)
        return jsonify({"error": str(e)}), 500


# 🔥 NEW: FRONTEND LIVE RFID API
@app.route("/rfid/latest", methods=["GET"])
def get_latest_rfid():
    return jsonify({"uid": last_rfid})


# ── RUN SERVER ───────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Smart Library System (OCR + RFID)")
    print(f"📚 Books Loaded: {len(BOOK_LOOKUP)}")
    print("🌐 Server ready for ESP32")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5001, debug=False)