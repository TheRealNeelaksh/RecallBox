# **RecallBox – Local AI-Powered Photo & File Memory Engine**

RecallBox is a local, privacy-preserving search engine that lets you scan folders of images, extract text + visual meaning using embeddings, and instantly search them semantically. No cloud, no telemetry — your machine becomes your personal memory engine.

---

# **Table of Contents**

* [Features](#features)
* [Architecture Overview](#architecture-overview)
* [Installation](#installation)
* [Running the Server](#running-the-server)
* [API Endpoints](#api-endpoints)
* [Workflow Example](#workflow-example)
* [Project Structure](#project-structure)
* [Roadmap](#roadmap)
* [License](#license)

---

# **Features**

Phase 1 delivers a stable, fully functional backend:

### **Core**

* FastAPI backend with clean modular structure
* Local folder mounting
* Scanning & indexing of image files
* SHA256 hashing to prevent duplicates
* OCR extraction using **pytesseract**
* Thumbnail generation (PIL)
* Embedding generation using **sentence-transformers (all-MiniLM-L6-v2)**
* FAISS in-memory vector search
* SQLite local data store (`.memory_index.db`)

### **API**

* `/mount` — prepare a folder for indexing
* `/scan` — analyze folder contents and index new files
* `/search` — semantic search via embeddings
* `/thumbnail/{file_id}` — return stored thumbnail
* `/memory` — debugging endpoint for index info
* `/health` — quick readiness test

Everything runs **offline**, locally, and fast.

---

# **Architecture Overview**

```
                +---------------------------+
                |         FastAPI           |
                +------------+--------------+
                             |
                             v
        +--------------------------------------------+
        |                Indexer                     |
        |--------------------------------------------|
        | - File scanning                            |
        | - SHA256 hashing                           |
        | - OCR (pytesseract)                        |
        | - Thumbnails (PIL)                         |
        | - Embeddings (sentence-transformers)       |
        +--------------------------------------------+
                             |
                             v
        +--------------------------------------------+
        |               SQLite DB                    |
        |  file_id | path | hash | summary | ...     |
        +--------------------------------------------+
                             |
                             v
        +--------------------------------------------+
        |                FAISS Manager               |
        |  In-memory vector index for fast search    |
        +--------------------------------------------+
```

Each scan updates both the **SQLite metadata** and the **FAISS vector index**, giving you instant semantic search.

---

# **Installation**

### **1. Clone the repository**

```bash
git clone https://github.com/<your-username>/RecallBox
cd RecallBox
```

### **2. Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows
```

### **3. Install dependencies**

```bash
pip install -r requirements.txt
```

### **4. (Windows only) Install Tesseract**

Download:
[https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)

Make sure `tesseract.exe` is in your PATH.

---

# **Running the Server**

Start the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 5500
```

Open the API docs:

```
http://127.0.0.1:5500/docs
```

---

# **API Endpoints**

### **POST /mount**

Initialize a folder and create its `.memory_index.db`.

**Body:**

```json
{ "path": "G:/Photos" }
```

---

### **POST /scan**

Scan folder, detect images, index new ones.

**Body:**

```json
{ "path": "G:/Photos" }
```

**Response:**

```json
{
  "status": "ok",
  "scanned_path": "G:/Photos",
  "new": 12,
  "skipped": 0
}
```

---

### **POST /search**

Semantic search over image content + OCR text.

**Body:**

```json
{ "query": "coffee house", "top_k": 4 }
```

**Response (example):**

```json
{
  "results": [
    {
      "file_id": "4f3e...",
      "path": "G:/Photos/central-park-coffeehouse.jpg",
      "score": 0.59,
      "summary": "central park coffeehouse",
      "thumbnail_b64": "<base64>"
    }
  ]
}
```

---

### **GET /thumbnail/{file_id}**

Returns JPEG bytes for the stored thumbnail.

Example (PowerShell):

```powershell
Invoke-WebRequest http://127.0.0.1:5500/thumbnail/<file_id> -OutFile thumb.jpg
```

---

# **Workflow Example**

### **1. Mount**

```bash
POST /mount
{ "path": "G:/Projects/RecallBox/testing_data" }
```

### **2. Scan**

```bash
POST /scan
{ "path": "G:/Projects/RecallBox/testing_data" }
```

→ `"new": 5`

### **3. Search**

```bash
POST /search
{ "query": "coffee house", "top_k": 4 }
```

→ returns semantic matches + thumbnails

### **4. Fetch thumbnail**

```bash
GET /thumbnail/<id> → thumb.jpg
```

---

# **Project Structure**

```
app/
│
├── main.py               # FastAPI entry
├── db.py                 # SQLite layer
├── indexer.py            # OCR, hashing, images, embeddings
├── faiss_mgr.py          # FAISS vector index
└── models/               # (if applicable)
│
requirements.txt
README.md
.gitignore
```

---

# **Roadmap**

### **Phase 2 — User Interface**

* Local web UI for browsing scans
* Thumbnail grid with lazy loading
* Search bar + instant results

### **Phase 3 — Multi-drive memory**

* Multiple indexed folders
* Background scanning
* Incremental re-indexing

### **Phase 4 — Smart features**

* Duplicate detection
* Face clustering
* Natural language tagging
* Event grouping (e.g., “Trip to Japan 2020”)

---

# **License**

MIT (or whatever you choose).
