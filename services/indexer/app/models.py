from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    address: str
    symbol: str
    name: str
    decimals: int = 9
    image: str | None = None
    price_usd: float | None = None
    price_ton: float | None = None
    liquidity_usd: float | None = None
    holders_count: int | None = None
    tonscan_url: str


class TokenPage(BaseModel):
    items: list[Token]
    total: int


class PricePoint(BaseModel):
    timestamp: datetime
    price_usd: float


class Pool(BaseModel):
    dex: str
    pool_address: str
    token_address: str
    liquidity_usd: float
    volume_24h_usd: float | None = None
