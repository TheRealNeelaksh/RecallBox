import httpx
from typing import List, Optional
from .contract import VisionContract
from .vendors.ollama import OllamaVendor
from .vendors.lmstudio import LMStudioVendor
from .vendors.base import VendorBase

class VisionAdapter:
    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.vendor: Optional[VendorBase] = None
        self._detect_vendor()

    def _detect_vendor(self):
        # Auto-detect vendor
        # Check Ollama
        try:
            r = httpx.get(f"{self.endpoint}/api/tags", timeout=2)
            if r.status_code == 200:
                self.vendor = OllamaVendor(self.endpoint, self.api_key)
                return
        except:
            pass

        # Check LM Studio / OpenAI-compat
        try:
            r = httpx.get(f"{self.endpoint}/v1/models", timeout=2)
            if r.status_code == 200:
                self.vendor = LMStudioVendor(self.endpoint, self.api_key)
                return
        except:
            pass

        # Fallback / Undetected
        # We don't raise error here, we just leave vendor None.
        # listing models will return empty.

    def list_models(self) -> List[str]:
        if not self.vendor:
            return []
        return self.vendor.list_models()

    def predict(self, model: str, image_b64: str) -> VisionContract:
        if not self.vendor:
            raise RuntimeError("No compatible vision vendor detected at endpoint")
        return self.vendor.predict(model, image_b64)
