import asyncio
import io
import base64
import logging

import httpx
import google.generativeai as genai
from functools import lru_cache
from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _configure_gemini() -> None:
    genai.configure(api_key=get_settings().gemini_api_key)


class GeminiImageAnalyzer:
    """
    Uses Gemini Vision to analyze an image URL.
    Fetches the image bytes, resizes to max 1024px, encodes to
    base64, and sends to Gemini.


    Assumption: image URLs are publicly accessible.
    For private/mock URLs, a fallback description is returned.
    """

    ANALYSIS_PROMPT = (
        "You are analyzing an image for a project assistant. "
        "Describe what you see in detail: content, style, colors, composition, "
        "and how it might relate to a design or product project. "
        "Be specific and useful. Keep the response under 300 words."
    )
    MAX_IMAGE_PX = 1024   

    def __init__(self):
        _configure_gemini()
        settings = get_settings()
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.max_output_tokens = settings.gemini_max_tokens  

    async def analyze(
        self, image_url: str, context: str | None = None
    ) -> str:
        """
        Fetches image from URL, resizes it, and asks Gemini to describe it.
        Falls back to a mock description if the URL is not reachable.
        """
        settings = get_settings()

        
        if settings.mock_ai:
            logger.debug("MOCK_AI=true — skipping Gemini analyze() call")
            return self._mock_analysis(image_url, context)

        try:
            raw_bytes = await self._fetch_image(image_url)
        except Exception:
            
            return self._mock_analysis(image_url, context)

        # resizing before encoding — reduces Gemini tile count
        image_data = self._resize_image(raw_bytes, max_px=self.MAX_IMAGE_PX)

        prompt = self.ANALYSIS_PROMPT
        if context:
            prompt += f"\n\nGeneration prompt used: '{context}'"

        response = await asyncio.to_thread(
            self.model.generate_content,
            [
                prompt,
                {
                    "mime_type": "image/jpeg",   
                    "data": image_data,
                },
            ],
            generation_config={"max_output_tokens": self.max_output_tokens},
        )
        return response.text

    async def _fetch_image(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    @staticmethod
    def _resize_image(image_bytes: bytes, max_px: int = 1024) -> bytes:
        """
        Resize image so the longest side <= max_px.
        Saves as JPEG (smaller than PNG) at quality=85.
        Returns the compressed bytes. (Change 3)
        """
        from PIL import Image  

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        if max(w, h) > max_px:
            scale = max_px / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()

    @staticmethod
    def _mock_analysis(url: str, context: str | None) -> str:
        base = "Mock analysis: This is a placeholder image"
        if context:
            return f"{base} generated from the prompt: '{context}'."
        return f"{base} at path: {url}."
