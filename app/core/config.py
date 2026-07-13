from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_ticker: str = "E1VFVN30.VN"
    database_url: str = "sqlite:///./simple_finance.db"

    market_data_provider: str = "yfinance"
    vnstock_api_key: str = ""
    market_data_base_url: str = "https://api.example.com"
    market_data_ohlcv_path: str = "/v1/ohlcv/{ticker}"
    market_data_api_key: str = ""
    market_data_start_param: str = "start"
    market_data_end_param: str = "end"

    market_summary_symbols: str = "E1VFVN30.VN,FUEVFVND.VN,^VNINDEX.VN"

    annual_rf_rate: float = 0.05
    default_initial_cash: float = 10_000_000
    default_monthly_cash: float = 1_000_000
    default_fee_rate: float = 0.0015

    app_name: str = Field(default="Simple Finance")

    @property
    def market_summary_symbol_list(self) -> list[str]:
        return [s.strip() for s in self.market_summary_symbols.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
