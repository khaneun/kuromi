from __future__ import annotations

import json
import os
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
    improver_seed_file: str = "data/improver_seed.json"
    cryptoquant_api_key: str = ""

    @property
    def tickers(self) -> list[str]:
        return [
            t.strip()
            for t in os.getenv("TRADING_TICKERS", "KRW-BTC,KRW-ETH").split(",")
            if t.strip()
        ]

    def initial_runtime_defaults(self) -> dict:
        """RuntimeConfig 파일 초기 생성 시 사용할 기본값 (.env에서 읽음)."""
        return {
            "dry_run": os.getenv("DRY_RUN", "true").lower() in ("true", "1"),
            "trading_tickers": [
                t.strip()
                for t in os.getenv("TRADING_TICKERS", "KRW-BTC,KRW-ETH").split(",")
                if t.strip()
            ],
            "max_concurrent_positions": int(os.getenv("MAX_CONCURRENT_POSITIONS", "3")),
            "per_trade_risk_pct": float(os.getenv("PER_TRADE_RISK_PCT", "0.01")),
            "improver_cadence_sec": int(os.getenv("IMPROVER_CADENCE_SEC", "3600")),
            "usdkrw_rate": float(os.getenv("USDKRW_RATE", "1380")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }

    def hydrate_from_secrets_manager(self) -> Settings:
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
