from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class Position:
    ticker: str
    entry_price: float
    volume: float
    side: str = "buy"

    @property
    def cost(self) -> float:
        return self.entry_price * self.volume

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.entry_price) * self.volume

    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.entry_price == 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price

    def to_dict(self, current_price: float | None = None) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ticker": self.ticker,
            "entry_price": self.entry_price,
            "volume": self.volume,
            "cost": self.cost,
        }
        if current_price is not None:
            d["current_price"] = current_price
            d["market_value"] = current_price * self.volume
            d["unrealized_pnl"] = self.unrealized_pnl(current_price)
            d["unrealized_pnl_pct"] = self.unrealized_pnl_pct(current_price)
        return d


class Capital:
    """Thread-safe capital tracker. Single source of truth for balances."""

    def __init__(self, initial_krw: float = 0.0) -> None:
        self._lock = threading.Lock()
        self._krw: float = initial_krw        # 가용(free) KRW
        self._locked_krw: float = 0.0         # 미체결 주문에 묶인 KRW
        self._initial_krw: float = initial_krw
        self._positions: dict[str, Position] = {}
        self._realized_pnl: float = 0.0
        self._realized_per_ticker: dict[str, float] = {}  # A: 티커별 실현 손익
        self._trade_count: int = 0

    # ---- read ----
    @property
    def available_krw(self) -> float:
        """주문 가능한 가용 KRW (locked 제외)."""
        with self._lock:
            return self._krw

    @property
    def locked_krw(self) -> float:
        """미체결 주문에 묶인 KRW."""
        with self._lock:
            return self._locked_krw

    @property
    def positions(self) -> dict[str, Position]:
        with self._lock:
            return dict(self._positions)

    @property
    def realized_pnl(self) -> float:
        with self._lock:
            return self._realized_pnl

    @property
    def trade_count(self) -> int:
        with self._lock:
            return self._trade_count

    def position_cost(self) -> float:
        with self._lock:
            return sum(p.cost for p in self._positions.values())

    def total_equity(self, prices: dict[str, float]) -> float:
        """총 자산 = 가용 KRW + 주문 중 KRW + 코인 평가액."""
        with self._lock:
            equity = self._krw + self._locked_krw
            for ticker, pos in self._positions.items():
                price = prices.get(ticker, pos.entry_price)
                equity += price * pos.volume
            return equity

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        with self._lock:
            return sum(
                pos.unrealized_pnl(prices.get(ticker, pos.entry_price))
                for ticker, pos in self._positions.items()
            )

    def total_return_pct(self, prices: dict[str, float]) -> float:
        if self._initial_krw == 0:
            return 0.0
        return (self.total_equity(prices) - self._initial_krw) / self._initial_krw

    # ---- write ----
    def set_krw(self, amount: float) -> None:
        with self._lock:
            self._krw = amount

    def open_position(self, ticker: str, price: float, volume: float) -> Position:
        cost = price * volume
        with self._lock:
            if cost > self._krw:
                raise InsufficientFundsError(
                    f"need {cost:.0f} KRW, have {self._krw:.0f}"
                )
            self._krw -= cost
            pos = Position(ticker=ticker, entry_price=price, volume=volume)
            self._positions[ticker] = pos
            self._trade_count += 1
            return pos

    def close_position(self, ticker: str, price: float) -> float:
        with self._lock:
            pos = self._positions.pop(ticker, None)
            if pos is None:
                return 0.0
            proceeds = price * pos.volume
            pnl = proceeds - pos.cost
            self._krw += proceeds
            self._realized_pnl += pnl
            self._realized_per_ticker[ticker] = self._realized_per_ticker.get(ticker, 0.0) + pnl
            self._trade_count += 1
            return pnl

    def sync_from_upbit(self, accounts: list[dict], prices: dict[str, float]) -> None:
        """Upbit 계좌를 Capital 상태에 동기화.
        balance: 가용 잔고 / locked: 미체결 주문에 묶인 수량.
        코인은 balance+locked 합산을 포지션 볼륨으로 사용."""
        with self._lock:
            self._positions.clear()
            self._krw = 0.0
            self._locked_krw = 0.0
            for acc in accounts:
                currency = acc["currency"]
                balance = float(acc.get("balance", 0))
                locked = float(acc.get("locked", 0))
                total = balance + locked
                if total <= 0:
                    continue
                if currency == "KRW":
                    self._krw = balance          # 주문 가능 KRW
                    self._locked_krw = locked    # 미체결 매수 주문에 묶인 KRW
                    continue
                ticker = f"KRW-{currency}"
                avg_buy = float(acc.get("avg_buy_price", 0))
                if avg_buy > 0:
                    # locked 코인도 포지션에 포함 (미체결 매도 주문 중인 수량)
                    self._positions[ticker] = Position(
                        ticker=ticker, entry_price=avg_buy, volume=total
                    )
            if self._initial_krw == 0:
                # 이미 락을 보유 중이므로 total_equity() 재호출 금지 (데드락) — 인라인 계산
                equity = self._krw + self._locked_krw
                for ticker, pos in self._positions.items():
                    equity += prices.get(ticker, pos.entry_price) * pos.volume
                self._initial_krw = equity

    def snapshot(self, prices: dict[str, float]) -> dict[str, Any]:
        equity = self.total_equity(prices)
        with self._lock:
            realized_per_ticker = dict(self._realized_per_ticker)
        return {
            "available_krw": self.available_krw,
            "locked_krw": self.locked_krw,
            "position_cost": self.position_cost(),
            "total_equity": equity,
            "unrealized_pnl": self.unrealized_pnl(prices),
            "realized_pnl": self.realized_pnl,
            "realized_per_ticker": realized_per_ticker,   # A: 티커별 실현 손익
            "total_return_pct": self.total_return_pct(prices),
            "trade_count": self.trade_count,
            "positions": {
                t: p.to_dict(prices.get(t)) for t, p in self.positions.items()
            },
        }


class InsufficientFundsError(Exception):
    pass
