// src/api/memoryApi.ts

const API_BASE = '/api'; // Uses Vite proxy

export interface Memory {
  file_id: string;
  path: string;
  score?: number;
  summary?: string;
  exif_date?: string;
  thumbnail_b64?: string;
  created_at?: string; // Added created_at
}

export interface MemoryDetail {
  file_id: string;
  path: string;
  hash: string;
  created_at: string;
  modified_at: string;
  exif_date: string;
  ocr_text: string;
  caption: string;
  memory_summary: string;
  tags: string;
}

export interface SearchResponse {
  results: Memory[];
}

export interface ScanResponse {
  status: string;
  scanned_path: string;
  new: number;
  skipped: number;
}

export interface MountResponse {
  status: string;
  db_path: string;
  count: number;
}

export const memoryApi = {
  async health() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Backend health check failed');
    return res.json();
  },

  async mountDrive(path: string): Promise<MountResponse> {
    const res = await fetch(`${API_BASE}/mount`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Mount failed');
    }
    return res.json();
  },

  async scanDrive(path?: string, rescan: boolean = false): Promise<ScanResponse> {
    const res = await fetch(`${API_BASE}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, rescan }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Scan failed');
    }
    return res.json();
  },

  async searchMemories(query: string, top_k: number = 12, date_from?: string, date_to?: string): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k, date_from, date_to }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Search failed');
    }
    return res.json();
  },

  async getMemory(file_id: string): Promise<MemoryDetail> {
    const res = await fetch(`${API_BASE}/memory/${file_id}`);
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Get memory failed');
    }
    return res.json();
  },

  getThumbnailUrl(file_id: string): string {
    return `${API_BASE}/thumbnail/${file_id}`;
  }
};
