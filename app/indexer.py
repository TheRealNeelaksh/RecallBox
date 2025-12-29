# app/indexer.py
import os
import hashlib
import io
import uuid
import asyncio
from pathlib import Path
from PIL import Image, ImageOps
import pytesseract
import numpy as np
from tqdm import tqdm
from .db import row_to_dict
from datetime import datetime
import json
import reverse_geocoder as rg

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

def get_exif_date(path: Path):
    try:
        im = Image.open(path)
        exif = im.getexif()
        # 36867 = DateTimeOriginal
        date_str = exif.get(36867)
        if date_str:
            # format: YYYY:MM:DD HH:MM:SS
            try:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                return dt.isoformat()
            except ValueError:
                return None
    except Exception:
        pass
    return None

def _convert_to_degrees(value):
    """
    Helper to convert GPS coordinates to degrees
    """
    d = value[0]
    m = value[1]
    s = value[2]
    return d + (m / 60.0) + (s / 3600.0)

def get_gps_from_exif(path: Path):
    """
    Extracts lat, lon from image EXIF if available.
    Returns (lat, lon) tuple or None.
    """
    try:
        im = Image.open(path)
        exif = im.getexif()
        if not exif:
            return None

        gps_info = exif.get_ifd(34853) # GPSInfo IFD
        if not gps_info:
            return None

        # Tags: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
        lat_ref = gps_info.get(1)
        lat_raw = gps_info.get(2)
        lon_ref = gps_info.get(3)
        lon_raw = gps_info.get(4)

        if lat_raw and lon_raw and lat_ref and lon_ref:
            lat = _convert_to_degrees(lat_raw)
            if lat_ref != 'N':
                lat = -lat

            lon = _convert_to_degrees(lon_raw)
            if lon_ref != 'E':
                lon = -lon

            return lat, lon
    except Exception:
        pass
    return None

def get_location_name(lat, lon):
    """
    Returns 'City, Admin1, CC' or similar from coordinates using reverse_geocoder.
    """
    try:
        # mode=1 means single result
        res = rg.search((lat, lon), mode=1)
        if res:
            # res is a list of dicts. We want the first one.
            # keys: lat, lon, name (City), admin1 (State/Region), admin2, cc (Country Code)
            data = res[0]
            city = data.get('name', '')
            admin = data.get('admin1', '')
            cc = data.get('cc', '')
            parts = [p for p in [city, admin, cc] if p]
            return ", ".join(parts)
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def scan_and_index(root: Path, conn, model, rebuild=False, faiss_mgr=None, vision_adapter=None):
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

    # We need an event loop to run async vision adapter calls
    # Since FastAPI is async, but this function is called synchronously or needs to bridge,
    # we'll create a loop or run_until_complete if we are in a thread.
    # However, scan is called from a sync endpoint wrapper currently?
    # Wait, scan endpoint is sync `def scan`. We can use asyncio.run if not already in loop.
    # But usually better to use `asyncio.create_task` or run in executor.
    # For simplicity here, we'll do a mini-wrapper to run async vision call.

    def run_vision(path_str):
        if not vision_adapter:
            return None
        try:
             # This is a bit hacky inside a sync loop, but sufficient for local single-user tool
             # Ideally the whole scan pipeline becomes async
             return asyncio.run(vision_adapter.analyze_image(path_str))
        except RuntimeError:
             # Already in event loop?
             # If `scan` endpoint is synchronous, we are fine.
             return None

    for p in tqdm(files, desc="scan"):
        try:
            h = file_hash(p)
        except Exception:
            skipped += 1
            continue

        # Check existing
        cur.execute("SELECT file_id, path, vision_status FROM memories WHERE hash=?", (h,))
        row = cur.fetchone()

        # Determine if we need to process
        # If rebuild=True, always process
        # If not in DB, process
        # If in DB but vision_status is failed/null and we have an adapter now, we might want to retry?
        # User requirement: "If vision inference fails... indexed with vision_status failed"
        # Let's say we only process if not exists or rebuild is set.

        if row and not rebuild:
            # Maybe check if we should retry vision?
            # For now stick to simple "skip if exists" unless rebuild
            skipped += 1
            continue

        fid = str(uuid.uuid4())
        # If updating existing
        if row:
            fid = row[0]

        # 1. Basic Metadata
        created = datetime_iso(p)
        modified = datetime_iso(p)
        exif_date = get_exif_date(p) or created

        # GPS & Location
        latlon = get_gps_from_exif(p)
        location_str = None
        if latlon:
            location_str = get_location_name(*latlon)

        # 2. Vision Analysis
        vision_res = None
        vision_status = "pending"
        vision_json_str = None

        if vision_adapter:
            # We need to run async in this sync loop.
            # If `scan` is a sync function in FastAPI, it runs in a threadpool.
            # So `asyncio.run` creates a new loop for each call which is inefficient but works.
            try:
                vision_res = asyncio.run(vision_adapter.analyze_image(str(p), location=location_str, date=exif_date))
                if vision_res:
                    vision_status = "success"
                    # Pydantic v2 use model_dump_json()
                    vision_json_str = vision_res.model_dump_json()
                else:
                    vision_status = "failed"
            except Exception as e:
                print(f"Vision crash: {e}")
                vision_status = "failed"

        # 3. Text Extraction (Fallback or augment)
        ocr = do_ocr(p)
        caption = p.stem

        # 4. Derive Summary & Tags
        if vision_res:
            summary = vision_res.summary
            tag_list = vision_res.objects[:5] + [vision_res.setting, vision_res.time_of_day]
            if location_str:
                tag_list.insert(0, location_str)
            tags = ", ".join([str(t) for t in tag_list if t])
            # Embed based on vision
            emb_text = f"{summary} {tags} {ocr}"
        else:
            # Fallback
            summary = summarize_text(ocr, caption)
            tags = "ocr-fallback"
            if location_str:
                tags += f", {location_str}"
                summary += f" Location: {location_str}"
            emb_text = f"{caption} {summary} {ocr}"

        # 5. Embed
        try:
            emb = model.encode(emb_text).astype("float32")
        except Exception:
            emb = np.zeros((384,), dtype="float32")

        thumb = make_thumbnail_bytes(p)

        # 6. Save
        cur.execute("""
            INSERT OR REPLACE INTO memories
            (file_id, path, hash, created_at, modified_at, exif_date, ocr_text, caption, memory_summary, tags, vision_json, vision_status, embedding, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fid, str(p), h, created, modified, exif_date, ocr, caption, summary, tags, vision_json_str, vision_status, emb.tobytes(), thumb))
        conn.commit()
        added += 1

        # incrementally add to faiss if provided
        if faiss_mgr:
            faiss_mgr.add_vector(emb, (fid, str(p)))

    return added, skipped
