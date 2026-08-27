# SYNCHRO MQL5 Bridge Protocol (File-Based Polling)

## Overview
External bridge architecture: **MQL5 EA** ←→ **File System** ←→ **Python Bridge** ←→ **Cloud (mTLS)**

No DLL injection. No direct network calls from EA. All communication via files in a secured directory.

---

## Directory Structure
```
C:\SynchroBridge\
├── commands\           # Cloud → EA (bridge writes, EA reads)
│   ├── pending\        # New commands awaiting pickup
│   ├── processing\     # EA has picked up, executing
│   └── completed\      # EA finished, bridge collects result
├── responses\          # EA → Cloud (EA writes, bridge reads)
│   ├── pending\        # New results awaiting pickup
│   ├── processing\     # Bridge picked up, forwarding to cloud
│   └── completed\      # Cloud acknowledged
├── heartbeat\          # EA writes timestamp every 5s
│   └── ea_heartbeat.json
├── state\              # EA persistent state
│   └── ea_state.json
└── config\             # Bridge writes, EA reads on startup
    └── bridge_config.json
```

---

## File Formats

### 1. Command File (commands/pending/{command_id}.json)
```json
{
  "command_id": "cmd_20240115_001",
  "type": "OPEN|MODIFY|CLOSE|PARTIAL_CLOSE|BREAKEVEN|TRAILING|HEARTBEAT|SHUTDOWN",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {
    "symbol": "R_75",
    "direction": "BUY|SELL",
    "volume": 0.10,
    "sl": 18450.00,
    "tp": 18550.00,
    "comment": "SYNCHRO_5_5",
    "magic": 123456,
    "ticket": 123456789,
    "sl_new": 18470.00,
    "tp_new": 18560.00,
    "volume_partial": 0.05
  },
  "hmac": "sha256_hex_of(payload + secret)",
  "nonce": "uuid_v4"
}
```

### 2. Response File (responses/pending/{command_id}.json)
```json
{
  "command_id": "cmd_20240115_001",
  "status": "SUCCESS|ERROR|PARTIAL|REJECTED",
  "timestamp": "2024-01-15T10:30:05Z",
  "result": {
    "ticket": 123456789,
    "price": 18472.50,
    "volume": 0.10,
    "sl": 18450.00,
    "tp": 18550.00,
    "profit": 0.00,
    "swap": 0.00,
    "comment": "SYNCHRO_5_5"
  },
  "error_code": 0,
  "error_message": "",
  "hmac": "sha256_hex_of(result + secret)",
  "nonce": "uuid_v4"
}
```

### 3. Heartbeat File (heartbeat/ea_heartbeat.json) — Written every 5s by EA
```json
{
  "ea_version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "account": 12345678,
  "balance": 10000.00,
  "equity": 10025.50,
  "margin_free": 9500.00,
  "open_positions": 2,
  "cloud_connected": true,
  "last_command_processed": "cmd_20240115_001",
  "protective_mode": false
}
```

### 4. EA State File (state/ea_state.json) — Persistent
```json
{
  "magic": 123456,
  "account": 12345678,
  "symbol": "R_75",
  "open_positions": [
    {
      "ticket": 123456789,
      "symbol": "R_75",
      "type": "BUY",
      "volume": 0.10,
      "open_price": 18472.50,
      "sl": 18450.00,
      "tp": 18550.00,
      "breakeven_triggered": false,
      "trailing_active": false,
      "partial_closed": false
    }
  ],
  "last_command_id": "cmd_20240115_001",
  "protective_mode": false,
  "last_heartbeat": "2024-01-15T10:30:00Z"
}
```

### 5. Bridge Config (config/bridge_config.json) — Written by bridge on startup
```json
{
  "bridge_version": "1.0.0",
  "cloud_endpoint": "wss://api.synchro.trade/bridge/ws",
  "poll_interval_ms": 500,
  "command_timeout_ms": 30000,
  "heartbeat_interval_ms": 5000,
  "cloud_timeout_ms": 60000,
  "protective_mode_after_ms": 60000,
  "hmac_key_id": "synchro_hmac_v1",
  "allowed_symbols": ["R_75", "R_100", "frxEURUSD", "frxGBPUSD", "frxUSDJPY"],
  "max_positions": 5,
  "max_volume_per_symbol": 1.0,
  "default_sl_pips": 200,
  "default_tp_pips": 300,
  "breakeven_pips": 100,
  "trailing_pips": 50,
  "partial_close_ratio": 0.5
}
```

---

## HMAC Signing

**Key**: 32-byte secret from AWS Secrets Manager (`synchro/bridge/hmac_key`)

**Algorithm**: HMAC-SHA256

**Signing**:
```python
def sign(payload: dict, secret: bytes) -> str:
    # Canonical JSON: sorted keys, no whitespace
    canonical = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    return hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest()
```

**Verification**: Cloud and Bridge both verify. EA verifies commands. Bridge verifies responses.

**Replay Protection**: `nonce` (UUID v4) + `timestamp` (reject if > 5 min old)

---

## Command Types

| Type | Direction | Payload Fields | Description |
|------|-----------|----------------|-------------|
| `OPEN` | Cloud→EA | symbol, direction, volume, sl, tp, comment, magic | Open new position |
| `MODIFY` | Cloud→EA | ticket, sl_new, tp_new | Modify SL/TP |
| `CLOSE` | Cloud→EA | ticket, volume (optional) | Close position (full or partial) |
| `PARTIAL_CLOSE` | Cloud→EA | ticket, volume | Close portion (default 50%) |
| `BREAKEVEN` | Cloud→EA | ticket | Move SL to entry + 10 pips |
| `TRAILING` | Cloud→EA | ticket | Activate trailing stop |
| `HEARTBEAT` | Cloud→EA | — | Keep-alive |
| `SHUTDOWN` | Cloud→EA | — | Emergency stop, close all |

---

## Response Status Codes

| Code | Status | Meaning |
|------|--------|---------|
| 0 | SUCCESS | Order executed |
| 1 | ERR_NO_ERROR | Success (MT5) |
| 2 | ERR_COMMON_ERROR | Generic failure |
| 3 | ERR_INVALID_TRADE_PARAMETERS | Bad params |
| 4 | ERR_SERVER_BUSY | Retry |
| 5 | ERR_OLD_VERSION | Reconnect |
| 6 | ERR_NO_CONNECTION | No net |
| 7 | ERR_NOT_ENOUGH_RIGHTS | Permissions |
| 8 | ERR_TOO_FREQUENT_REQUESTS | Rate limit |
| 9 | ERR_MALFUNCTION | Terminal error |
| 10001 | ERR_BRIDGE_TIMEOUT | Bridge didn't respond |
| 10002 | ERR_HMAC_INVALID | Signature failed |
| 10003 | ERR_NONCE_REPLAY | Replay detected |
| 10004 | ERR_PROTECTIVE_MODE | EA in protective mode |
| 10005 | ERR_INVALID_SYMBOL | Not in allowed list |
| 10006 | ERR_VOLUME_EXCEEDED | Max volume reached |

---

## Protective Mode Logic

```
Cloud heartbeat missing > 60s:
  1. EA sets protective_mode = true
  2. EA closes ALL open positions at market
  3. EA rejects ALL new OPEN commands
  4. EA only accepts CLOSE/PARTIAL_CLOSE
  5. EA continues heartbeats with protective_mode: true
  6. When cloud reconnects (heartbeat received):
     - EA sends current state to cloud
     - Cloud sends RECOVER command
     - EA resets protective_mode = false
```

---

## File Polling Logic (EA)

```mql5
// OnTimer() - runs every 500ms
void OnTimer() {
  // 1. Check heartbeat timeout
  if (GetTickCount64() - lastCloudHeartbeat > CLOUD_TIMEOUT_MS) {
    EnterProtectiveMode();
  }
  
  // 2. Poll commands/pending/
  ProcessPendingCommands();
  
  // 3. Write heartbeat
  WriteHeartbeat();
  
  // 4. Manage position lifecycle (breakeven, trailing)
  ManagePositions();
}

// ProcessPendingCommands()
void ProcessPendingCommands() {
  string files[] = GetFiles("commands/pending/*.json");
  for (string file : files) {
    Command cmd = ParseCommand(file);
    if (!VerifyHMAC(cmd)) { MoveToCompleted(file, ERR_HMAC_INVALID); continue; }
    if (IsReplay(cmd.nonce)) { MoveToCompleted(file, ERR_NONCE_REPLAY); continue; }
    
    MoveToProcessing(file);
    Response resp = ExecuteCommand(cmd);
    WriteResponse(resp);
    MoveToCompleted(file);
    RecordNonce(cmd.nonce);
  }
}
```

---

## Security Requirements

1. **Directory Permissions**: Only `SYSTEM` and `BridgeUser` have write access
2. **File Locking**: Use `LockFileEx` / `flock` for atomic moves
3. **No Plaintext Secrets**: HMAC key only in AWS Secrets Manager, injected at bridge startup
3. **Audit Log**: Every command/response logged to cloud (immutable)
4. **EA Binary**: Signed with code-signing certificate
5. **Bridge Binary**: Signed, runs as restricted Windows service