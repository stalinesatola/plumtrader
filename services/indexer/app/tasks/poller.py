import asyncio
import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.clients.dex import dedust_client, stonfi_client
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


def _market_cap_usd(price_usd: float | None, total_supply_raw: object, decimals: int) -> float | None:
    """Cap. de mercado = preço × total_supply ajustado por decimais.

    total_supply vem no nível raiz do JettonInfo (TEP-74), não dentro de
    metadata. Sem preço ou sem total_supply, não calcula (nunca inventa).
    """
    if price_usd is None or total_supply_raw is None:
        return None
    try:
        total_supply = float(total_supply_raw) / (10**decimals)
        return price_usd * total_supply
    except (TypeError, ValueError):
        return None


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


def _dedust_pool_liquidity_and_reserve(
    pool: dict, ton_price_usd: float | None
) -> tuple[str, float, float, float] | None:
    """Deriva liquidez em USD e a reserva bruta do jetton num pool do
    DeDust (schema real, verificado em github.com/dedust-io/sdk:
    `assets`/`reserves` são pares na mesma ordem, cada asset é
    `{type: 'native'}` ou `{type: 'jetton', address, metadata}`).

    NÃO ajusta a reserva por decimais aqui, de propósito: em produção o
    `metadata` do lado jetton às vezes vem `null` (visto em pools reais do
    DeDust), então usar `metadata.decimals` daria um valor errado (caindo
    no default 9) sempre que o token real tivesse outro número de casas —
    preço/liquidez sairiam errados por ordens de grandeza sem nenhum
    aviso. Os decimais confiáveis vêm depois da chamada à TonAPI (mesmo
    padrão já usado pro STON.fi em `_derive_price_usd`), então só
    devolvemos aqui a reserva crua pra conversão ser feita com o valor
    certo.

    Ao contrário do STON.fi (que já expõe `lp_total_supply_usd` pronto), o
    DeDust só dá reservas brutas — só é possível converter pra USD sem
    inventar quando um dos lados do pool é o próprio TON nativo (usamos a
    cotação real de `/ton-price`). Pools jetton/jetton (sem lado TON)
    ficam de fora: não há como bootstrapar o valor em USD com dado real.
    """
    if not ton_price_usd:
        return None
    assets = pool.get("assets") or []
    reserves = pool.get("reserves") or []
    if len(assets) != 2 or len(reserves) != 2:
        return None

    native_idx = next((i for i, a in enumerate(assets) if a.get("type") == "native"), None)
    if native_idx is None:
        return None
    jetton_idx = 1 - native_idx
    jetton_asset = assets[jetton_idx]
    if jetton_asset.get("type") != "jetton":
        return None
    address = jetton_asset.get("address")
    if not address:
        return None

    try:
        reserve_ton = float(reserves[native_idx]) / 1e9
        reserve_jetton_raw = float(reserves[jetton_idx])
        if reserve_ton <= 0 or reserve_jetton_raw <= 0:
            return None
        reserve_ton_usd = reserve_ton * ton_price_usd
        # Mesma aproximação 50/50 de pool constant-product já usada pro
        # STON.fi em `_derive_price_usd`.
        return address, reserve_ton_usd * 2, reserve_ton_usd, reserve_jetton_raw
    except (TypeError, ValueError):
        return None


def _dedust_price_usd(reserve_ton_usd: float, reserve_jetton_raw: float, decimals: int) -> float | None:
    """Segunda metade do cálculo acima, aplicada só depois que os decimais
    confiáveis chegam da TonAPI."""
    try:
        reserve_jetton = reserve_jetton_raw / (10**decimals)
        if reserve_jetton <= 0:
            return None
        return reserve_ton_usd / reserve_jetton
    except (TypeError, ValueError, ZeroDivisionError):
        return None


async def refresh_featured_tokens() -> None:
    """Popula/atualiza os tokens de maior liquidez nos pools do STON.fi e
    do DeDust — duas fontes reais de mercado (nunca uma lista escolhida à
    mão), reaproveitando os mesmos endereços de contrato que os DEXes já
    expõem.
    """
    results = await asyncio.gather(
        stonfi_client.get_pools(),
        dedust_client.get_pools(),
        tonapi_client.get_rates(tokens="ton", currencies="usd"),
        return_exceptions=True,
    )
    stonfi_data, dedust_data, ton_rates_data = results

    if isinstance(stonfi_data, Exception):
        logger.warning("failed to fetch STON.fi pools for featured tokens: %s", stonfi_data)
        stonfi_data = {}
    if isinstance(dedust_data, Exception):
        logger.warning("failed to fetch DeDust pools for featured tokens: %s", dedust_data)
        dedust_data = []

    # Preço do TON em USD: única forma de converter as reservas brutas do
    # DeDust pra USD sem inventar (STON.fi já dá liquidez em USD pronta).
    ton_price_usd = None
    if isinstance(ton_rates_data, Exception):
        logger.warning("failed to fetch TON/USD rate for DeDust price derivation: %s", ton_rates_data)
    else:
        try:
            ton_price_usd = float(ton_rates_data.get("rates", {}).get("TON", {}).get("prices", {}).get("USD"))
        except (TypeError, ValueError):
            ton_price_usd = None

    active_pools = [
        p
        for p in stonfi_data.get("pool_list", [])
        if not p.get("deprecated") and _pool_liquidity_usd(p) >= MIN_FEATURED_LIQUIDITY_USD
    ]
    top_stonfi_pools = sorted(active_pools, key=_pool_liquidity_usd, reverse=True)[:FEATURED_POOL_LIMIT]

    dedust_derived = [
        derived
        for pool in dedust_data
        if (derived := _dedust_pool_liquidity_and_reserve(pool, ton_price_usd)) is not None
        and derived[1] >= MIN_FEATURED_LIQUIDITY_USD
    ]
    dedust_derived.sort(key=lambda d: d[1], reverse=True)
    top_dedust_pools = dedust_derived[:FEATURED_POOL_LIMIT]

    # endereço -> (liquidez_usd, fonte, payload). payload é (pool, is_token0)
    # pro STON.fi, ou (reserve_ton_usd, reserve_jetton_raw) pro DeDust — em
    # ambos os casos o preço final só é calculado depois, já com os
    # decimais confiáveis vindos da chamada à TonAPI.
    best: dict[str, tuple[float, str, object]] = {}
    for pool in top_stonfi_pools:
        liquidity = _pool_liquidity_usd(pool)
        for is_token0, address in (
            (True, pool.get("token0_address")),
            (False, pool.get("token1_address")),
        ):
            if not address:
                continue
            current = best.get(address)
            if current is None or liquidity > current[0]:
                best[address] = (liquidity, "stonfi", (pool, is_token0))

    for address, liquidity, reserve_ton_usd, reserve_jetton_raw in top_dedust_pools:
        current = best.get(address)
        if current is None or liquidity > current[0]:
            best[address] = (liquidity, "dedust", (reserve_ton_usd, reserve_jetton_raw))

    async with async_session() as session:
        total = 0
        now = int(time.time())
        for address, (liquidity_usd, source, payload) in best.items():
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

            if source == "stonfi":
                pool, is_token0 = payload
                price_usd = _derive_price_usd(pool, is_token0, decimals)
            else:
                reserve_ton_usd, reserve_jetton_raw = payload
                price_usd = _dedust_price_usd(reserve_ton_usd, reserve_jetton_raw, decimals)

            # holders_count e total_supply vêm no nível raiz do JettonInfo
            # (não dentro de metadata) — mesmo objeto `info` que já
            # buscamos pra pegar symbol/name/decimals.
            holders_count = info.get("holders_count")
            if not isinstance(holders_count, int):
                holders_count = None
            market_cap_usd = _market_cap_usd(price_usd, info.get("total_supply"), decimals)

            stmt = (
                insert(TokenRow)
                .values(
                    address=address,
                    symbol=metadata.get("symbol", "?"),
                    name=metadata.get("name", "Unknown"),
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    holders_count=holders_count,
                    market_cap_usd=market_cap_usd,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[TokenRow.address],
                    set_={
                        "symbol": metadata.get("symbol", "?"),
                        "name": metadata.get("name", "Unknown"),
                        "price_usd": price_usd,
                        "liquidity_usd": liquidity_usd,
                        "holders_count": holders_count,
                        "market_cap_usd": market_cap_usd,
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
        logger.info(
            "refreshed %d featured tokens (%d STON.fi pools, %d DeDust pools)",
            total,
            len(top_stonfi_pools),
            len(top_dedust_pools),
        )


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
