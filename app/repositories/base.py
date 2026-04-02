from supabase._async.client import AsyncClient


class BaseRepository:
    """
    Thin base class — just holds the injected Supabase client.
    All repos inherit from this so client injection is consistent.
    The client is resolved async by the dependency factory in dependencies.py.
    """

    def __init__(self, client: AsyncClient):
        self._client = client

    @property
    def db(self) -> AsyncClient:
        return self._client