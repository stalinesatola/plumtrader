import asyncio
import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.clients.dex import stonfi_client
from app.clients.tonapi import tonapi_client
from app.config import settings
from app.db import PriceHistoryRow, TokenRow, async_session

logger = logging.getLogger(__name__)

PRICE_HISTORY_RETENTION_SECONDS = 30 * 24 * 60 * 60  # 30 dias

# Quantos pools (por liquidez) usar para montar os "tokens em destaque".
# Cada pool tem 2 lados (token0/token1), então isso rende até 2x esse
# número de tokens distintos.
FEATURED_POOL_LIMIT = 15

# Pools abaixo disso são ruído (liquidez baixa demais pra um preço
# confiável, risco alto de slippage/rug) — não entram nos destaques.
MIN_FEATURED_LIQUIDITY_USD = 1000.0

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


def _derive_price_usd(pool: dict, is_token0: bool, decimals: int) -> float | None:
    """Deriva o preço do token em USD a partir das reservas do pool.

    Pools constant-product (padrão STON.fi/Uniswap-V2) mantêm os dois
    lados com valor em USD aproximadamente igual, então
    preço ≈ (liquidez_total_usd / 2) / reserva_do_token. Usa só dados reais
    (reservas on-chain + liquidez total do pool), sem nenhum número
    inventado — é uma aproximação, não uma cotação exata de mercado.
    """
    try:
        total_usd = float(pool.get("lp_total_supply_usd") or 0)
        if total_usd <= 0:
            return None
        reserve_raw = pool.get("reserve0") if is_token0 else pool.get("reserve1")
        reserve = float(reserve_raw) / (10**decimals)
        if reserve <= 0:
            return None
        return (total_usd / 2) / reserve
    except (TypeError, ValueError):
        return None


async def refresh_featured_tokens() -> None:
    """Popula/atualiza os tokens de maior liquidez nos pools do STON.fi.

    Usa dados reais de mercado (liquidez e reservas em USD) em vez de uma
    lista escolhida à mão, e reaproveita o mesmo endereço de contrato que
    o STON.fi já expõe — nunca inventamos endereço de jetton aqui.
    """
    try:
        data = await stonfi_client.get_pools()
    except Exception:
        logger.exception("failed to fetch STON.fi pools for featured tokens")
        return

    active_pools = [
        p
        for p in data.get("pool_list", [])
        if not p.get("deprecated") and _pool_liquidity_usd(p) >= MIN_FEATURED_LIQUIDITY_USD
    ]
    top_pools = sorted(active_pools, key=_pool_liquidity_usd, reverse=True)[:FEATURED_POOL_LIMIT]

    # endereço -> (liquidez, pool onde apareceu com mais liquidez, é token0?)
    best: dict[str, tuple[float, dict, bool]] = {}
    for pool in top_pools:
        liquidity = _pool_liquidity_usd(pool)
        for is_token0, address in (
            (True, pool.get("token0_address")),
            (False, pool.get("token1_address")),
        ):
            if not address:
                continue
            current = best.get(address)
            if current is None or liquidity > current[0]:
                best[address] = (liquidity, pool, is_token0)

    async with async_session() as session:
        total = 0
        now = int(time.time())
        for address, (liquidity_usd, pool, is_token0) in best.items():
            try:
                info = await tonapi_client.get_jetton(address)
            except Exception:
                logger.warning("skipping featured token %s: metadata fetch failed", address)
                continue

            metadata = info.get("metadata", {})
            try:
                decimals = int(metadata.get("decimals") or 9)
            except (TypeError, ValueError):
                decimals = 9
            price_usd = _derive_price_usd(pool, is_token0, decimals)

            stmt = (
                insert(TokenRow)
                .values(
                    address=address,
                    symbol=metadata.get("symbol", "?"),
                    name=metadata.get("name", "Unknown"),
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[TokenRow.address],
                    set_={
                        "symbol": metadata.get("symbol", "?"),
                        "name": metadata.get("name", "Unknown"),
                        "price_usd": price_usd,
                        "liquidity_usd": liquidity_usd,
                        "updated_at": now,
                    },
                )
            )
            await session.execute(stmt)
            total += 1

            # Só grava histórico quando temos um preço real derivado das
            # reservas — nunca um ponto vazio/inventado.
            if price_usd is not None:
                await session.execute(
                    PriceHistoryRow.__table__.insert().values(
                        address=address, price_usd=price_usd, recorded_at=now
                    )
                )

        cutoff = now - PRICE_HISTORY_RETENTION_SECONDS
        await session.execute(delete(PriceHistoryRow).where(PriceHistoryRow.recorded_at < cutoff))

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
