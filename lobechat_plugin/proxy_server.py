from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy_server")

app = FastAPI(title="Memory Brain Proxy")

BACKEND_URL = "http://127.0.0.1:5500"

class ToolCallRequest(BaseModel):
    function_name: str
    arguments: Dict[str, Any]

@app.post("/api")
async def proxy_tool_call(req: ToolCallRequest):
    logger.info(f"Received request for function: {req.function_name}")

    function_name = req.function_name
    arguments = req.arguments

    try:
        if function_name == "mount_drive":
            # Map to POST /mount
            # Expecting arguments: {"path": "..."}
            if "path" not in arguments:
                 raise HTTPException(status_code=400, detail="Missing required argument: path")

            resp = requests.post(f"{BACKEND_URL}/mount", json=arguments)

        elif function_name == "scan_drive":
            # Map to POST /scan
            # Expecting arguments: {"path": "..."} (optional)
            resp = requests.post(f"{BACKEND_URL}/scan", json=arguments)

        elif function_name == "search_memories":
            # Map to POST /search
            # Expecting arguments: {"query": "...", "top_k": ...}
            if "query" not in arguments:
                raise HTTPException(status_code=400, detail="Missing required argument: query")

            # Ensure top_k is an integer if present
            if "top_k" in arguments:
                arguments["top_k"] = int(arguments["top_k"])

            resp = requests.post(f"{BACKEND_URL}/search", json=arguments)

        elif function_name == "get_memory":
            # Map to GET /memory/{file_id}
            # Expecting arguments: {"file_id": "..."}
            if "file_id" not in arguments:
                raise HTTPException(status_code=400, detail="Missing required argument: file_id")

            file_id = arguments["file_id"]
            resp = requests.get(f"{BACKEND_URL}/memory/{file_id}")

        else:
            raise HTTPException(status_code=400, detail=f"Unknown function: {function_name}")

        # Handle backend errors
        if resp.status_code >= 400:
             # Try to parse backend error detail
            try:
                error_detail = resp.json()
            except:
                error_detail = resp.text

            logger.error(f"Backend error ({resp.status_code}): {error_detail}")
            # Return the backend error directly or wrap it?
            # The requirements say "handle errors gracefully" and "return backend JSON directly"
            # But if we raise HTTPException here, FastAPI will return a JSON error structure.
            # If we return a Response object with the status code, it might be cleaner.
            return JSONResponse(status_code=resp.status_code, content=error_detail)

        return resp.json()

    except requests.exceptions.ConnectionError:
        logger.error("Connection refused to backend")
        return JSONResponse(status_code=503, content={"error": "Backend unavailable", "detail": "Connection refused"})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Proxy error", "detail": str(e)})
