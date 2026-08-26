import asyncio

import pytest
from websockets.exceptions import WebSocketException

from synchro.services.data_ingestion.client import DerivAPIError, DerivWSClient

LIVE_URL = "wss://api.derivws.com/trading/v1/options/ws/public"
TEST_APP_ID = "1089"


def test_live_tick_stream():
    async def scenario():
        ticks = []
        received = asyncio.Event()

        async def callback(tick):
            if not ticks:
                received.set()
            ticks.append(tick)

        async with DerivWSClient(LIVE_URL, app_id="", request_timeout=10) as client:
            rtt = await client.ping()
            print(f"\nDeriv RTT: {rtt} ms")
            await client.subscribe_ticks("R_75", callback)
            await asyncio.wait_for(received.wait(), timeout=15)
            candles = await client.get_candles("R_75", count=5)
            assert len(candles) == 5

        assert ticks[0]["symbol"] == "R_75"
        assert float(ticks[0]["quote"]) > 0

    try:
        asyncio.run(scenario())
    except (OSError, TimeoutError, WebSocketException, DerivAPIError) as exc:
        pytest.skip(f"Deriv network unreachable or slow: {exc}")
