import httpx

from app.config import settings


class TonApiClient:
    """Cliente para a TonAPI.io (dados de jettons, holders e transações na TON)."""

    def __init__(self) -> None:
        headers = {}
        if settings.tonapi_key:
            headers["Authorization"] = f"Bearer {settings.tonapi_key}"
        self._client = httpx.AsyncClient(
            base_url=settings.tonapi_base_url, headers=headers, timeout=10.0
        )

    async def get_jetton(self, address: str) -> dict:
        resp = await self._client.get(f"/v2/jettons/{address}")
        resp.raise_for_status()
        return resp.json()

    async def get_jetton_holders(self, address: str, limit: int = 20) -> dict:
        resp = await self._client.get(
            f"/v2/jettons/{address}/holders", params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def search_jettons(self, query: str) -> dict:
        resp = await self._client.get("/v2/jettons", params={"query": query})
        resp.raise_for_status()
        return resp.json()

    async def list_jettons(self, limit: int = 1000, last_account_id: str | None = None) -> dict:
        """Lista jettons indexados pela TonAPI (GET /v2/jettons), paginado
        por cursor via ``last_account_id`` em vez de ``offset`` (deprecado).
        """
        params: dict = {"limit": limit}
        if last_account_id:
            params["last_account_id"] = last_account_id
        resp = await self._client.get("/v2/jettons", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_rates(self, tokens: str = "ton", currencies: str = "usd") -> dict:
        """Cotação da moeda nativa TON (não é um jetton, então não aparece
        em /v2/jettons). Resposta real da TonAPI:
        {"rates": {"TON": {"prices": {"USD": 2.12}, "diff_24h": {"USD": "+0.85%"}, ...}}}
        """
        resp = await self._client.get("/v2/rates", params={"tokens": tokens, "currencies": currencies})
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


tonapi_client = TonApiClient()
