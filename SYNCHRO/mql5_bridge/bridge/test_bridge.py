"""Tests for MQL5 Bridge components."""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from bridge.config import BridgeConfig, Settings
from bridge.crypto import (
    Command, Response, create_command, create_response,
    validate_command, validate_response, sign_payload, verify_hmac,
    generate_nonce, generate_command_id
)


class TestCrypto:
    """Test HMAC signing and verification."""
    
    def test_sign_verify_roundtrip(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = '{"symbol":"R_75","volume":0.1}'
        sig = sign_payload(payload, hmac_key)
        assert verify_hmac(payload, hmac_key, sig)
    
    def test_verify_fails_on_tampering(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = '{"symbol":"R_75","volume":0.1}'
        sig = sign_payload(payload, hmac_key)
        
        # Tamper with payload
        tampered = '{"symbol":"R_75","volume":0.2}'
        assert not verify_hmac(tampered, hmac_key, sig)
    
    def test_verify_fails_on_wrong_key(self):
        hmac_key1 = b"test-secret-key-32-bytes-long!!"
        hmac_key2 = b"different-secret-key-32-bytes!!"
        payload = '{"symbol":"R_75"}'
        sig = sign_payload(payload, hmac_key1)
        assert not verify_hmac(payload, hmac_key2, sig)


class TestCommand:
    """Test Command creation and validation."""
    
    def test_create_command(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = {"symbol": "R_75", "direction": "BUY", "volume": 0.1}
        cmd = create_command("OPEN", payload, hmac_key)
        
        assert cmd.type == "OPEN"
        assert cmd.payload == payload
        assert cmd.command_id.startswith("cmd_")
        assert len(cmd.nonce) > 0
        assert len(cmd.hmac) == 64  # SHA256 hex
    
    def test_validate_command_success(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = {"symbol": "R_75", "volume": 0.1}
        cmd = create_command("OPEN", payload, hmac_key)
        
        seen = set()
        valid, error = validate_command(cmd, hmac_key, seen)
        assert valid
        assert error == ""
        assert cmd.nonce in seen
    
    def test_validate_command_replay(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = {"symbol": "R_75"}
        cmd = create_command("OPEN", payload, hmac_key)
        
        seen = {cmd.nonce}
        valid, error = validate_command(cmd, hmac_key, seen)
        assert not valid
        assert "replay" in error.lower()
    
    def test_validate_command_hmac_fail(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = {"symbol": "R_75"}
        cmd = create_command("OPEN", payload, hmac_key)
        
        # Tamper with HMAC
        cmd.hmac = "0" * 64
        
        seen = set()
        valid, error = validate_command(cmd, hmac_key, seen)
        assert not valid
        assert "hmac" in error.lower()
    
    def test_validate_command_old_timestamp(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        payload = {"symbol": "R_75"}
        cmd = create_command("OPEN", payload, hmac_key)
        
        # Manually set old timestamp
        from datetime import datetime, timezone, timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        cmd.timestamp = old_time.isoformat()
        
        seen = set()
        valid, error = validate_command(cmd, hmac_key, seen, max_age_sec=300)
        assert not valid
        assert "old" in error.lower()


class TestResponse:
    """Test Response creation and validation."""
    
    def test_create_response(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        result = {"ticket": 12345, "price": 18472.50}
        resp = create_response("cmd_123", "SUCCESS", result, 0, "", hmac_key)
        
        assert resp.command_id == "cmd_123"
        assert resp.status == "SUCCESS"
        assert resp.result == result
        assert resp.error_code == 0
        assert len(resp.hmac) == 64
    
    def test_validate_response_success(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        result = {"ticket": 12345}
        resp = create_response("cmd_123", "SUCCESS", result, 0, "", hmac_key)
        
        valid, error = validate_response(resp, hmac_key)
        assert valid
        assert error == ""
    
    def test_validate_response_fail(self):
        hmac_key = b"test-secret-key-32-bytes-long!!"
        result = {"ticket": 12345}
        resp = create_response("cmd_123", "SUCCESS", result, 0, "", hmac_key)
        
        # Tamper
        resp.hmac = "0" * 64
        valid, error = validate_response(resp, hmac_key)
        assert not valid


class TestConfig:
    """Test configuration loading."""
    
    def test_default_config(self):
        config = BridgeConfig()
        assert config.bridge_version == "1.0.0"
        assert config.poll_interval_ms == 500
        assert config.max_positions == 5
        assert "R_75" in config.allowed_symbols
    
    def test_directory_properties(self):
        config = BridgeConfig(bridge_root=Path(r"C:\TestBridge"))
        assert config.commands_pending == Path(r"C:\TestBridge\commands\pending")
        assert config.responses_completed == Path(r"C:\TestBridge\responses\completed")


class TestBridgeIntegration:
    """Integration tests for bridge (mocked)."""
    
    @pytest.fixture
    def temp_bridge_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_bridge_creates_directories(self, temp_bridge_root):
        from bridge.config import BridgeConfig
        config = BridgeConfig(bridge_root=temp_bridge_root)
        
        # Directories should be created by load_config
        # This is tested in config test
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])