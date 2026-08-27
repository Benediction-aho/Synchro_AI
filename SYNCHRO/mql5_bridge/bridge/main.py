"""File-based polling bridge service."""

import asyncio
import json
import shutil
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Set
from datetime import datetime, timezone

from .config import load_config, BridgeConfig
from .crypto import (
    Command, Response, create_command, create_response,
    validate_command, validate_response
)

logger = logging.getLogger(__name__)


class FileBridge:
    """File-based polling bridge between EA and cloud."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.running = False
        self.seen_nonces: Set[str] = set()
        self.last_cloud_heartbeat: Optional[datetime] = None
        self.bridge_state = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "commands_processed": 0,
            "responses_sent": 0,
            "errors": 0
        }
    
    async def start(self):
        """Start the bridge polling loop."""
        self.running = True
        logger.info("Starting file bridge...")
        
        # Load existing nonces from state
        await self._load_state()
        
        # Write initial config for EA
        await self._write_bridge_config()
        
        # Start polling tasks
        tasks = [
            asyncio.create_task(self._poll_commands()),
            asyncio.create_task(self._poll_responses()),
            asyncio.create_task(self._write_heartbeat()),
            asyncio.create_task(self._monitor_cloud_connection()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Bridge tasks cancelled")
        finally:
            await self._save_state()
    
    async def stop(self):
        """Stop the bridge."""
        self.running = False
        logger.info("Stopping bridge...")
    
    async def _load_state(self):
        """Load bridge state from file."""
        state_file = self.config.state_dir / "bridge_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    self.seen_nonces = set(data.get("seen_nonces", []))
                    self.bridge_state = data.get("bridge_state", self.bridge_state)
                logger.info(f"Loaded {len(self.seen_nonces)} nonces from state")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
    
    async def _save_state(self):
        """Save bridge state to file."""
        state_file = self.config.state_dir / "bridge_state.json"
        try:
            data = {
                "seen_nonces": list(self.seen_nonces)[-10000:],  # Keep last 10k
                "bridge_state": self.bridge_state,
                "saved_at": datetime.now(timezone.utc).isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    async def _write_bridge_config(self):
        """Write bridge config for EA to read."""
        config_file = self.config.config_dir / "bridge_config.json"
        try:
            config_data = {
                "bridge_version": self.config.bridge_version,
                "poll_interval_ms": self.config.poll_interval_ms,
                "command_timeout_ms": self.config.command_timeout_ms,
                "heartbeat_interval_ms": self.config.heartbeat_interval_ms,
                "cloud_timeout_ms": self.config.cloud_timeout_ms,
                "protective_mode_after_ms": self.config.protective_mode_after_ms,
                "hmac_key_id": self.config.hmac_key_id,
                "allowed_symbols": self.config.allowed_symbols,
                "max_positions": self.config.max_positions,
                "max_volume_per_symbol": self.config.max_volume_per_symbol,
                "default_sl_pips": self.config.default_sl_pips,
                "default_tp_pips": self.config.default_tp_pips,
                "breakeven_pips": self.config.breakeven_pips,
                "trailing_pips": self.config.trailing_pips,
                "partial_close_ratio": self.config.partial_close_ratio,
            }
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write bridge config: {e}")
    
    async def _poll_commands(self):
        """Poll for new commands from cloud."""
        while self.running:
            try:
                await self._process_pending_commands()
            except Exception as e:
                logger.error(f"Error polling commands: {e}")
                self.bridge_state["errors"] += 1
            await asyncio.sleep(self.config.poll_interval_ms / 1000)
    
    async def _process_pending_commands(self):
        """Process all pending command files."""
        pending_dir = self.config.commands_pending
        if not pending_dir.exists():
            return
        
        for cmd_file in pending_dir.glob("*.json"):
            if not self.running:
                break
            
            try:
                await self._process_command_file(cmd_file)
            except Exception as e:
                logger.error(f"Error processing {cmd_file}: {e}")
                self.bridge_state["errors"] += 1
    
    async def _process_command_file(self, cmd_file: Path):
        """Process a single command file."""
        # Read command
        try:
            with open(cmd_file) as f:
                cmd_data = json.load(f)
            cmd = Command.from_json(json.dumps(cmd_data))
        except Exception as e:
            logger.error(f"Failed to parse command {cmd_file}: {e}")
            await self._move_to_completed(cmd_file, error_code=10000, error_msg="Parse error")
            return
        
        # Validate command
        is_valid, error = validate_command(cmd, self.config.hmac_key, self.seen_nonces)
        if not is_valid:
            logger.warning(f"Command validation failed: {error}")
            await self._move_to_completed(cmd_file, error_code=10002, error_msg=error)
            return
        
        # Mark nonce as seen
        self.seen_nonces.add(cmd.nonce)
        
        # Move to processing
        processing_file = self.config.commands_processing / cmd_file.name
        shutil.move(str(cmd_file), str(processing_file))
        
        # Execute command (forward to cloud via WebSocket)
        response = await self._execute_command(cmd)
        
        # Write response
        await self._write_response(response)
        
        # Move to completed
        await self._move_to_completed(processing_file)
        
        self.bridge_state["commands_processed"] += 1
    
    async def _execute_command(self, cmd: Command) -> Response:
        """Execute command by forwarding to cloud via WebSocket."""
        # This is where the bridge connects to cloud
        # For now, simulate with a mock response
        # Real implementation: connect to cloud WebSocket, send command, await response
        
        # Mock implementation - replace with actual cloud WebSocket call
        await asyncio.sleep(0.1)  # Simulate network latency
        
        if cmd.type == "HEARTBEAT":
            self.last_cloud_heartbeat = datetime.now(timezone.utc)
            return create_response(
                command_id=cmd.command_id,
                status="SUCCESS",
                result={"ack": True},
                error_code=0,
                error_message="",
                hmac_key=self.config.hmac_key
            )
        
        # For other commands, simulate success
        return create_response(
            command_id=cmd.command_id,
            status="SUCCESS",
            result={"ack": True, "command": cmd.type},
            error_code=0,
            error_message="",
            hmac_key=self.config.hmac_key
        )
    
    async def _write_response(self, response: Response):
        """Write response file for cloud to pick up."""
        resp_file = self.config.responses_pending / f"{response.command_id}.json"
        try:
            with open(resp_file, 'w') as f:
                json.dump(json.loads(response.to_json()), f)
        except Exception as e:
            logger.error(f"Failed to write response: {e}")
    
    async def _move_to_completed(self, file_path: Path, error_code: int = 0, error_msg: str = ""):
        """Move file to completed directory."""
        try:
            completed_dir = file_path.parent.parent / "completed"
            completed_dir.mkdir(exist_ok=True)
            dest = completed_dir / file_path.name
            if file_path.exists():
                shutil.move(str(file_path), str(dest))
        except Exception as e:
            logger.error(f"Failed to move {file_path} to completed: {e}")
    
    async def _poll_responses(self):
        """Poll for EA responses and forward to cloud."""
        while self.running:
            try:
                await self._process_pending_responses()
            except Exception as e:
                logger.error(f"Error polling responses: {e}")
            await asyncio.sleep(self.config.poll_interval_ms / 1000)
    
    async def _process_pending_responses(self):
        """Process EA responses and forward to cloud."""
        pending_dir = self.config.responses_pending
        if not pending_dir.exists():
            return
        
        for resp_file in pending_dir.glob("*.json"):
            if not self.running:
                break
            
            try:
                with open(resp_file) as f:
                    resp_data = json.load(f)
                resp = Response.from_json(json.dumps(resp_data))
                
                # Validate response HMAC
                is_valid, error = validate_response(resp, self.config.hmac_key)
                if not is_valid:
                    logger.warning(f"Response validation failed: {error}")
                    await self._move_to_completed(resp_file)
                    continue
                
                # Forward to cloud (WebSocket)
                await self._forward_response_to_cloud(resp)
                
                # Move to completed
                await self._move_to_completed(resp_file)
                self.bridge_state["responses_sent"] += 1
                
            except Exception as e:
                logger.error(f"Error processing response {resp_file}: {e}")
    
    async def _forward_response_to_cloud(self, response: Response):
        """Forward response to cloud via WebSocket."""
        # Real implementation: send over WebSocket to cloud
        # Mock for now
        await asyncio.sleep(0.05)
    
    async def _write_heartbeat(self):
        """Write bridge heartbeat for EA to monitor."""
        while self.running:
            try:
                heartbeat_file = self.config.heartbeat_dir / "bridge_heartbeat.json"
                data = {
                    "bridge_version": self.config.bridge_version,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "running",
                    "commands_processed": self.bridge_state["commands_processed"],
                    "responses_sent": self.bridge_state["responses_sent"],
                    "errors": self.bridge_state["errors"],
                    "cloud_connected": self.last_cloud_heartbeat is not None
                }
                with open(heartbeat_file, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                logger.error(f"Failed to write heartbeat: {e}")
            await asyncio.sleep(self.config.heartbeat_interval_ms / 1000)
    
    async def _monitor_cloud_connection(self):
        """Monitor cloud connection and trigger protective mode if needed."""
        while self.running:
            await asyncio.sleep(5)
            
            if self.last_cloud_heartbeat:
                elapsed = (datetime.now(timezone.utc) - self.last_cloud_heartbeat).total_seconds() * 1000
                if elapsed > self.config.protective_mode_after_ms:
                    logger.warning(f"Cloud connection lost for {elapsed}ms - protective mode should activate")
                    # EA should detect this via heartbeat timeout
                    # Bridge can write a flag file for EA
                    protective_file = self.config.state_dir / "protective_mode.flag"
                    protective_file.write_text("1")
            else:
                # No heartbeat yet - check if we should warn
                pass


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = load_config()
    bridge = FileBridge(config)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bridge.stop()))
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())