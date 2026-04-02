import httpx
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from app.config import get_settings


class ImageGeneratorProvider(ABC):
    """
    Abstract base — swap implementations via IMAGE_PROVIDER env var.
    All providers must return a publicly accessible URL or local path.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def generate(self, prompt: str) -> str: ...


# ─────────────────────────────────────────────
class MockImageProvider(ImageGeneratorProvider):
    """
    Returns a deterministic placeholder URL.
    No API calls — safe for local dev and tests.
    Images are saved as empty placeholder files under memory_store/images/.
    """

    provider_name = "mock"

    async def generate(self, prompt: str) -> str:
        image_id = uuid.uuid4()
        # Use a real placeholder image service so the URL is actually viewable
        width, height = 800, 600
        seed = abs(hash(prompt)) % 1000
        return f"https://picsum.photos/seed/{seed}/{width}/{height}"


# ─────────────────────────────────────────────
class DalleImageProvider(ImageGeneratorProvider):
    """
    Calls OpenAI DALL-E 3.
    Requires OPENAI_API_KEY and IMAGE_PROVIDER=dalle.
    """

    provider_name = "dalle"

    async def generate(self, prompt: str) -> str:
        import openai
        client = openai.AsyncOpenAI(api_key=get_settings().openai_api_key)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url


# ─────────────────────────────────────────────
def get_image_provider() -> ImageGeneratorProvider:
    """
    Factory — reads IMAGE_PROVIDER from settings.
    Add new providers here as elif branches.
    """
    provider = get_settings().image_provider.lower()
    if provider == "dalle":
        return DalleImageProvider()
    return MockImageProvider()   # default fallback