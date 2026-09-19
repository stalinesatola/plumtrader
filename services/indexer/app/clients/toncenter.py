import httpx

from app.config import settings


class TonCenterClient:
    """Cliente de fallback para o RPC público da Toncenter."""

    def __init__(self) -> None:
        headers = {}
        if settings.toncenter_api_key:
            headers["X-API-Key"] = settings.toncenter_api_key
        self._client = httpx.AsyncClient(
            base_url=settings.toncenter_base_url, headers=headers, timeout=10.0
        )

    async def get_address_information(self, address: str) -> dict:
        resp = await self._client.get(
            "/getAddressInformation", params={"address": address}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_transactions(self, address: str, limit: int = 20) -> dict:
        resp = await self._client.get(
            "/getTransactions", params={"address": address, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


toncenter_client = TonCenterClient()
