import asyncio
import contextlib
import itertools
import json
import logging
from typing import Any, Awaitable, Callable

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

TickCallback = Callable[[dict], Awaitable[None]]


class DerivAPIError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class DerivWSClient:
    def __init__(self, ws_url: str, app_id: str = "", request_timeout: float = 10.0):
        self._url = f"{ws_url}?app_id={app_id}" if app_id else ws_url
        self._request_timeout = request_timeout
        self._ws: ClientConnection | None = None
        self._req_ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._callbacks: dict[int, TickCallback] = {}
        self._subscription_ids: dict[int, str] = {}
        self._reader: asyncio.Task | None = None

    async def connect(self) -> None:
        self._ws = await connect(self._url, open_timeout=self._request_timeout)
        self._reader = asyncio.create_task(self._read_loop())
        logger.info("Connected to %s", self._url.split("?")[0])

    async def close(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
            self._reader = None
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> "DerivWSClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                self._dispatch(json.loads(raw))
        except ConnectionClosed:
            logger.warning("Deriv WebSocket connection closed")

    def _extract_req_id(self, msg: dict) -> int | None:
        req_id = msg.get("req_id")
        if req_id is None:
            req_id = (msg.get("echo_req") or {}).get("req_id")
        if isinstance(req_id, int):
            return req_id
        return None

    def _dispatch(self, msg: dict) -> None:
        req_id = self._extract_req_id(msg)
        if req_id is None:
            logger.debug("Ignoring unroutable message (msg_type=%s)", msg.get("msg_type"))
            return
        future = self._pending.pop(req_id, None)
        if future is not None and not future.done():
            future.set_result(msg)
        callback = self._callbacks.get(req_id)
        tick = msg.get("tick")
        if callback is not None and tick is not None:
            asyncio.get_running_loop().create_task(self._run_callback(callback, tick))

    async def _run_callback(self, callback: TickCallback, tick: dict) -> None:
        try:
            await callback(tick)
        except Exception:
            logger.exception("Tick callback raised")

    def _raise_on_error(self, msg: dict) -> None:
        if "error" in msg:
            err = msg["error"]
            raise DerivAPIError(err.get("code", "UnknownCode"), err.get("message", ""))

    async def request(self, payload: dict) -> dict:
        if self._ws is None:
            raise RuntimeError("Client not connected; call connect() first")
        req_id = next(self._req_ids)
        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        try:
            await self._ws.send(json.dumps({**payload, "req_id": req_id}))
            msg = await asyncio.wait_for(future, timeout=self._request_timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise
        self._raise_on_error(msg)
        return msg

    async def ping(self) -> float:
        start = asyncio.get_running_loop().time()
        await self.request({"ping": 1})
        return round((asyncio.get_running_loop().time() - start) * 1000, 2)

    async def subscribe_ticks(self, symbol: str, callback: TickCallback) -> int:
        if self._ws is None:
            raise RuntimeError("Client not connected; call connect() first")
        req_id = next(self._req_ids)
        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        self._callbacks[req_id] = callback
        await self._ws.send(
            json.dumps({"ticks": symbol, "subscribe": 1, "req_id": req_id})
        )
        try:
            msg = await asyncio.wait_for(future, timeout=self._request_timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            self._callbacks.pop(req_id, None)
            raise
        self._raise_on_error(msg)
        subscription_id = (msg.get("subscription") or {}).get("id", "")
        self._subscription_ids[req_id] = subscription_id
        logger.info("Subscribed to %s (stream id=%s)", symbol, subscription_id or "?")
        return req_id

    async def unsubscribe_ticks(self, stream_req_id: int) -> None:
        subscription_id = self._subscription_ids.pop(stream_req_id, None)
        self._callbacks.pop(stream_req_id, None)
        if subscription_id:
            await self.request({"forget": subscription_id})

    async def get_candles(
        self, symbol: str, count: int = 60, granularity_seconds: int = 60
    ) -> list[dict[str, Any]]:
        msg = await self.request(
            {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "style": "candles",
                "granularity": granularity_seconds,
            }
        )
        candles = []
        for c in msg.get("candles", []):
            candles.append(
                {
                    "epoch": int(c["epoch"]),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                }
            )
        return candles


__all__ = ["DerivAPIError", "DerivWSClient", "WebSocketException"]
