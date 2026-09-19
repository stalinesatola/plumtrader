import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert

from app.clients.tonapi import tonapi_client
from app.config import settings
from app.db import TokenRow, async_session

logger = logging.getLogger(__name__)

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
