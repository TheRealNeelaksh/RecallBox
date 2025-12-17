# app/db.py
import sqlite3
import numpy as np

# Updated schema for fresh installs
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
    schema_version INTEGER DEFAULT 1,
    vision_json TEXT,
    vision_status TEXT
);
CREATE INDEX IF NOT EXISTS idx_hash ON memories(hash);
CREATE INDEX IF NOT EXISTS idx_path ON memories(path);
CREATE INDEX IF NOT EXISTS idx_vision_status ON memories(vision_status);

CREATE TABLE IF NOT EXISTS vision_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    endpoint TEXT NOT NULL,
    api_key TEXT,
    vendor TEXT,
    model TEXT,
    last_validated_at TEXT
);
"""

def migrate_db(conn):
    """
    Perform idempotent migrations on the database connection.
    """
    cur = conn.cursor()

    # 1. Ensure vision columns exist in memories
    # Get existing columns
    cur.execute("PRAGMA table_info(memories)")
    columns = {row[1] for row in cur.fetchall()}

    if "vision_json" not in columns:
        cur.execute("ALTER TABLE memories ADD COLUMN vision_json TEXT")

    if "vision_status" not in columns:
        cur.execute("ALTER TABLE memories ADD COLUMN vision_status TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vision_status ON memories(vision_status)")

    # 2. Ensure vision_config table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vision_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            endpoint TEXT NOT NULL,
            api_key TEXT,
            vendor TEXT,
            model TEXT,
            last_validated_at TEXT
        )
    """)

    conn.commit()

def init_db(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()

    # Create tables if not exist (using the updated schema which includes new cols for fresh DBs)
    # Note: If table exists, this script continues (due to IF NOT EXISTS) but won't add columns if they are missing from the CREATE stmt in an old DB.
    # So we trust the migrate function to handle the diffs.
    # But for a fresh DB, we want the CREATE stmt to be sufficient.
    # To cover both cases:
    # We can run the CREATE stmt first (it handles fresh start), then run migrate (handles updates).
    # But wait, `SCHEMA` above has the new columns.
    # If table exists, `CREATE TABLE IF NOT EXISTS` does nothing.
    # So `migrate_db` is essential for existing DBs.

    cur.executescript(SCHEMA)
    conn.commit()

    migrate_db(conn)

    return conn

def row_to_dict(row):
    # This function is fragile as it depends on row index.
    # If the query is `SELECT *`, the index might change if we added columns in the middle (unlikely with SQLite append).
    # It's better if the caller uses explicit column selection or dict factory.
    # For now, I will keep it as is but warn that it expects the schema order.
    # Since I appended columns, indices 0-11 should be stable.
    # However, consumers of this function might need to be updated if they select * and expect specific length.

    if not row:
        return None

    # basic safety check
    if len(row) < 12:
        return None

    res = {
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

    # If the row has more columns (the new ones), we could add them,
    # but `row_to_dict` seems to be used for `memory` endpoint which might return specific JSON.
    # For now, keeping legacy behavior for existing endpoints unless specified otherwise.
    # The new columns will be accessed explicitly where needed.

    return res
