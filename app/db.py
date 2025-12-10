# app/db.py
import sqlite3
import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    file_id TEXT PRIMARY KEY,
    path TEXT,
    hash TEXT,
    created_at TEXT,
    modified_at TEXT,
    exif_date TEXT,
    ocr_text TEXT,
    caption TEXT,
    memory_summary TEXT,
    tags TEXT,
    embedding BLOB,
    thumbnail BLOB,
    schema_version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_hash ON memories(hash);
CREATE INDEX IF NOT EXISTS idx_path ON memories(path);
"""

def init_db(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()
    return conn

def row_to_dict(row):
    # row expected: file_id, path, hash, created_at, modified_at, exif_date, ocr_text, caption, memory_summary, tags, embedding, thumbnail, ...
    if not row:
        return None
    # handle thumbnail as bytes, embedding as bytes
    return {
        "file_id": row[0],
        "path": row[1],
        "hash": row[2],
        "created_at": row[3],
        "modified_at": row[4],
        "exif_date": row[5],
        "ocr_text": row[6],
        "caption": row[7],
        "memory_summary": row[8],
        "tags": row[9],
        "embedding": np.frombuffer(row[10], dtype=np.float32) if row[10] else None,
        "thumbnail": row[11]
    }
