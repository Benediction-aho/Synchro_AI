import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from websockets.asyncio.server import serve

from synchro.services.data_ingestion.client import DerivAPIError, DerivWSClient


def _tick_payload(symbol: str, quote: str, epoch: int) -> dict:
    return {
        "msg_type": "tick",
        "symbol": symbol,
        "quote": quote,
        "epoch": epoch,
        "pip_size": 2,
    }


async def _fake_deriv_handler(ws):
    async for raw in ws:
        req = json.loads(raw)
        rid = req.get("req_id")
        if "ping" in req:
            await ws.send(json.dumps({"pong": "pong", "req_id": rid}))
        elif "ticks_history" in req:
            n = int(req.get("count", 3))
            candles = [
                {"epoch": str(1700000000 + i), "open": "1.0", "high": "2.0", "low": "0.5", "close": "1.5"}
                for i in range(n)
            ]
            await ws.send(json.dumps({"candles": candles, "req_id": rid}))
        elif req.get("boom"):
            await ws.send(json.dumps({"error": {"code": "Boom", "message": "exploded"}, "req_id": rid}))
        elif "ticks" in req and req.get("subscribe"):
            symbol = req["ticks"]
            confirm = {
                "echo_req": req,
                "msg_type": "tick",
                "subscription": {"id": "SUB-1"},
                "req_id": rid,
                "tick": _tick_payload(symbol, "100.50", 1700000000),
            }
            await ws.send(json.dumps(confirm))
            for i in range(1, 4):
                await asyncio.sleep(0.01)
                await ws.send(
                    json.dumps(
                        {
                            "echo_req": req,
                            "msg_type": "tick",
                            "req_id": rid,
                            "tick": _tick_payload(symbol, str(100 + i), 1700000000 + i),
                        }
                    )
                )


@asynccontextmanager
async def fake_deriv_server():
    server = await serve(_fake_deriv_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


def _run(coro):
    asyncio.run(coro)


def test_ping():
    async def scenario():
        async with fake_deriv_server() as url:
            async with DerivWSClient(url, app_id="1089") as client:
                latency = await client.ping()
                assert latency >= 0

    _run(scenario())


def test_error_raises_api_error():
    async def scenario():
        async with fake_deriv_server() as url:
            async with DerivWSClient(url, app_id="1089") as client:
                with pytest.raises(DerivAPIError) as exc_info:
                    await client.request({"boom": 1})
                assert exc_info.value.code == "Boom"

    _run(scenario())


def test_subscribe_receives_stream():
    async def scenario():
        ticks = []
        all_received = asyncio.Event()

        async def callback(tick):
            ticks.append(tick)
            if len(ticks) == 4:
                all_received.set()

        async with fake_deriv_server() as url:
            async with DerivWSClient(url, app_id="1089") as client:
                stream_id = await client.subscribe_ticks("R_75", callback)
                await asyncio.wait_for(all_received.wait(), timeout=5)

        assert [t["quote"] for t in ticks] == ["100.50", "101", "102", "103"]
        assert all(t["symbol"] == "R_75" for t in ticks)
        assert isinstance(stream_id, int)

    _run(scenario())


def test_get_candles_parses_floats():
    async def scenario():
        async with fake_deriv_server() as url:
            async with DerivWSClient(url, app_id="1089") as client:
                candles = await client.get_candles("R_75", count=3)
                assert len(candles) == 3
                first = candles[0]
                assert set(first.keys()) == {"epoch", "open", "high", "low", "close"}
                assert isinstance(first["close"], float)
                assert isinstance(first["epoch"], int)

    _run(scenario())


def test_request_without_connection():
    async def scenario():
        client = DerivWSClient("ws://127.0.0.1:1", app_id="1089")
        with pytest.raises(RuntimeError):
            await client.request({"ping": 1})

    _run(scenario())
