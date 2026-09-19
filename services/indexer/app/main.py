import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select

from app.clients.dex import dedust_client, stonfi_client
from app.clients.tonapi import tonapi_client
from app.clients.toncenter import toncenter_client
from app.config import settings
from app.db import PriceHistoryRow, TokenRow, async_session, init_db
from app.models import PricePoint, Token, TokenPage
from app.tasks.poller import MIN_FEATURED_LIQUIDITY_USD, start_scheduler

MAX_PAGE_LIMIT = 100
MAX_HISTORY_DAYS = 30

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # O Postgres é opcional: sem DATABASE_URL acessível (ex.: deploy de
    # demonstração sem banco provisionado ainda), a API continua no ar e
    # /tokens simplesmente responde uma lista vazia em vez de derrubar o
    # processo inteiro.
    scheduler = None
    try:
        await init_db()
        scheduler = start_scheduler()
    except Exception:
        logger.exception("database unavailable, running without cache/scheduler")

    yield

    if scheduler is not None:
        scheduler.shutdown()
    await tonapi_client.aclose()
    await toncenter_client.aclose()
    await stonfi_client.aclose()
    await dedust_client.aclose()


app = FastAPI(title="PlumTrader Indexer", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/tokens", response_model=TokenPage)
async def list_tokens(limit: int = 20, offset: int = 0, q: str | None = None) -> TokenPage:
    limit = max(1, min(limit, MAX_PAGE_LIMIT))
    offset = max(0, offset)

    try:
        async with async_session() as session:
            # Só lista tokens com liquidez de verdade confirmada (>= o
            # mínimo). A sincronização geral de jettons (sem preço/liquidez
            # calculados) não aparece aqui — mostrar milhares de linhas com
            # "—" em tudo não ajuda ninguém.
            filters = [
                TokenRow.liquidity_usd.is_not(None),
                TokenRow.liquidity_usd >= MIN_FEATURED_LIQUIDITY_USD,
            ]
            if q:
                needle = f"%{q.strip()}%"
                filters.append(
                    or_(
                        TokenRow.symbol.ilike(needle),
                        TokenRow.name.ilike(needle),
                        TokenRow.address == q.strip(),
                    )
                )

            total = (
                await session.execute(select(func.count()).select_from(TokenRow).where(*filters))
            ).scalar_one()
            query = (
                select(TokenRow)
                .where(*filters)
                .order_by(TokenRow.liquidity_usd.desc().nullslast())
                .limit(limit)
                .offset(offset)
            )
            rows = (await session.execute(query)).scalars().all()
    except Exception:
        logger.exception("database unavailable, returning empty token list")
        return TokenPage(items=[], total=0)

    items = [
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
    return TokenPage(items=items, total=total)


@app.get("/tokens/{address}", response_model=Token)
async def get_token(address: str) -> Token:
    try:
        data = await tonapi_client.get_jetton(address)
    except Exception as exc:  # noqa: BLE001 - propaga como 404 para o gateway
        raise HTTPException(status_code=404, detail="jetton not found") from exc

    metadata = data.get("metadata", {})

    # A metadata vem sempre fresca da TonAPI, mas preço/liquidez só
    # existem no nosso cache (calculados pelo job de destaques) — sem
    # isso, a tela do token sempre mostraria "—".
    price_usd = None
    liquidity_usd = None
    try:
        async with async_session() as session:
            row = await session.get(TokenRow, address)
            if row is not None:
                price_usd = row.price_usd
                liquidity_usd = row.liquidity_usd
    except Exception:
        logger.exception("database unavailable, skipping cached price/liquidity")

    return Token(
        address=address,
        symbol=metadata.get("symbol", "?"),
        name=metadata.get("name", "Unknown"),
        image=metadata.get("image"),
        price_usd=price_usd,
        liquidity_usd=liquidity_usd,
        tonscan_url=f"{settings.tonscan_base_url}/jetton/{address}",
    )


@app.get("/tokens/{address}/price-history", response_model=list[PricePoint])
async def get_price_history(address: str, days: int = MAX_HISTORY_DAYS) -> list[PricePoint]:
    days = max(1, min(days, MAX_HISTORY_DAYS))
    cutoff = int(time.time()) - days * 24 * 60 * 60

    try:
        async with async_session() as session:
            query = (
                select(PriceHistoryRow)
                .where(PriceHistoryRow.address == address, PriceHistoryRow.recorded_at >= cutoff)
                .order_by(PriceHistoryRow.recorded_at.asc())
            )
            rows = (await session.execute(query)).scalars().all()
    except Exception:
        logger.exception("database unavailable, returning empty price history")
        return []

    return [
        PricePoint(timestamp=datetime.fromtimestamp(row.recorded_at, tz=timezone.utc), price_usd=row.price_usd)
        for row in rows
    ]


@app.get("/ton-price")
async def get_ton_price() -> dict:
    """Cotação da moeda nativa da rede TON — renomeada de Toncoin/TON para
    Gram (GRAM) em jun/2026, mas continua sendo a mesma moeda-base, não um
    jetton (por isso não aparece em /tokens, igual ETH não aparece como
    'token ERC-20' no Etherscan). A TonAPI ainda usa "ton" como
    identificador técnico do ativo — o rebrand é só de exibição."""
    try:
        data = await tonapi_client.get_rates(tokens="ton", currencies="usd")
        ton_rates = data.get("rates", {}).get("TON", {})
        return {
            "price_usd": ton_rates.get("prices", {}).get("USD"),
            "diff_24h": ton_rates.get("diff_24h", {}).get("USD"),
            "diff_7d": ton_rates.get("diff_7d", {}).get("USD"),
            "diff_30d": ton_rates.get("diff_30d", {}).get("USD"),
        }
    except Exception:
        logger.exception("failed to fetch TON price from TonAPI")
        return {"price_usd": None, "diff_24h": None, "diff_7d": None, "diff_30d": None}


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
