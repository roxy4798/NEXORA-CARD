"""Application configuration management using Pydantic Settings."""

from decimal import Decimal
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_connect_timeout: float = Field(default=30.0, alias="TELEGRAM_CONNECT_TIMEOUT")
    telegram_read_timeout: float = Field(default=30.0, alias="TELEGRAM_READ_TIMEOUT")
    telegram_write_timeout: float = Field(default=30.0, alias="TELEGRAM_WRITE_TIMEOUT")
    telegram_proxy_url: str = Field(default="", alias="TELEGRAM_PROXY_URL")

    # Binance Market Data
    binance_base_url: str = Field(default="https://fapi.binance.com", alias="BINANCE_BASE_URL")
    binance_ws_url: str = Field(default="wss://fstream.binance.com/ws", alias="BINANCE_WS_URL")

    # Simulation Defaults
    default_max_leverage: int = Field(default=125, alias="DEFAULT_MAX_LEVERAGE")
    default_mode: Literal["MOCK", "LIVE"] = Field(default="MOCK", alias="DEFAULT_MODE")

    # Image Card Dimensions
    image_width: int = Field(default=1080, alias="IMAGE_WIDTH")
    image_height: int = Field(default=650, alias="IMAGE_HEIGHT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
