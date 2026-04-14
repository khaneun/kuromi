from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

from src.agents.base import BaseAgent
from src.core.event_bus import EventBus
from src.core.state import SharedState


class ImproverAgent(BaseAgent):
    """LLM-driven meta-agent. Reads performance reports, proposes new
    strategy parameters, emits improver.params_updated for StrategyAgent.

    Keep the surface area narrow: Improver never places orders directly.
    """

    name = "improver"

    SYSTEM_PROMPT = (
        "You are a quantitative trading meta-optimizer. Given a performance report, "
        "current strategy parameters, and active trading positions, propose improvements. "
        "Respond with a single JSON object with exactly three keys:\n"
        "1) 'params': object mapping parameter names to new numeric values (only include changes).\n"
        "2) 'ticker_advice': object with 'add' (list of Upbit KRW-XXX codes to consider adding) "
        "and 'remove' (list of currently active tickers to consider removing). "
        "Base removal on poor realized PnL or weak signals. Base additions on momentum/volume leaders. "
        "Be conservative — only recommend when evidence is clear. Empty lists are fine.\n"
        "3) 'reasoning': concise Korean string (2-4 sentences) explaining WHY each parameter was changed "
        "based on the performance data. Be specific about which metrics drove each decision."
    )

    def __init__(
        self,
        bus: EventBus,
        state: SharedState,
        api_key: str,
        cadence_sec: int = 3600,
        model: str = "claude-sonnet-4-6",
        seed_file: str | None = None,
    ) -> None:
        super().__init__(bus, state)
        self.api_key = api_key
        self.cadence_sec = cadence_sec
        self.model = model
        self.seed_file = seed_file
        self._last_report: dict | None = None
        self._feedback_log: deque[dict] = deque(maxlen=100)
        self._ticker_advice: dict = {"add": [], "remove": []}  # B: 최신 티커 편입/편출 추천
        self._last_advice_ts: float = 0.0
        self._log_path = "data/improver_log.jsonl"
        self._load_log()
        self.subscribe("performance.report", self._on_report)

    async def setup(self) -> None:
        if not self.seed_file:
            return
        path = Path(self.seed_file)
        if not path.exists():
            self.log(f"no seed at {path}")
            return
        try:
            seed = json.loads(path.read_text())
            if isinstance(seed, dict) and seed:
                await self.emit("improver.params_updated", seed)
                self._append_log({"ts": time.time(), "updates": seed, "source": "seed"})
                self.log(f"seed applied from {path}: keys={list(seed.keys())}")
        except Exception as exc:
            self.log(f"seed load error: {exc}")

    async def _on_report(self, event) -> None:
        report = dict(event.payload) if isinstance(event.payload, dict) else {}
        # B: 현재 포지션(티커) 정보 포함 → LLM 편입/편출 추천 근거로 활용
        cap = self.state.capital
        report["active_tickers"] = list(cap.positions.keys())
        report["realized_per_ticker"] = {
            t: round(pnl, 2) for t, pnl in cap.snapshot(self.state.last_prices).get("realized_per_ticker", {}).items()
        }
        self._last_report = report

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.cadence_sec)
            if not self._last_report or not self.api_key:
                continue
            try:
                result = await self._ask_llm(self._last_report, self.state.strategy_params)
                updates = result.get("params", {})
                advice = result.get("ticker_advice", {})
                if isinstance(advice, dict):
                    self._ticker_advice = {
                        "add": [t for t in advice.get("add", []) if isinstance(t, str)],
                        "remove": [t for t in advice.get("remove", []) if isinstance(t, str)],
                    }
                    self._last_advice_ts = time.time()
                    await self.emit("improver.ticker_advice", {
                        "add": self._ticker_advice["add"],
                        "remove": self._ticker_advice["remove"],
                        "ts": self._last_advice_ts,
                    })
                if updates:
                    before = {k: self.state.strategy_params.get(k) for k in updates}
                    reasoning = result.get("reasoning", "")
                    await self.emit("improver.params_updated", {
                        "params": updates,
                        "before": before,
                        "reasoning": reasoning,
                    })
                self._append_log({
                    "ts": time.time(),
                    "updates": updates,
                    "ticker_advice": self._ticker_advice,
                    "reasoning": result.get("reasoning", ""),
                    "source": "llm",
                })
            except Exception as exc:
                self.log(f"improver error: {exc}")

    def _load_log(self) -> None:
        p = Path(self._log_path)
        if not p.exists():
            return
        try:
            for line in p.read_text().strip().splitlines()[-100:]:
                self._feedback_log.append(json.loads(line))
        except Exception:
            pass

    def _append_log(self, entry: dict) -> None:
        self._feedback_log.append(entry)
        try:
            Path(self._log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def feedback_log(self) -> list[dict]:
        return list(self._feedback_log)

    def ticker_advice(self) -> dict:
        """B: 최신 LLM 티커 편입/편출 추천 (ts: Unix timestamp of last update)."""
        return {**self._ticker_advice, "ts": self._last_advice_ts}

    async def _ask_llm(self, report: dict, params: dict) -> dict:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        msg = await client.messages.create(
            model=self.model,
            max_tokens=768,
            system=self.SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps({"report": report, "params": params}),
                }
            ],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        raw = self._safe_json(text)
        # 구버전 응답(params만 있는 flat dict) 호환 처리
        if raw and "params" not in raw and "ticker_advice" not in raw:
            return {"params": raw, "ticker_advice": {"add": [], "remove": []}}
        return raw

    @staticmethod
    def _safe_json(text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
