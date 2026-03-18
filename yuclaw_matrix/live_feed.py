"""yuclaw_matrix/live_feed.py — Real-time price feed for CRT scheduler.

Provides websocket and polling-based live price feeds that integrate
with the CRT scheduler. Uses free data sources:
- Finnhub websocket (free tier: 30 symbols)
- Yahoo Finance polling (unlimited, ~1s delay)
- Simulated feed for testing
"""
from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, Coroutine


@dataclass
class PriceTick:
    """A single price update."""
    symbol: str
    price: float
    timestamp: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None

    @property
    def mid(self) -> float:
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.price


class LiveFeed(ABC):
    """Abstract base for live price feeds."""

    @abstractmethod
    async def connect(self, symbols: list[str]):
        ...

    @abstractmethod
    async def get_price(self, symbol: str) -> Optional[PriceTick]:
        ...

    @abstractmethod
    async def close(self):
        ...


class YahooPollingFeed(LiveFeed):
    """Poll Yahoo Finance for near-real-time prices.

    No API key needed. ~1s delay. Good for 100+ symbols.
    """

    def __init__(self, poll_interval: float = 5.0):
        self._interval = poll_interval
        self._prices: dict[str, PriceTick] = {}
        self._symbols: list[str] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def connect(self, symbols: list[str]):
        self._symbols = symbols
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        # Initial fetch
        await self._fetch_all()

    async def _fetch_all(self):
        """Fetch prices for all symbols via yfinance."""
        try:
            import yfinance as yf
            # Batch download for efficiency
            tickers = " ".join(self._symbols)
            data = yf.download(tickers, period="1d", interval="1m",
                             progress=False, auto_adjust=True)
            if data.empty:
                return

            for sym in self._symbols:
                try:
                    if len(self._symbols) == 1:
                        price = float(data["Close"].iloc[-1])
                    else:
                        price = float(data["Close"][sym].iloc[-1])

                    self._prices[sym] = PriceTick(
                        symbol=sym,
                        price=price,
                        timestamp=time.time(),
                    )
                except (KeyError, IndexError):
                    pass
        except Exception as e:
            print(f"[LiveFeed] Yahoo poll error: {e}")

    async def _poll_loop(self):
        while self._running:
            await asyncio.sleep(self._interval)
            await self._fetch_all()

    async def get_price(self, symbol: str) -> Optional[PriceTick]:
        return self._prices.get(symbol)

    async def close(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class SimulatedFeed(LiveFeed):
    """Simulated price feed for testing and benchmarking.

    Generates realistic price movements with configurable volatility
    and bid/ask spreads.
    """

    def __init__(self, volatility: float = 0.001, spread_bps: float = 5.0):
        self._vol = volatility
        self._spread = spread_bps / 10000
        self._prices: dict[str, float] = {}
        self._tick_count = 0

    async def connect(self, symbols: list[str]):
        import random
        for sym in symbols:
            self._prices[sym] = 50.0 + random.random() * 200

    async def get_price(self, symbol: str) -> Optional[PriceTick]:
        import random
        if symbol not in self._prices:
            return None

        # Random walk with drift
        self._prices[symbol] *= 1 + (random.gauss(0.0001, self._vol))
        price = self._prices[symbol]
        half_spread = price * self._spread / 2

        self._tick_count += 1
        return PriceTick(
            symbol=symbol,
            price=price,
            timestamp=time.time(),
            bid=price - half_spread,
            ask=price + half_spread,
            spread=2 * half_spread,
            volume=random.randint(100, 10000),
        )

    async def close(self):
        pass


class FinnhubWebsocketFeed(LiveFeed):
    """Finnhub websocket feed for real-time prices.

    Requires FINNHUB_API_KEY environment variable.
    Free tier: 30 symbols, real-time US stock prices.
    """

    def __init__(self):
        import os
        self._api_key = os.getenv("FINNHUB_API_KEY", "")
        self._prices: dict[str, PriceTick] = {}
        self._ws = None
        self._task: Optional[asyncio.Task] = None

    async def connect(self, symbols: list[str]):
        if not self._api_key:
            print("[LiveFeed] No FINNHUB_API_KEY set, using Yahoo polling fallback")
            return

        try:
            import websockets
            uri = f"wss://ws.finnhub.io?token={self._api_key}"
            self._ws = await websockets.connect(uri)

            for sym in symbols[:30]:  # Free tier limit
                await self._ws.send(json.dumps({"type": "subscribe", "symbol": sym}))

            self._task = asyncio.create_task(self._listen())
        except ImportError:
            print("[LiveFeed] websockets not installed, use: pip install websockets")
        except Exception as e:
            print(f"[LiveFeed] Finnhub connection failed: {e}")

    async def _listen(self):
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                if data.get("type") == "trade":
                    for trade in data.get("data", []):
                        sym = trade.get("s", "")
                        self._prices[sym] = PriceTick(
                            symbol=sym,
                            price=trade.get("p", 0),
                            timestamp=trade.get("t", time.time()) / 1000,
                            volume=trade.get("v", 0),
                        )
        except Exception:
            pass

    async def get_price(self, symbol: str) -> Optional[PriceTick]:
        return self._prices.get(symbol)

    async def close(self):
        if self._task:
            self._task.cancel()
        if self._ws:
            await self._ws.close()


def create_feed(feed_type: str = "auto") -> LiveFeed:
    """Factory for creating the appropriate feed.

    auto: tries Finnhub websocket, falls back to Yahoo polling
    simulated: for testing/benchmarking
    yahoo: polling-based, always works
    finnhub: websocket, requires API key
    """
    import os
    if feed_type == "simulated":
        return SimulatedFeed()
    elif feed_type == "finnhub" or (feed_type == "auto" and os.getenv("FINNHUB_API_KEY")):
        return FinnhubWebsocketFeed()
    else:
        return YahooPollingFeed()
