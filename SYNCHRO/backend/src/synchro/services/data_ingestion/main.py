import argparse
import asyncio
import logging

from synchro.core.config import get_settings
from synchro.core.logging_config import setup_logging
from synchro.services.data_ingestion.client import DerivWSClient
from synchro.services.data_ingestion.publishers import get_publisher

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ("R_75", "frxEURUSD")


async def run(symbols: list[str], duration: float | None = None, report_interval: float = 5.0) -> None:
    setup_logging()
    settings = get_settings()
    app_id = settings.deriv_app_id or "1089"
    publisher = get_publisher(settings)
    await publisher.start()
    try:
        async with DerivWSClient(settings.deriv_ws_url, app_id) as client:
            latency = await client.ping()
            logger.info("Deriv RTT: %.2f ms", latency)
            for symbol in symbols:
                await client.subscribe_ticks(symbol, publisher.publish)
            elapsed = 0.0
            while duration is None or elapsed < duration:
                await asyncio.sleep(report_interval)
                elapsed += report_interval
                logger.info("ingested so far: %s", dict(publisher.counts) or "waiting for ticks...")
    finally:
        await publisher.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="SYNCHRO data ingestion runner")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="comma-separated symbols")
    parser.add_argument("--duration", type=float, default=30.0, help="seconds to run (omit for endless)")
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    try:
        asyncio.run(run(symbols, duration=args.duration))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
