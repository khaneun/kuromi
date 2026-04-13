from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel


_DEFAULT_PATH = "data/runtime_config.json"
_LOCK = threading.Lock()


def _save_to_file(cfg: "RuntimeConfig", path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg.model_dump(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, str(p))


class RuntimeConfig(BaseModel):
    """Dashboard/운영 변경 가능한 설정. data/runtime_config.json에 저장."""

    model_config = {"extra": "ignore"}

    dry_run: bool = True
    trading_tickers: list[str] = ["KRW-BTC", "KRW-ETH"]
    max_concurrent_positions: int = 3
    per_trade_risk_pct: float = 0.01
    daily_loss_limit_pct: float = 0.03
    improver_cadence_sec: int = 10800
    usdkrw_rate: float = 1380.0
    decision_threshold: float = 0.5
    strategy_weights: dict[str, float] = {}
    llm_model: str = "claude-sonnet-4-6"
    llm_endpoint: str = ""
    log_level: str = "INFO"

    _file_path: str = _DEFAULT_PATH

    @classmethod
    def load_or_create(
        cls, path: str = _DEFAULT_PATH, defaults: dict | None = None
    ) -> RuntimeConfig:
        """파일이 있으면 로드, 없으면 defaults로 생성."""
        p = Path(path)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cfg = cls.model_validate(data)
            except Exception:
                cfg = cls(**(defaults or {}))
                _save_to_file(cfg, path)
        else:
            cfg = cls(**(defaults or {}))
            _save_to_file(cfg, path)
        cfg._file_path = path
        return cfg

    def save(self) -> None:
        """현재 설정을 파일에 원자적 저장."""
        with _LOCK:
            _save_to_file(self, self._file_path)

    def update_and_save(self, updates: dict[str, Any]) -> None:
        """부분 업데이트 후 저장."""
        with _LOCK:
            for k, v in updates.items():
                if k in self.model_fields:
                    setattr(self, k, v)
            _save_to_file(self, self._file_path)

    def apply(self, orchestrator: Any, state: Any, bus: Any = None) -> list[str]:
        """현재 설정을 실행 중인 Agent에 반영. 반환: 변경된 항목 목록."""
        applied: list[str] = []

        # ExecutionAgent: dry_run
        exec_agent = orchestrator.get_agent("execution")
        if exec_agent and hasattr(exec_agent, "dry_run"):
            exec_agent.dry_run = self.dry_run
            applied.append("dry_run")

        # RiskAgent: limits
        risk_agent = orchestrator.get_agent("risk")
        if risk_agent:
            if hasattr(risk_agent, "max_positions"):
                risk_agent.max_positions = self.max_concurrent_positions
            if hasattr(risk_agent, "per_trade_risk_pct"):
                risk_agent.per_trade_risk_pct = self.per_trade_risk_pct
            if hasattr(risk_agent, "daily_loss_limit_pct"):
                risk_agent.daily_loss_limit_pct = self.daily_loss_limit_pct
            applied.extend(
                ["max_concurrent_positions", "per_trade_risk_pct", "daily_loss_limit_pct"]
            )

        # ImproverAgent: cadence, model
        improver = orchestrator.get_agent("improver")
        if improver:
            if hasattr(improver, "cadence_sec"):
                improver.cadence_sec = self.improver_cadence_sec
            if hasattr(improver, "model"):
                improver.model = self.llm_model
            applied.extend(["improver_cadence_sec", "llm_model"])

        # PortfolioAgent: live mode 동기화
        portfolio = orchestrator.get_agent("portfolio")
        if portfolio and hasattr(portfolio, "live"):
            portfolio.live = not self.dry_run
            applied.append("portfolio_live")

        # StrategyAgent: decision_threshold, strategy_weights via state
        state.strategy_params["decision_threshold"] = self.decision_threshold
        if self.strategy_weights:
            state.strategy_params["strategy_weights"] = self.strategy_weights
        applied.extend(["decision_threshold", "strategy_weights"])

        return applied
