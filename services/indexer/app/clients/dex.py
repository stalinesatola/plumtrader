import httpx

from app.config import settings


class StonFiClient:
    """Cliente para a API pública do STON.fi (preços e pools de swap na TON)."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.stonfi_base_url, timeout=10.0)

    async def get_asset(self, address: str) -> dict:
        resp = await self._client.get(f"/v1/assets/{address}")
        resp.raise_for_status()
        return resp.json()

    async def get_pools(self) -> dict:
        resp = await self._client.get("/v1/pools")
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


class DeDustClient:
    """Cliente para a API pública do DeDust (preços e pools de swap na TON)."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.dedust_base_url, timeout=10.0)

    async def get_pools(self) -> list:
        resp = await self._client.get("/v2/pools")
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


stonfi_client = StonFiClient()
dedust_client = DeDustClient()
