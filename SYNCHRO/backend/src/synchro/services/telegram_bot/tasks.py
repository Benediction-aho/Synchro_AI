"""Telegram Bot Celery tasks — Doc 4 item 19."""

from synchro.services.telegram_bot.bot import (
    crisis_broadcast_sync,
    notify_trade_sync,
    send_approval_card_sync,
    wait_for_approval_sync,
)


def send_approval_task(chat_id: int, title: str, details: dict, approval_id: int) -> dict:
    """Celery task: send approval card."""
    return send_approval_card_sync(chat_id, title, details, approval_id)


def wait_approval_task(approval_id: int, timeout: int = 900) -> bool | None:
    """Celery task: wait for approval decision."""
    return wait_for_approval_sync(approval_id, timeout)


def crisis_broadcast_task(message: str) -> int:
    """Celery task: broadcast crisis alert."""
    return crisis_broadcast_sync(message)


def notify_trade_task(chat_id: int, trade_data: dict) -> None:
    """Celery task: notify trade execution."""
    notify_trade_sync(chat_id, trade_data)