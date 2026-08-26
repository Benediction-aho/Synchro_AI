"""Telegram Bot service — Doc 4 item 19.

Features:
- Approval cards with YES/NO inline buttons (15-min timeout → auto-decline)
- CRISIS broadcast to all users
- Mobile kill-switch (stop all trading)
"""

import asyncio
from datetime import datetime
from typing import Any

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.orm import Session

from synchro.core.config import get_settings
from synchro.db.models.user import Account, User
from synchro.db.session import SessionLocal

settings = get_settings()

# Lazy initialization
_bot: Bot | None = None
_dp: Dispatcher | None = None
_router: Router | None = None


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")
        _bot = Bot(token=settings.telegram_bot_token, parse_mode=ParseMode.HTML)
    return _bot


def _get_dp() -> Dispatcher:
    global _dp, _router
    if _dp is None:
        _dp = Dispatcher(storage=MemoryStorage())
        _router = Router()
        _dp.include_router(_router)
    return _dp


def get_router() -> Router:
    return _get_dp()


# In-memory pending approvals (in production: Redis)
_pending_approvals: dict[int, dict] = {}
_approval_timeouts: dict[int, asyncio.Task] = {}

# Kill switch state
_kill_switch_active = False


class ApprovalStates(StatesGroup):
    waiting = State()


def _approval_keyboard(approval_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ YES", callback_data=f"approve_{approval_id}"),
            InlineKeyboardButton(text="❌ NO", callback_data=f"decline_{approval_id}"),
        ]
    ])


async def _auto_decline(approval_id: int, chat_id: int):
    """Auto-decline after 15 minutes."""
    await asyncio.sleep(900)  # 15 minutes
    if approval_id in _pending_approvals:
        del _pending_approvals[approval_id]
        try:
            await _get_bot().send_message(chat_id, f"⏰ Approval #{approval_id} timed out — auto-declined.")
        except Exception:
            pass


@get_router().message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 <b>SYNCHRO Trading Bot</b>\n\n"
        "Commands:\n"
        "/status — Account status\n"
        "/kill — Emergency kill switch\n"
        "/help — This message",
    )


@get_router().message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)


@get_router().message(Command("status"))
async def cmd_status(message: types.Message):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_chat_id == str(message.chat.id)).first()
        if not user:
            await message.answer("❌ Not linked. Contact admin to link your Telegram.")
            return
        accounts = db.query(Account).filter(Account.user_id == user.id, Account.is_active == True).all()
        if not accounts:
            await message.answer("📭 No active accounts.")
            return
        lines = ["📊 <b>Account Status</b>"]
        for acc in accounts:
            lines.append(f"• {acc.name} (ID: {acc.id}) — {'🟢 Active' if acc.is_active else '🔴 Inactive'}")
        if _kill_switch_active:
            lines.append("\n🛑 <b>KILL SWITCH ACTIVE</b> — All trading halted")
        await message.answer("\n".join(lines))
    finally:
        db.close()


@get_router().message(Command("kill"))
async def cmd_kill(message: types.Message):
    global _kill_switch_active
    _kill_switch_active = True
    await message.answer("🛑 <b>KILL SWITCH ACTIVATED</b>\nAll trading halted immediately.")


@get_router().callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: types.CallbackQuery):
    approval_id = int(callback.data.split("_")[1])
    if approval_id not in _pending_approvals:
        await callback.answer("❌ Expired or invalid")
        return

    approval = _pending_approvals.pop(approval_id)
    if approval_id in _approval_timeouts:
        _approval_timeouts[approval_id].cancel()
        del _approval_timeouts[approval_id]

    approval["approved"] = True
    approval["decided_at"] = datetime.utcnow()
    await callback.message.edit_text(
        f"{callback.message.html_text}\n\n✅ <b>APPROVED</b> by {callback.from_user.full_name}",
        reply_markup=None,
    )
    await callback.answer("✅ Approved")


@get_router().callback_query(F.data.startswith("decline_"))
async def cb_decline(callback: types.CallbackQuery):
    approval_id = int(callback.data.split("_")[1])
    if approval_id not in _pending_approvals:
        await callback.answer("❌ Expired or invalid")
        return

    approval = _pending_approvals.pop(approval_id)
    if approval_id in _approval_timeouts:
        _approval_timeouts[approval_id].cancel()
        del _approval_timeouts[approval_id]

    approval["approved"] = False
    approval["decided_at"] = datetime.utcnow()
    await callback.message.edit_text(
        f"{callback.message.html_text}\n\n❌ <b>DECLINED</b> by {callback.from_user.full_name}",
        reply_markup=None,
    )
    await callback.answer("❌ Declined")


async def send_approval_card(
    chat_id: int,
    title: str,
    details: dict,
    approval_id: int,
) -> dict:
    """Send an approval card with YES/NO buttons and 15-min timeout."""
    lines = [f"📋 <b>{title}</b>"]
    for k, v in details.items():
        lines.append(f"  • {k}: {v}")
    lines.append("\n⏳ Expires in 15 minutes — auto-declines if no action")

    msg = await _get_bot().send_message(
        chat_id,
        "\n".join(lines),
        reply_markup=_approval_keyboard(approval_id),
    )

    approval = {
        "id": approval_id,
        "chat_id": chat_id,
        "message_id": msg.message_id,
        "title": title,
        "details": details,
        "created_at": datetime.utcnow(),
        "approved": None,
    }
    _pending_approvals[approval_id] = approval
    _approval_timeouts[approval_id] = asyncio.create_task(_auto_decline(approval_id, chat_id))
    return approval


async def wait_for_approval(approval_id: int, timeout: int = 900) -> bool | None:
    """Wait for approval decision. Returns True/False/None (timeout)."""
    start = datetime.utcnow()
    while approval_id in _pending_approvals:
        if (datetime.utcnow() - start).total_seconds() > timeout:
            return None
        await asyncio.sleep(1)
    approval = _pending_approvals.get(approval_id)
    return approval["approved"] if approval else None


async def crisis_broadcast(message: str) -> int:
    """Send CRISIS alert to all linked users."""
    db: Session = SessionLocal()
    sent = 0
    try:
        users = db.query(User).filter(User.telegram_chat_id.isnot(None), User.is_active == True).all()
        bot = _get_bot()
        for user in users:
            try:
                await bot.send_message(user.telegram_chat_id, f"🚨 <b>CRISIS ALERT</b>\n\n{message}")
                sent += 1
            except Exception:
                pass
        return sent
    finally:
        db.close()


async def notify_trade(chat_id: int, trade_data: dict) -> None:
    """Send trade execution notification."""
    lines = [
        "📈 <b>Trade Executed</b>",
        f"  Symbol: {trade_data.get('symbol')}",
        f"  Direction: {trade_data.get('direction')}",
        f"  Entry: {trade_data.get('entry_price')}",
        f"  SL: {trade_data.get('sl')}",
        f"  TP: {trade_data.get('tp')}",
        f"  Size: {trade_data.get('lots')} lots",
    ]
    await _get_bot().send_message(chat_id, "\n".join(lines))


async def start_polling():
    """Start the bot polling loop."""
    await _get_dp().start_polling(_get_bot())


async def stop_polling():
    """Stop the bot."""
    if _bot:
        await _bot.session.close()


# Sync wrappers for Celery tasks
def send_approval_card_sync(
    chat_id: int,
    title: str,
    details: dict,
    approval_id: int,
) -> dict:
    """Sync wrapper for Celery."""
    return asyncio.run(send_approval_card(chat_id, title, details, approval_id))


def wait_for_approval_sync(approval_id: int, timeout: int = 900) -> bool | None:
    return asyncio.run(wait_for_approval(approval_id, timeout))


def crisis_broadcast_sync(message: str) -> int:
    return asyncio.run(crisis_broadcast(message))


def notify_trade_sync(chat_id: int, trade_data: dict) -> None:
    asyncio.run(notify_trade(chat_id, trade_data))