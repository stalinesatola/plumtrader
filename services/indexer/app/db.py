from sqlalchemy import BigInteger, Float, Index, Integer, String, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


def _to_asyncpg_url(url: str) -> str:
    # Render/Heroku-style providers entregam "postgres://" ou
    # "postgresql://" (driver síncrono); o SQLAlchemy async precisa do
    # dialeto asyncpg explícito no esquema da URL.
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


engine = create_async_engine(_to_asyncpg_url(settings.database_url), echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TokenRow(Base):
    __tablename__ = "tokens"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    holders_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_cap_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class PriceHistoryRow(Base):
    """Snapshot append-only de preço, usado para montar o gráfico de
    variação (ex.: últimos 30 dias). Só grava pontos reais calculados a
    partir das reservas do pool — nunca preenche lacunas com dado
    inventado."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String, index=True)
    price_usd: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (Index("ix_price_history_address_recorded_at", "address", "recorded_at"),)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all só cria tabelas que não existem — não adiciona
        # colunas numa tabela já existente em produção. Migração leve e
        # idempotente para as colunas adicionadas depois do deploy
        # inicial.
        for statement in (
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS holders_count INTEGER",
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS market_cap_usd FLOAT",
        ):
            await conn.execute(text(statement))


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
