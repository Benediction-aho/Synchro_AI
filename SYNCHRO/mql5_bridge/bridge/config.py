"""Bridge configuration with AWS Secrets Manager integration."""

import os
import json
import boto3
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeConfig(BaseModel):
    """Runtime configuration loaded from AWS Secrets Manager + local file."""
    
    bridge_version: str = "1.0.0"
    cloud_endpoint: str = "wss://api.synchro.trade/bridge/ws"
    poll_interval_ms: int = 500
    command_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 5000
    cloud_timeout_ms: int = 60000
    protective_mode_after_ms: int = 60000
    hmac_key_id: str = "synchro_hmac_v1"
    allowed_symbols: list[str] = [
        "R_75", "R_100", "R_50", "R_25", "R_10",
        "frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD", "frxUSDCAD"
    ]
    max_positions: int = 5
    max_volume_per_symbol: float = 1.0
    default_sl_pips: int = 200
    default_tp_pips: int = 300
    breakeven_pips: int = 100
    trailing_pips: int = 50
    partial_close_ratio: float = 0.5
    
    # Bridge file paths
    bridge_root: Path = Path(r"C:\SynchroBridge")
    
    @property
    def commands_pending(self) -> Path:
        return self.bridge_root / "commands" / "pending"
    
    @property
    def commands_processing(self) -> Path:
        return self.bridge_root / "commands" / "processing"
    
    @property
    def commands_completed(self) -> Path:
        return self.bridge_root / "commands" / "completed"
    
    @property
    def responses_pending(self) -> Path:
        return self.bridge_root / "responses" / "pending"
    
    @property
    def responses_processing(self) -> Path:
        return self.bridge_root / "responses" / "processing"
    
    @property
    def responses_completed(self) -> Path:
        return self.bridge_root / "responses" / "completed"
    
    @property
    def heartbeat_dir(self) -> Path:
        return self.bridge_root / "heartbeat"
    
    @property
    def state_dir(self) -> Path:
        return self.bridge_root / "state"
    
    @property
    def config_dir(self) -> Path:
        return self.bridge_root / "config"
    
    @property
    def hmac_key(self) -> bytes:
        """Load HMAC key from AWS Secrets Manager."""
        return self._get_hmac_key()
    
    def _get_hmac_key(self) -> bytes:
        """Fetch HMAC key from AWS Secrets Manager."""
        secret_name = os.getenv("HMAC_SECRET_NAME", "synchro/bridge/hmac_key")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        try:
            client = boto3.client("secretsmanager", region_name=region)
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response["SecretString"])
            return secret["hmac_key"].encode()
        except Exception as e:
            # Fallback for local development
            if os.getenv("ENVIRONMENT") == "local":
                fallback = os.getenv("HMAC_KEY_FALLBACK", "local-dev-hmac-key-32-bytes-long!!")
                return fallback.encode()
            raise RuntimeError(f"Failed to load HMAC key from AWS Secrets Manager: {e}")


class Settings(BaseSettings):
    """Application settings from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    environment: str = "local"
    aws_region: str = "us-east-1"
    hm_secret_name: str = "synchro/bridge/hmac_key"
    log_level: str = "INFO"
    
    # Bridge directories
    bridge_root: str = r"C:\SynchroBridge"
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None


def load_config() -> BridgeConfig:
    """Load bridge configuration from AWS Secrets Manager + local overrides."""
    settings = Settings()
    
    # Create directory structure
    root = Path(settings.bridge_root)
    for subdir in ["commands/pending", "commands/processing", "commands/completed",
                   "responses/pending", "responses/processing", "responses/completed",
                   "heartbeat", "state", "config"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    
    # Set restrictive permissions on Windows
    if os.name == "nt":
        import subprocess
        try:
            # Restrict to SYSTEM and Administrators only
            subprocess.run([
                "icacls", str(root), "/inheritance:r", 
                "/grant:r", "SYSTEM:(OI)(CI)F", 
                "/grant:r", "Administrators:(OI)(CI)F"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass  # Non-fatal
    
    return BridgeConfig()