from sqlalchemy import BigInteger, Float, String
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
    updated_at: Mapped[int] = mapped_column(BigInteger)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
