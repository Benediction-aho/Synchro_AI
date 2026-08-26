import logging

import pytest

from synchro.core.logging_config import SecretScrubbingFormatter
from synchro.domain.market_symbols import (
    SymbolNotAllowed,
    is_allowed_symbol,
    validate_symbol,
    validate_symbol_list,
)


def make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_scrubber_redacts_bearer_tokens():
    formatter = SecretScrubbingFormatter("%(message)s")
    out = formatter.format(make_record("auth header: Bearer eyJhbGciOiJIUzI1NiJ9.xxx.yyy"))
    assert "eyJhbGciOiJIUzI1NiJ9" not in out
    assert "Bearer [REDACTED]" in out


def test_scrubber_redacts_pat_tokens():
    formatter = SecretScrubbingFormatter("%(message)s")
    out = formatter.format(make_record("using token pat_FAKE00example000000000000"))
    assert "pat_FAKE00example000000000000" not in out
    assert "pat_[REDACTED]" in out


def test_scrubber_leaves_normal_logs():
    formatter = SecretScrubbingFormatter("%(message)s")
    text = "ingested so far: {'R_75': 12}"
    assert formatter.format(make_record(text)) == text


def test_validate_symbol_accepts_known():
    assert validate_symbol("R_75") == "R_75"
    assert validate_symbol("frxEURUSD") == "frxEURUSD"


def test_validate_symbol_rejects_unknown():
    with pytest.raises(SymbolNotAllowed):
        validate_symbol("WEIRD_COIN")
    with pytest.raises(SymbolNotAllowed):
        validate_symbol("R_75; DROP TABLE users")


def test_validate_list_and_helper():
    assert validate_symbol_list(["R_75", "1HZ100V"]) == ["R_75", "1HZ100V"]
    assert is_allowed_symbol("R_10")
    assert not is_allowed_symbol("")
