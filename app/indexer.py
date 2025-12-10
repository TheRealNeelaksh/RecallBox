# app/indexer.py
import os
import hashlib
import io
import uuid
from pathlib import Path
from PIL import Image, ImageOps
import pytesseract
import numpy as np
from tqdm import tqdm
from .db import row_to_dict
from datetime import datetime

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".gif"}
THUMB_SIZE = (256, 256)

def file_hash(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def make_thumbnail_bytes(path: Path, size=THUMB_SIZE):
    try:
        im = Image.open(path)
        im = ImageOps.exif_transpose(im)
        im.thumbnail(size)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        # generate blank
        im = Image.new("RGB", size, (100,100,100))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

def do_ocr(path: Path):
    try:
        txt = pytesseract.image_to_string(str(path))
        return txt
    except Exception:
        return ""

def summarize_text(ocr_text: str, filename: str):
    # simple heuristic summary for Phase1
    first_line = ""
    if ocr_text and ocr_text.strip():
        first_line = ocr_text.strip().splitlines()[0]
    if first_line:
        return first_line[:300]
    # fallback to filename words
    return filename.replace("_", " ").replace("-", " ")[:300]

def datetime_iso(path: Path):
    st = path.stat()
    ct = getattr(st, "st_ctime", st.st_mtime)
    return datetime.fromtimestamp(ct).isoformat()

def scan_and_index(root: Path, conn, model, rebuild=False, faiss_mgr=None):
    """
    Walk root for supported image files. Insert new entries into DB.
    Returns (added, skipped)
    """
    cur = conn.cursor()
    files = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if Path(fn).suffix.lower() in SUPPORTED_EXT:
                files.append(Path(dp) / fn)
    added = 0
    skipped = 0
    for p in tqdm(files, desc="scan"):
        try:
            h = file_hash(p)
        except Exception:
            skipped += 1
            continue
        # check existing by hash
        cur.execute("SELECT file_id, path FROM memories WHERE hash=?", (h,))
        row = cur.fetchone()
        if row and not rebuild:
            skipped += 1
            continue
        # process
        ocr = do_ocr(p)
        fname = p.stem
        caption = fname
        summary = summarize_text(ocr, fname)
        emb_text = " ".join([caption, summary, ocr])
        try:
            emb = model.encode(emb_text).astype("float32")
        except Exception:
            emb = np.zeros((384,), dtype="float32")
        thumb = make_thumbnail_bytes(p)
        fid = str(uuid.uuid4())
        created = datetime_iso(p)
        modified = datetime_iso(p)
        cur.execute("""
            INSERT OR REPLACE INTO memories
            (file_id, path, hash, created_at, modified_at, exif_date, ocr_text, caption, memory_summary, tags, embedding, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fid, str(p), h, created, modified, None, ocr, caption, summary, "", emb.tobytes(), thumb))
        conn.commit()
        added += 1
        # incrementally add to faiss if provided
        if faiss_mgr:
            faiss_mgr.add_vector(emb, (fid, str(p)))
    return added, skipped
