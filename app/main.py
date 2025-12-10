# app/main.py
import os
import io
import hashlib
import sqlite3
import base64
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import Response, JSONResponse
from sentence_transformers import SentenceTransformer
from PIL import Image, ImageOps
import numpy as np
import faiss
import pytesseract
from datetime import datetime

from .db import init_db, row_to_dict
from .indexer import scan_and_index
from .faiss_mgr import FaissManager

APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Memory Brain - Phase1")

MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384

# Global runtime state (simple single-drive focus)
state = {
    "mounted_path": None,
    "db_path": None,
    "conn": None,
    "faiss": None,
    "embed_model": None
}

# Simple boot
@app.on_event("startup")
def load_model():
    try:
        state["embed_model"] = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        raise RuntimeError(f"Failed loading embedding model: {e}")

class MountRequest(BaseModel):
    path: str

@app.post("/mount")
def mount(req: MountRequest):
    p = Path(req.path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail="path does not exist or is not a directory")
    db_path = p.joinpath(".memory_index.db")
    conn = init_db(str(db_path))
    state.update({
        "mounted_path": str(p),
        "db_path": str(db_path),
        "conn": conn,
        "faiss": FaissManager(EMBED_DIM)
    })
    # Build FAISS from existing DB
    state["faiss"].build_from_db(conn)
    # count entries
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM memories")
    count = cur.fetchone()[0]
    return {"status": "ok", "db_path": str(db_path), "count": count}

class ScanRequest(BaseModel):
    path: Optional[str] = None
    rescan: Optional[bool] = False

@app.post("/scan")
def scan(req: ScanRequest):
    if req.path:
        base = Path(req.path)
    else:
        if not state["mounted_path"]:
            raise HTTPException(status_code=400, detail="No mounted path. Call /mount first or supply path.")
        base = Path(state["mounted_path"])
    if not base.exists():
        raise HTTPException(status_code=400, detail="scan path does not exist")
    conn = state["conn"] or init_db(str(base.joinpath(".memory_index.db")))
    model = state["embed_model"]
    added, skipped = scan_and_index(base, conn, model, rebuild=req.rescan, faiss_mgr=state.get("faiss"))
    # After scan, ensure FAISS rebuilt if needed
    if state.get("faiss"):
        state["faiss"].build_from_db(conn)
    return {"status": "ok", "scanned_path": str(base), "new": added, "skipped": skipped}

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 12
    date_from: Optional[str] = None
    date_to: Optional[str] = None

@app.post("/search")
def search(req: SearchRequest):
    if not state.get("faiss") or state["faiss"].index.ntotal == 0:
        # try to build from DB
        if state.get("conn"):
            state["faiss"].build_from_db(state["conn"])
        else:
            raise HTTPException(status_code=400, detail="no index available; mount and scan first")
    qvec = state["embed_model"].encode(req.query).astype("float32")
    results = state["faiss"].search(qvec, topk=req.top_k)
    # optionally filter by date range
    out = []
    conn = state["conn"]
    c = conn.cursor()
    for r in results:
        fid, path, score = r["file_id"], r["path"], r["score"]
        c.execute("SELECT file_id, path, created_at, exif_date, memory_summary, thumbnail FROM memories WHERE file_id=?", (fid,))
        row = c.fetchone()
        if not row:
            continue

        # Manually unpack since we selected specific columns
        # row: file_id(0), path(1), created_at(2), exif_date(3), memory_summary(4), thumbnail(5)
        file_id, path_val, created_at, exif_date, summary, thumbnail_blob = row

        # date filtering
        if req.date_from or req.date_to:
            ok = True
            if req.date_from:
                if exif_date:
                    ok = ok and exif_date >= req.date_from
            if req.date_to:
                if exif_date:
                    ok = ok and exif_date <= req.date_to
            if not ok:
                continue
        thumb_b64 = None
        if thumbnail_blob:
            thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(thumbnail_blob).decode("utf-8")
        out.append({
            "file_id": file_id,
            "path": path_val,
            "score": float(score),
            "summary": summary,
            "exif_date": exif_date,
            "thumbnail_b64": thumb_b64
        })
    return {"results": out}

@app.get("/thumbnail/{file_id}")
def thumbnail(file_id: str):
    if not state.get("conn"):
        raise HTTPException(status_code=400, detail="No DB loaded")
    c = state["conn"].cursor()
    c.execute("SELECT thumbnail FROM memories WHERE file_id=?", (file_id,))
    row = c.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="thumbnail not found")
    return Response(content=row[0], media_type="image/jpeg")

@app.get("/memory/{file_id}")
def memory(file_id: str):
    if not state.get("conn"):
        raise HTTPException(status_code=400, detail="No DB loaded")
    c = state["conn"].cursor()
    c.execute("SELECT file_id, path, hash, created_at, modified_at, exif_date, ocr_text, caption, memory_summary, tags FROM memories WHERE file_id=?", (file_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="memory not found")
    rec = {
        "file_id": row[0],
        "path": row[1],
        "hash": row[2],
        "created_at": row[3],
        "modified_at": row[4],
        "exif_date": row[5],
        "ocr_text": row[6],
        "caption": row[7],
        "memory_summary": row[8],
        "tags": row[9]
    }
    return rec

@app.get("/health")
def health():
    return {"status": "ok", "mounted_path": state.get("mounted_path")}
