import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert

from app.clients.tonapi import tonapi_client
from app.config import settings
from app.db import TokenRow, async_session

logger = logging.getLogger(__name__)

# Endereços de jettons "seed" para acompanhar por padrão. Em produção isto
# viria de uma lista configurável (watchlist do usuário, trending do TonAPI).
WATCHED_JETTONS: list[str] = []


async def refresh_watched_tokens() -> None:
    if not WATCHED_JETTONS:
        return
    async with async_session() as session:
        for address in WATCHED_JETTONS:
            try:
                data = await tonapi_client.get_jetton(address)
            except Exception:
                logger.exception("failed to refresh jetton %s", address)
                continue

            metadata = data.get("metadata", {})
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
        await session.commit()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_watched_tokens,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="refresh_watched_tokens",
    )
    scheduler.start()
    return scheduler
