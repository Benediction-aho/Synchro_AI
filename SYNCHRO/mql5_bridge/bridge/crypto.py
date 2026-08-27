"""HMAC signing and verification for bridge protocol."""

import hmac
import hashlib
import json
import uuid
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class Command:
    """Bridge command from cloud to EA."""
    command_id: str
    type: str  # OPEN, MODIFY, CLOSE, PARTIAL_CLOSE, BREAKEVEN, TRAILING, HEARTBEAT, SHUTDOWN
    timestamp: str
    payload: Dict[str, Any]
    hmac: str
    nonce: str
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'), sort_keys=True)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Command':
        data = json.loads(json_str)
        return cls(**data)
    
    def canonical_payload(self) -> str:
        """Canonical JSON for HMAC signing (sorted keys, no whitespace)."""
        return json.dumps(self.payload, separators=(',', ':'), sort_keys=True)


@dataclass
class Response:
    """Bridge response from EA to cloud."""
    command_id: str
    status: str  # SUCCESS, ERROR, PARTIAL, REJECTED
    timestamp: str
    result: Dict[str, Any]
    error_code: int
    error_message: str
    hmac: str
    nonce: str
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'), sort_keys=True)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Response':
        data = json.loads(json_str)
        return cls(**data)
    
    def canonical_result(self) -> str:
        """Canonical JSON for HMAC signing."""
        return json.dumps(self.result, separators=(',', ':'), sort_keys=True)


def generate_nonce() -> str:
    """Generate unique nonce for replay protection."""
    return str(uuid.uuid4())


def generate_command_id() -> str:
    """Generate unique command ID with timestamp."""
    return f"cmd_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"


def sign_payload(payload: str, hmac_key: bytes) -> str:
    """Sign payload with HMAC-SHA256."""
    return hmac.new(hmac_key, payload.encode(), hashlib.sha256).hexdigest()


def verify_hmac(payload: str, hmac_key: bytes, expected_hmac: str) -> bool:
    """Verify HMAC signature."""
    computed = sign_payload(payload, hmac_key)
    return hmac.compare_digest(computed, expected_hmac)


def create_command(
    cmd_type: str,
    payload: Dict[str, Any],
    hmac_key: bytes
) -> Command:
    """Create a new signed command."""
    nonce = generate_nonce()
    cmd_id = generate_command_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Canonical payload for signing
    canonical = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    hmac_sig = sign_payload(canonical, hmac_key)
    
    return Command(
        command_id=cmd_id,
        type=cmd_type,
        timestamp=timestamp,
        payload=payload,
        hmac=hmac_sig,
        nonce=nonce
    )


def create_response(
    command_id: str,
    status: str,
    result: Dict[str, Any],
    error_code: int,
    error_message: str,
    hmac_key: bytes
) -> Response:
    """Create a new signed response."""
    nonce = generate_nonce()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    canonical = json.dumps(result, separators=(',', ':'), sort_keys=True)
    hmac_sig = sign_payload(canonical, hmac_key)
    
    return Response(
        command_id=command_id,
        status=status,
        timestamp=timestamp,
        result=result,
        error_code=error_code,
        error_message=error_message,
        hmac=hmac_sig,
        nonce=nonce
    )


def validate_command(cmd: Command, hmac_key: bytes, seen_nonces: set, max_age_sec: int = 300) -> tuple[bool, str]:
    """
    Validate command: HMAC, nonce replay, timestamp age.
    Returns (is_valid, error_message).
    """
    # Check timestamp age
    try:
        cmd_time = datetime.fromisoformat(cmd.timestamp.replace('Z', '+00:00'))
        age = (datetime.now(timezone.utc) - cmd_time).total_seconds()
        if age > max_age_sec:
            return False, f"Command too old: {age}s > {max_age_sec}s"
    except ValueError:
        return False, "Invalid timestamp format"
    
    # Check nonce replay
    if cmd.nonce in seen_nonces:
        return False, f"Nonce replay detected: {cmd.nonce}"
    
    # Verify HMAC
    canonical = cmd.canonical_payload()
    if not verify_hmac(canonical, hmac_key, cmd.hmac):
        return False, "HMAC verification failed"
    
    return True, ""


def validate_response(resp: Response, hmac_key: bytes) -> tuple[bool, str]:
    """Validate response HMAC."""
    canonical = resp.canonical_result()
    if not verify_hmac(canonical, hmac_key, resp.hmac):
        return False, "Response HMAC verification failed"
    return True, ""