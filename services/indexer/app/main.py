from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import select

from app.clients.dex import dedust_client, stonfi_client
from app.clients.tonapi import tonapi_client
from app.clients.toncenter import toncenter_client
from app.config import settings
from app.db import TokenRow, async_session, init_db
from app.models import Token
from app.tasks.poller import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()
    await tonapi_client.aclose()
    await toncenter_client.aclose()
    await stonfi_client.aclose()
    await dedust_client.aclose()


app = FastAPI(title="PlumTrader Indexer", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/tokens", response_model=list[Token])
async def list_tokens() -> list[Token]:
    async with async_session() as session:
        rows = (await session.execute(select(TokenRow))).scalars().all()
    return [
        Token(
            address=row.address,
            symbol=row.symbol,
            name=row.name,
            price_usd=row.price_usd,
            liquidity_usd=row.liquidity_usd,
            tonscan_url=f"{settings.tonscan_base_url}/jetton/{row.address}",
        )
        for row in rows
    ]


@app.get("/tokens/{address}", response_model=Token)
async def get_token(address: str) -> Token:
    try:
        data = await tonapi_client.get_jetton(address)
    except Exception as exc:  # noqa: BLE001 - propaga como 404 para o gateway
        raise HTTPException(status_code=404, detail="jetton not found") from exc

    metadata = data.get("metadata", {})
    return Token(
        address=address,
        symbol=metadata.get("symbol", "?"),
        name=metadata.get("name", "Unknown"),
        image=metadata.get("image"),
        tonscan_url=f"{settings.tonscan_base_url}/jetton/{address}",
    )


@app.get("/tokens/{address}/pools")
async def get_token_pools(address: str) -> dict:
    stonfi_pools: list = []
    dedust_pools: list = []
    try:
        stonfi_pools = (await stonfi_client.get_pools()).get("pool_list", [])
    except Exception:  # noqa: BLE001 - fonte externa opcional
        pass
    try:
        dedust_pools = await dedust_client.get_pools()
    except Exception:  # noqa: BLE001 - fonte externa opcional
        pass

    return {
        "address": address,
        "stonfi_pools": [p for p in stonfi_pools if address in str(p)],
        "dedust_pools": [p for p in dedust_pools if address in str(p)],
    }
