import httpx
import json
from typing import List
from ..contract import VisionContract
from .base import VendorBase

class LMStudioVendor(VendorBase):
    def list_models(self) -> List[str]:
        url = f"{self.endpoint}/v1/models"
        try:
            resp = httpx.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for item in data.get("data", []):
                mid = item.get("id", "").lower()
                if any(x in mid for x in ["vision", "llava", "moondream", "clip"]):
                    models.append(item["id"])
            return models
        except Exception:
            return []

    def predict(self, model: str, image_b64: str) -> VisionContract:
        url = f"{self.endpoint}/v1/chat/completions"
        prompt = (
            "Analyze the image and return ONLY valid JSON.\n"
            "Do not explain anything.\n"
            "Required fields:\n"
            "activity, setting, social_context, objects, people_count, summary\n\n"
            "No markdown. No commentary. JSON only."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 512,
            "stream": False
        }

        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()

        choices = res_json.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from LLM")

        content = choices[0].get("message", {}).get("content", "")
        return self._validate_response(content)
