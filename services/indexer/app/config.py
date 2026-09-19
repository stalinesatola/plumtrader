from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tonapi_base_url: str = "https://tonapi.io"
    tonapi_key: str = ""
    toncenter_base_url: str = "https://toncenter.com/api/v2"
    toncenter_api_key: str = ""
    stonfi_base_url: str = "https://api.ston.fi"
    dedust_base_url: str = "https://api.dedust.io"
    tonscan_base_url: str = "https://tonscan.org"
    database_url: str = "postgresql+asyncpg://plumtrader:plumtrader@localhost:5432/plumtrader"
    redis_url: str = "redis://localhost:6379/0"
    # Cada ciclo pagina até MAX_PAGES * MAX_PAGE_SIZE jettons (ver
    # app/tasks/poller.py) — um intervalo curto sobrecarregaria a TonAPI
    # sem key (rate limit) e o Postgres free tier à toa, já que a lista de
    # jettons indexados não muda a cada poucos segundos.
    poll_interval_seconds: int = 600

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
