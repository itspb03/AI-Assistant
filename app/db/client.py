import asyncio
from supabase._async.client import AsyncClient
from supabase import acreate_client
from app.config import get_settings

_client: AsyncClient | None = None
_lock = asyncio.Lock()


async def get_supabase() -> AsyncClient:
    """
    Returns a lazily-initialised async Supabase client (singleton).
    Uses the service role key — bypasses Row Level Security.
    Swap to anon key + user JWT if you add auth later.
    """
    global _client
    if _client is None:
        async with _lock:
            if _client is None:          # double-checked locking
                settings = get_settings()
                _client = await acreate_client(
                    settings.supabase_url,
                    settings.supabase_key,
                )
    return _client