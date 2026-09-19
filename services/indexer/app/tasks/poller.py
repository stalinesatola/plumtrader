import asyncio
import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert

from app.clients.dex import stonfi_client
from app.clients.tonapi import tonapi_client
from app.config import settings
from app.db import TokenRow, async_session

logger = logging.getLogger(__name__)

# Quantos pools (por liquidez) usar para montar os "tokens em destaque".
# Cada pool tem 2 lados (token0/token1), então isso rende até 2x esse
# número de tokens distintos.
FEATURED_POOL_LIMIT = 15

# Em vez de uma watchlist fixa (que exigiria endereços de contrato
# digitados à mão — arriscado numa plataforma de trading, um endereço
# errado manda o usuário pro token errado), a watchlist é populada
# dinamicamente com os jettons que a própria TonAPI indexa.
#
# MAX_PAGES limita quantas páginas de MAX_PAGE_SIZE jettons são buscadas
# por ciclo, para não sobrecarregar o Postgres free tier nem estourar o
# rate limit da TonAPI sem key. Ajuste conforme necessário.
MAX_PAGE_SIZE = 1000
MAX_PAGES = 3


async def refresh_watched_tokens() -> None:
    async with async_session() as session:
        last_account_id: str | None = None
        total = 0

        for _ in range(MAX_PAGES):
            try:
                data = await tonapi_client.list_jettons(
                    limit=MAX_PAGE_SIZE, last_account_id=last_account_id
                )
            except Exception:
                logger.exception("failed to list jettons from TonAPI")
                break

            jettons = data.get("jettons", [])
            if not jettons:
                break

            for jetton in jettons:
                metadata = jetton.get("metadata", {})
                address = metadata.get("address")
                if not address:
                    continue

                stmt = (
                    insert(TokenRow)
                    .values(
                        address=address,
                        symbol=metadata.get("symbol", "?"),
                        name=metadata.get("name", "Unknown"),
                        price_usd=None,
                        liquidity_usd=None,
                        updated_at=int(time.time()),
                    )
                    .on_conflict_do_update(
                        index_elements=[TokenRow.address],
                        set_={
                            "symbol": metadata.get("symbol", "?"),
                            "name": metadata.get("name", "Unknown"),
                            "updated_at": int(time.time()),
                        },
                    )
                )
                await session.execute(stmt)
                total += 1

            last_account_id = jettons[-1].get("metadata", {}).get("address")
            if not last_account_id or len(jettons) < MAX_PAGE_SIZE:
                break

        await session.commit()
        logger.info("refreshed %d jettons from TonAPI", total)


def _pool_liquidity_usd(pool: dict) -> float:
    try:
        return float(pool.get("lp_total_supply_usd") or 0)
    except (TypeError, ValueError):
        return 0.0


async def refresh_featured_tokens() -> None:
    """Popula/atualiza os tokens de maior liquidez nos pools do STON.fi.

    Usa dados reais de mercado (liquidez em USD) em vez de uma lista
    escolhida à mão, e reaproveita o mesmo endereço de contrato que o
    STON.fi já expõe — nunca inventamos endereço de jetton aqui.
    """
    try:
        data = await stonfi_client.get_pools()
    except Exception:
        logger.exception("failed to fetch STON.fi pools for featured tokens")
        return

    active_pools = [p for p in data.get("pool_list", []) if not p.get("deprecated")]
    top_pools = sorted(active_pools, key=_pool_liquidity_usd, reverse=True)[:FEATURED_POOL_LIMIT]

    # endereço -> maior liquidez em que ele aparece entre os pools top
    candidates: dict[str, float] = {}
    for pool in top_pools:
        liquidity = _pool_liquidity_usd(pool)
        for address in (pool.get("token0_address"), pool.get("token1_address")):
            if address and liquidity > candidates.get(address, 0):
                candidates[address] = liquidity

    async with async_session() as session:
        total = 0
        for address, liquidity_usd in candidates.items():
            try:
                info = await tonapi_client.get_jetton(address)
            except Exception:
                logger.warning("skipping featured token %s: metadata fetch failed", address)
                continue

            metadata = info.get("metadata", {})
            stmt = (
                insert(TokenRow)
                .values(
                    address=address,
                    symbol=metadata.get("symbol", "?"),
                    name=metadata.get("name", "Unknown"),
                    price_usd=None,
                    liquidity_usd=liquidity_usd,
                    updated_at=int(time.time()),
                )
                .on_conflict_do_update(
                    index_elements=[TokenRow.address],
                    set_={
                        "symbol": metadata.get("symbol", "?"),
                        "name": metadata.get("name", "Unknown"),
                        "liquidity_usd": liquidity_usd,
                        "updated_at": int(time.time()),
                    },
                )
            )
            await session.execute(stmt)
            total += 1

        await session.commit()
        logger.info("refreshed %d featured tokens from STON.fi pools", total)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_watched_tokens,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="refresh_watched_tokens",
    )
    scheduler.add_job(
        refresh_featured_tokens,
        "interval",
        seconds=settings.featured_poll_interval_seconds,
        id="refresh_featured_tokens",
    )
    scheduler.start()
    # Roda os destaques uma vez já na subida em vez de esperar o primeiro
    # intervalo — é rápido (poucos pools) e é a primeira coisa que o
    # miniapp mostra.
    asyncio.create_task(refresh_featured_tokens())
    return scheduler
