from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portfolix"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(default="portfolix-super-secret-production-grade-key-2026", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{BASE_DIR}/portfolix.db",
        env="DATABASE_URL"
    )
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "*"
    ]
    
    # Trading Engine Defaults
    DEFAULT_COMMISSION_RATE: float = 0.001  # 0.1%
    DEFAULT_SLIPPAGE_RATE: float = 0.0005   # 0.05%
    DEFAULT_INITIAL_CASH: float = 1000000.0 # INR 1,000,000
    
    # Data paths
    DATA_FILE_PATH: str = str(BASE_DIR / "data" / "processed" / "cleaned_stock_data.csv")
    RAW_DATA_FILE_PATH: str = str(BASE_DIR / "data" / "stock_data.csv")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings()
