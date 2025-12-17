import json
from typing import Optional, List
from ..contract import VisionContract

class VendorBase:
    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def list_models(self) -> List[str]:
        raise NotImplementedError

    def predict(self, model: str, image_b64: str) -> VisionContract:
        raise NotImplementedError

    @staticmethod
    def _validate_response(text: str) -> VisionContract:
        try:
            # simple cleanup for code blocks
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # fuzzy finder for json object
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                return VisionContract(**data)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            raise ValueError(f"Failed to parse or validate JSON: {e}")
