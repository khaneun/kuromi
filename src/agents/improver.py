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
        "You are a quantitative trading meta-optimizer. Given a performance "
        "report and current strategy parameters, propose small, incremental "
        "parameter adjustments to improve risk-adjusted returns. Respond with "
        "a single JSON object mapping parameter names to new numeric values. "
        "Only include parameters you want to change."
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
        self._last_report = event.payload

    async def run(self) -> None:
        while not self.stopping:
            await self.sleep(self.cadence_sec)
            if not self._last_report or not self.api_key:
                continue
            try:
                updates = await self._ask_llm(self._last_report, self.state.strategy_params)
                if updates:
                    await self.emit("improver.params_updated", updates)
                    self._append_log({"ts": time.time(), "updates": updates, "source": "llm"})
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

    async def _ask_llm(self, report: dict, params: dict) -> dict:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        msg = await client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps({"report": report, "params": params}),
                }
            ],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return self._safe_json(text)

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
