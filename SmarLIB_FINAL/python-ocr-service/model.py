"""
Smart Library — model.py  (v10 — CLAUDE VISION + TESSERACT HYBRID)
══════════════════════════════════════════════════════════════════════
ARCHITECTURE (in order of priority):
  1. Claude Vision API  — sends image tiles to Claude Vision
                          which reads tiny sticker text far better than Tesseract
  2. YOLO + Tesseract   — per-spine crop OCR with deskew & 5 preprocessing variants
  3. Strip OCR          — overlapping tile scan of the bottom label band

REAL-WORLD IMPROVEMENTS over v9:
  - Claude Vision reads stickers at ANY angle, ANY contrast, ANY size
  - Image is split into overlapping tiles before Vision API call
    so small stickers are never lost in a large image
  - Tesseract whitelist expanded; Dewey+accession regex improved
  - Vision API and Tesseract run concurrently (background thread)
  - Returns per-book confidence + detection method for debugging

REQUIREMENTS:
  pip install anthropic opencv-python pytesseract ultralytics numpy

ENVIRONMENT:
  Set ANTHROPIC_API_KEY in your environment, OR pass api_key= to process_image().
  If key is missing, Vision API pass is skipped (Tesseract only fallback).
"""

import cv2
import pytesseract
import re
import os
import sys
import base64
import json
import threading
import numpy as np
from ultralytics import YOLO
from collections import Counter

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False
    print("[WARN] anthropic package not installed. Run: pip install anthropic")

# ── Tesseract path (Windows only) ──────────────────────────────
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Load YOLO model ────────────────────────────────────────────
_model_path = os.path.join(os.path.dirname(__file__), "best.pt")
model = None
try:
    model = YOLO(_model_path if os.path.exists(_model_path) else "yolov8n.pt")
    print(f"[MODEL] YOLO loaded: {_model_path if os.path.exists(_model_path) else 'yolov8n.pt (fallback)'}")
except Exception as e:
    print(f"[MODEL ERROR] {e}")

# ── Tesseract configs ───────────────────────────────────────────
_WL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789. "
_TESS_CONFIGS = [
    f"--psm 6  --oem 3 -c tessedit_char_whitelist={_WL}",
    f"--psm 11 --oem 3 -c tessedit_char_whitelist={_WL}",
    f"--psm 7  --oem 3 -c tessedit_char_whitelist={_WL}",
    "--psm 11 --oem 3",  # no whitelist — catches unusual sticker formats
]

# ── Code extraction patterns ───────────────────────────────────
_CODE_RE  = re.compile(r'\bB(\d{3,5})\b')
_DEWEY_RE = re.compile(r'\d{3}[.,]\d+\s+[A-Z]{2,5}\s+(B\d{3,5})', re.I)
_ACC_RE   = re.compile(r'[A-Z]{2,5}\s+(B\d{3,5})', re.I)
_OCR_FIX  = str.maketrans({'O': '0', 'Q': '0', 'I': '1', 'L': '1'})


# ─────────────────────────────────────────────────────────────
# CODE NORMALISATION
# ─────────────────────────────────────────────────────────────
def _fix(s: str) -> str:
    return s.upper().translate(_OCR_FIX)

def _normalise(raw: str):
    raw = _fix(str(raw).strip())
    m = re.match(r'^B(\d{3,5})$', raw)
    if not m:
        return None
    num = int(m.group(1))
    if not (1 <= num <= 99999):
        return None
    return f"B{num:04d}" if num < 1000 else f"B{num}"

def extract_codes(text: str) -> list:
    found = set()
    upper = text.upper()
    for m in _DEWEY_RE.finditer(upper):
        c = _normalise(m.group(1))
        if c: found.add(c)
    for m in _ACC_RE.finditer(upper):
        c = _normalise(m.group(1))
        if c: found.add(c)
    for token in re.split(r'[\s\n]+', upper):
        token = _fix(token)
        for m in _CODE_RE.finditer(token):
            c = _normalise('B' + m.group(1))
            if c: found.add(c)
    return list(found)

def lookup_code(code: str, book_lookup: dict):
    if code in book_lookup:
        return book_lookup[code], code
    try:
        num = int(code[1:])
    except ValueError:
        return None, code
    for fmt in [f"B{num:04d}", f"B{num:05d}", f"B{num:03d}", f"B{num}"]:
        if fmt in book_lookup:
            return book_lookup[fmt], fmt
    return None, code


# ─────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────
def img_to_base64(img_bgr, quality: int = 90) -> str:
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode()

def deskew(img_bgr):
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, max(10, gray.shape[1] // 6))
    if lines is None:
        return img_bgr
    angles = []
    for line in lines[:30]:
        a = np.degrees(line[0][1]) - 90
        if -45 <= a <= 45:
            angles.append(a)
    if not angles:
        return img_bgr
    med = float(np.median(angles))
    if abs(med) < 0.5:
        return img_bgr
    h, w = img_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), med, 1.0)
    return cv2.warpAffine(img_bgr, M, (w, h),
                           flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_REPLICATE)

def preprocess_variants(img_bgr):
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h     = gray.shape[0]
    scale = max(2, min(8, 80 // max(h, 1)))
    up    = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    out   = []
    b1    = cv2.GaussianBlur(up, (3, 3), 0)
    _, ot = cv2.threshold(b1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out  += [ot, cv2.bitwise_not(ot)]
    b2    = cv2.GaussianBlur(up, (5, 5), 0)
    ad    = cv2.adaptiveThreshold(b2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
    out  += [ad, cv2.bitwise_not(ad)]
    cl    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(up)
    _, co = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out.append(co)
    return out


# ─────────────────────────────────────────────────────────────
# TESSERACT OCR
# ─────────────────────────────────────────────────────────────
def ocr_region(img_bgr, do_deskew=False) -> list:
    if img_bgr is None or img_bgr.size == 0:
        return []
    if do_deskew:
        img_bgr = deskew(img_bgr)
    codes = set()
    for variant in preprocess_variants(img_bgr):
        for cfg in _TESS_CONFIGS:
            try:
                codes.update(extract_codes(
                    pytesseract.image_to_string(variant, config=cfg)))
            except Exception:
                pass
    return list(codes)


# ─────────────────────────────────────────────────────────────
# CLAUDE VISION API — PRIMARY DETECTOR
# ─────────────────────────────────────────────────────────────
_VISION_PROMPT = """You are a library inventory scanning system.

Look carefully at this image of a library shelf.
Find EVERY white label sticker attached to the bottom of each book spine.

Each sticker looks like this (4 lines, printed text):
  005.74          ← Dewey decimal (top line — IGNORE)
  SIL             ← Author code   (2nd line  — IGNORE)
  B5619           ← Accession number (3rd line — THIS IS WHAT I NEED)
  GSFCU LIBRARY   ← Library stamp (bottom     — IGNORE)

Your task: Return a JSON array containing ONLY the accession numbers.
Format: ["B5619","B7826","B6030"]

Rules:
- Accession numbers always start with capital B followed by 3-5 digits
- Include ALL visible accession numbers, even if partially visible
- Do NOT include Dewey numbers, author codes, or library names
- If you cannot find any accession numbers, return []
- Respond with ONLY the JSON array — no explanation, no markdown"""

def claude_vision_detect(img_bgr, api_key: str = None) -> list:
    """
    Primary detector: sends image tiles to Claude Vision API.
    Returns list of normalised code strings e.g. ['B5619', 'B7826'].
    """
    if not _ANTHROPIC_AVAILABLE:
        return []
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("[VISION] No API key — skipping Vision pass")
        return []

    client = anthropic.Anthropic(api_key=key)
    h, w   = img_bgr.shape[:2]
    codes  = set()

    # ── Build tile list ──────────────────────────────────────
    tiles = []

    # 1. Full image (downscaled to 1600px max)
    scale = min(1.0, 1600 / max(w, h))
    small = cv2.resize(img_bgr, None, fx=scale, fy=scale) if scale < 1.0 else img_bgr.copy()
    tiles.append(("full", small))

    # 2. Bottom 40% — label strip region — split into 3 overlapping thirds
    bot_y = int(h * 0.58)
    bottom = img_bgr[bot_y:, :]
    bh, bw = bottom.shape[:2]
    for i in range(3):
        x1 = max(0, int(bw * i / 3) - int(bw * 0.08))
        x2 = min(bw, int(bw * (i + 1) / 3) + int(bw * 0.08))
        tile = bottom[:, x1:x2]
        # Upscale so each sticker is at least 40px tall
        ts = min(4.0, 160 / max(bh, 1))
        if ts > 1.1:
            tile = cv2.resize(tile, None, fx=ts, fy=ts, interpolation=cv2.INTER_CUBIC)
        tiles.append((f"bot_{i}", tile))

    # ── Call API per tile ────────────────────────────────────
    for tile_name, tile_img in tiles:
        b64 = img_to_base64(tile_img, quality=95)
        try:
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": _VISION_PROMPT}
                    ],
                }]
            )
            raw = response.content[0].text.strip()
            # Strip any accidental preamble / markdown fences
            raw = re.sub(r'^[^[]*', '', raw)
            raw = re.sub(r'[^\]]*$', '', raw)
            if raw:
                try:
                    parsed = json.loads(raw)
                    for item in parsed:
                        c = _normalise(str(item))
                        if c: codes.add(c)
                except json.JSONDecodeError:
                    # Fallback extraction from raw text
                    for c in extract_codes(raw):
                        if c: codes.add(c)
            print(f"[VISION] {tile_name}: found {sorted(codes)}")
        except Exception as e:
            print(f"[VISION] {tile_name} error: {e}")

    return list(codes)


# ─────────────────────────────────────────────────────────────
# LABEL STRIP DETECTION
# ─────────────────────────────────────────────────────────────
def find_label_strip(img_bgr):
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    start = h // 3
    bottom = gray[start:, :]
    row_br = np.mean(bottom, axis=1)
    k = max(3, h // 40) | 1
    smoothed = cv2.GaussianBlur(
        row_br.reshape(-1, 1).astype(np.float32), (1, k), 0).flatten()
    peak  = smoothed.max()
    bright = np.where(smoothed >= peak * 0.80)[0]
    if len(bright) == 0:
        return 0.62, 1.0
    y0r = int(bright[0]); y1r = int(bright[-1]) + 1
    bh  = max(1, y1r - y0r)
    pad = max(30, int(bh * 2.5))
    y0a = max(start, start + y0r - pad)
    y1a = min(h, start + y1r + 25)
    return y0a / h, y1a / h


# ─────────────────────────────────────────────────────────────
# STRIP TILE OCR (Tesseract fallback)
# ─────────────────────────────────────────────────────────────
def strip_tile_ocr(strip_bgr, book_lookup: dict) -> set:
    found = set()
    w = strip_bgr.shape[1]
    # Full strip
    for c in ocr_region(strip_bgr, do_deskew=True):
        if c in book_lookup: found.add(c)
    # Overlapping tiles at 3 widths
    for tw in [60, 90, 130]:
        step = max(1, tw - 25)
        x = 0
        while x < w:
            tile = strip_bgr[:, x:min(w, x + tw)]
            for c in ocr_region(tile):
                if c in book_lookup: found.add(c)
            x += step
    return found


# ─────────────────────────────────────────────────────────────
# AUTO-DETECT SHELF
# ─────────────────────────────────────────────────────────────
def auto_detect_shelf(book_results: list) -> str:
    shelves = [r["expectedShelf"] for r in book_results
               if r.get("found") and r.get("expectedShelf")]
    if not shelves: return "UNKNOWN"
    return Counter(shelves).most_common(1)[0][0]


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────
def process_image(path: str,
                  book_lookup: dict = None,
                  api_key: str = None) -> dict:
    """
    Parameters
    ----------
    path        : path to the shelf image file
    book_lookup : {code: {title, author, rack, subject, expectedShelf, ...}}
    api_key     : Anthropic API key (or set ANTHROPIC_API_KEY env var)

    Returns
    -------
    dict with keys: codes, detections, books, detectedShelf,
                    annotated_image (base64 jpg), total_matched, used_fallback
    """
    book_lookup = book_lookup or {}

    img = cv2.imread(path)
    if img is None:
        return {"error": "Cannot read image", "books": [], "codes": [],
                "detections": 0, "annotated_image": None,
                "detectedShelf": "UNKNOWN"}

    h, w         = img.shape[:2]
    annotated    = img.copy()
    seen_codes   = set()
    book_results = []

    # ── Find label strip ─────────────────────────────────────
    y_frac_start, y_frac_end = find_label_strip(img)
    sy1 = int(h * y_frac_start)
    sy2 = int(h * y_frac_end)
    print(f"[STRIP] y={y_frac_start:.2f}..{y_frac_end:.2f}")

    # ════════════════════════════════════════════════════════
    # PASS 1 — Claude Vision (background thread)
    # ════════════════════════════════════════════════════════
    vision_codes = []
    vision_err   = [None]

    def _vision():
        try:
            vision_codes.extend(claude_vision_detect(img, api_key=api_key))
        except Exception as e:
            vision_err[0] = str(e)

    vt = threading.Thread(target=_vision, daemon=True)
    vt.start()

    # ════════════════════════════════════════════════════════
    # PASS 2 — YOLO + Tesseract (while Vision is running)
    # ════════════════════════════════════════════════════════
    yolo_boxes = []
    if model is not None:
        try:
            results = model(img, conf=0.15, iou=0.35, verbose=False)
            for r in results:
                if r.boxes is None: continue
                for i, box in enumerate(r.boxes.xyxy.cpu().numpy()):
                    x1, y1b, x2, y2b = map(int, box)
                    yolo_boxes.append({
                        "x1": x1, "y1": y1b, "x2": x2, "y2": y2b,
                        "conf": float(r.boxes.conf.cpu().numpy()[i])
                    })
            print(f"[YOLO] {len(yolo_boxes)} boxes")
        except Exception as e:
            print(f"[YOLO ERROR] {e}")

    for b in yolo_boxes:
        x1, y1b, x2, y2b = b["x1"], b["y1"], b["x2"], b["y2"]
        bh = y2b - y1b
        crops = [
            # Bottom half (label area)
            img[max(0, y1b + int(bh * 0.50)):min(h, y2b + 15),
                max(0, x1 - 10):min(w, x2 + 10)],
            # Full spine
            img[max(0, y1b):min(h, y2b + 15),
                max(0, x1 - 10):min(w, x2 + 10)],
        ]
        for crop in crops:
            for c in ocr_region(crop, do_deskew=True):
                info, resolved = lookup_code(c, book_lookup)
                if info and resolved not in seen_codes:
                    seen_codes.add(resolved)
                    book_results.append({
                        "code": resolved, "title": info.get("title", ""),
                        "author": info.get("author", ""), "rack": info.get("rack", ""),
                        "subject": info.get("subject", ""),
                        "expectedShelf": info.get("expectedShelf", ""),
                        "found": True, "confidence": round(b["conf"], 2),
                        "box": [x1, y1b, x2, y2b], "method": "YOLO+OCR",
                    })

    # ════════════════════════════════════════════════════════
    # PASS 3 — Strip Tesseract OCR
    # ════════════════════════════════════════════════════════
    strip = img[sy1:sy2, :]
    for c in strip_tile_ocr(strip, book_lookup):
        if c in seen_codes: continue
        info, resolved = lookup_code(c, book_lookup)
        if info is None: continue
        seen_codes.add(resolved)
        book_results.append({
            "code": resolved, "title": info.get("title", ""),
            "author": info.get("author", ""), "rack": info.get("rack", ""),
            "subject": info.get("subject", ""),
            "expectedShelf": info.get("expectedShelf", ""),
            "found": True, "confidence": 0.0, "box": None, "method": "STRIP_OCR",
        })

    # ════════════════════════════════════════════════════════
    # Wait for Vision, merge results
    # ════════════════════════════════════════════════════════
    vt.join(timeout=60)
    if vision_err[0]:
        print(f"[VISION ERROR] {vision_err[0]}")

    for c in vision_codes:
        if c in seen_codes: continue
        info, resolved = lookup_code(c, book_lookup)
        if info is None:
            # Vision found it but it's not in the DB — record as unmatched
            seen_codes.add(c)
            book_results.append({
                "code": c, "title": "", "author": "", "rack": "",
                "subject": "", "expectedShelf": "", "found": False,
                "confidence": 0.95, "box": None, "method": "VISION_API",
            })
        else:
            seen_codes.add(resolved)
            book_results.append({
                "code": resolved, "title": info.get("title", ""),
                "author": info.get("author", ""), "rack": info.get("rack", ""),
                "subject": info.get("subject", ""),
                "expectedShelf": info.get("expectedShelf", ""),
                "found": True, "confidence": 0.95,
                "box": None, "method": "VISION_API",
            })

    # ── Shelf + status ────────────────────────────────────────
    detected_shelf = auto_detect_shelf(book_results)
    for r in book_results:
        r["scannedShelf"] = detected_shelf
        r["status"] = (
            "WRONG"
            if detected_shelf != "UNKNOWN"
               and r.get("expectedShelf")
               and r["expectedShelf"] != detected_shelf
            else "OK"
        )

    used_fallback = any(r["method"] != "VISION_API" for r in book_results)

    # ── Annotate ──────────────────────────────────────────────
    cv2.rectangle(annotated, (0, sy1), (w - 1, sy2), (0, 200, 255), 2)
    for r in book_results:
        if not r.get("box"): continue
        x1, y1b, x2, y2b = r["box"]
        col = (0, 50, 220) if r.get("status") == "WRONG" else (0, 200, 80)
        cv2.rectangle(annotated, (x1, y1b), (x2, y2b), col, 2)
        cv2.putText(annotated, r["code"], (x1 + 2, y1b - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)

    n_vis   = sum(1 for r in book_results if r["method"] == "VISION_API")
    n_yolo  = sum(1 for r in book_results if r["method"] == "YOLO+OCR")
    n_strip = sum(1 for r in book_results if r["method"] == "STRIP_OCR")
    method_lbl = f"V={n_vis} Y={n_yolo} S={n_strip}"

    cv2.putText(annotated, f"Shelf: {detected_shelf}  [{method_lbl}]",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 200, 0), 2, cv2.LINE_AA)
    cv2.putText(annotated, f"Found {len(book_results)} books",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (200, 200, 50), 2, cv2.LINE_AA)

    print(f"[RESULT] {len(book_results)} books | {method_lbl} | Shelf: {detected_shelf}")

    return {
        "codes":           sorted(seen_codes),
        "detections":      len(yolo_boxes),
        "books":           book_results,
        "detectedShelf":   detected_shelf,
        "annotated_image": img_to_base64(annotated),
        "total_matched":   sum(1 for r in book_results if r.get("found")),
        "used_fallback":   used_fallback,
    }