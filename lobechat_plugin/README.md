# Memory Brain LobeChat Plugin

This plugin integrates the Memory Brain backend with LobeChat, allowing you to mount drives, scan for photos, and search memories using natural language.

## Prerequisites

1.  **Memory Brain Backend**: Ensure the main backend is running on `http://127.0.0.1:5500`.
2.  **Proxy Server**: You need to run the provided proxy server.

## How to run the proxy server

Navigate to the project root and run:

```bash
uvicorn lobechat_plugin.proxy_server:app --port 5600
```

This will start the proxy server on `http://127.0.0.1:5600`.

## How to load the tool in LobeChat

1.  Open LobeChat.
2.  Go to **Settings** -> **Plugins** -> **Add Custom Plugin**.
3.  Upload the `lobechat_plugin/memory-brain-tool.json` file found in this directory.
4.  Set the tool endpoint to:
    `http://127.0.0.1:5600/api`

## How to test

Once the plugin is added, you can interact with it using natural language in LobeChat.

Examples:

*   **Mount a drive**:
    > "Mount my drive at D:/Photos"

*   **Scan the drive**:
    > "Scan the drive"

*   **Search memories**:
    > "Search memories about beach trips"

*   **Get details**:
    > "Tell me more about file_id: ..."

## Curl Examples

You can also test the proxy server directly using `curl`:

**Mount Drive:**
```bash
curl -X POST http://127.0.0.1:5600/api \
     -H "Content-Type: application/json" \
     -d '{
           "function_name": "mount_drive",
           "arguments": { "path": "/path/to/photos" }
         }'
```

**Scan Drive:**
```bash
curl -X POST http://127.0.0.1:5600/api \
     -H "Content-Type: application/json" \
     -d '{
           "function_name": "scan_drive",
           "arguments": {}
         }'
```

**Search Memories:**
```bash
curl -X POST http://127.0.0.1:5600/api \
     -H "Content-Type: application/json" \
     -d '{
           "function_name": "search_memories",
           "arguments": { "query": "cats", "top_k": 3 }
         }'
```

**Get Memory:**
```bash
curl -X POST http://127.0.0.1:5600/api \
     -H "Content-Type: application/json" \
     -d '{
           "function_name": "get_memory",
           "arguments": { "file_id": "FILE_ID_HERE" }
         }'
```
