import httpx
import json
from typing import List
from ..contract import VisionContract
from .base import VendorBase

class OllamaVendor(VendorBase):
    def list_models(self) -> List[str]:
        url = f"{self.endpoint}/api/tags"
        try:
            resp = httpx.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                families = details.get("families", []) or []
                name = m.get("name", "").lower()

                is_vision = False
                if "clip" in families:
                    is_vision = True
                if any(x in name for x in ["llava", "vision", "moondream", "minicpm", "bakllava"]):
                    is_vision = True

                if is_vision:
                    models.append(m["name"])
            return models
        except Exception:
            return []

    def predict(self, model: str, image_b64: str) -> VisionContract:
        url = f"{self.endpoint}/api/generate"
        prompt = (
            "Analyze the image and return ONLY valid JSON.\n"
            "Do not explain anything.\n"
            "Required fields:\n"
            "activity, setting, social_context, objects, people_count, summary\n\n"
            "No markdown. No commentary. JSON only."
        )
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "format": "json"
        }

        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        content = res_json.get("response", "")
        return self._validate_response(content)
