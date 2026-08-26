"""Tests for Telegram bot."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from synchro.services.telegram_bot.bot import (
    _pending_approvals,
    _approval_timeouts,
    _kill_switch_active,
    _approval_keyboard,
    send_approval_card,
    wait_for_approval,
    crisis_broadcast,
    _get_bot,
)


class TestApprovalKeyboard:
    def test_keyboard_has_yes_no(self):
        kb = _approval_keyboard(123)
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].text == "✅ YES"
        assert buttons[0].callback_data == "approve_123"
        assert buttons[1].text == "❌ NO"
        assert buttons[1].callback_data == "decline_123"


class TestKillSwitch:
    def test_kill_switch_state(self):
        import synchro.services.telegram_bot.bot as bot_module
        # Reset
        bot_module._kill_switch_active = False
        assert not bot_module._kill_switch_active
        bot_module._kill_switch_active = True
        assert bot_module._kill_switch_active
        bot_module._kill_switch_active = False


class MockBot:
    def __init__(self):
        self.sent_messages = []
        self.edited_messages = []

    async def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self.sent_messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        msg = MagicMock()
        msg.message_id = len(self.sent_messages)
        return msg

    async def edit_message_text(self, text, chat_id, message_id, reply_markup=None, **kwargs):
        self.edited_messages.append({"chat_id": chat_id, "message_id": message_id, "text": text})


class MockMessage:
    def __init__(self, message_id=1):
        self.message_id = message_id
        self.html_text = "Test message"
        self.chat = MagicMock()
        self.chat.id = 12345
        self.from_user = MagicMock()
        self.from_user.full_name = "Test User"


class TestApprovalFlow:
    @pytest.mark.asyncio
    async def test_send_approval_creates_entry(self):
        _pending_approvals.clear()
        _approval_timeouts.clear()

        mock_bot = MockBot()
        with patch("synchro.services.telegram_bot.bot._get_bot", return_value=mock_bot):
            approval = await send_approval_card(
                chat_id=12345,
                title="Test Approval",
                details={"param": "value"},
                approval_id=999,
            )

        assert approval["id"] == 999
        assert approval["chat_id"] == 12345
        assert approval["title"] == "Test Approval"
        assert approval["approved"] is None
        assert 999 in _pending_approvals
        assert 999 in _approval_timeouts
        assert len(mock_bot.sent_messages) == 1
        assert "Test Approval" in mock_bot.sent_messages[0]["text"]

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self):
        _pending_approvals.clear()
        _approval_timeouts.clear()

        mock_bot = MockBot()
        with patch("synchro.services.telegram_bot.bot._get_bot", return_value=mock_bot):
            await send_approval_card(
                chat_id=12345,
                title="Test",
                details={},
                approval_id=888,
            )

        # Don't resolve - wait for timeout (0 seconds for test)
        result = await wait_for_approval(888, timeout=0)
        assert result is None  # timeout returns None

        # Cleanup
        _pending_approvals.pop(888, None)
        if 888 in _approval_timeouts:
            _approval_timeouts[888].cancel()


class TestCrisisBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_structure(self):
        mock_bot = MockBot()
        mock_user = MagicMock()
        mock_user.telegram_chat_id = "12345"
        mock_user.is_active = True

        with patch("synchro.services.telegram_bot.bot._get_bot", return_value=mock_bot):
            with patch("synchro.services.telegram_bot.bot.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.all.return_value = [mock_user]

                result = await crisis_broadcast("Test crisis")

        assert isinstance(result, int)
        assert result == 1
        assert len(mock_bot.sent_messages) == 1
        assert "CRISIS ALERT" in mock_bot.sent_messages[0]["text"]