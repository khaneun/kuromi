from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: str = "dev"
    aws_region: str = "ap-northeast-2"
    secrets_name: str | None = None

    upbit_access_key: str = ""
    upbit_secret_key: str = ""
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""
    anthropic_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/kuromi.db"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    dashboard_public_url: str = ""   # ex) http://3.35.45.73:8080 — Telegram /dashboard 용
    log_level: str = "INFO"

    initial_capital_krw: float = 0.0
    trading_tickers: str = "KRW-BTC,KRW-ETH"
    max_concurrent_positions: int = 3
    per_trade_risk_pct: float = 0.01
    daily_loss_limit_pct: float = 0.03
    improver_cadence_sec: int = 3600
    improver_seed_file: str = "data/improver_seed.json"
    cryptoquant_api_key: str = ""
    usdkrw_rate: float = 1380.0
    dry_run: bool = True

    @property
    def tickers(self) -> list[str]:
        return [t.strip() for t in self.trading_tickers.split(",") if t.strip()]

    def hydrate_from_secrets_manager(self) -> "Settings":
        if self.env == "dev" or not self.secrets_name:
            return self
        import boto3

        client = boto3.client("secretsmanager", region_name=self.aws_region)
        raw = client.get_secret_value(SecretId=self.secrets_name)["SecretString"]
        overrides = {k.lower(): v for k, v in json.loads(raw).items()}
        merged = {**self.model_dump(), **overrides}
        return Settings.model_validate(merged)


@lru_cache
def get_settings() -> Settings:
    return Settings().hydrate_from_secrets_manager()
