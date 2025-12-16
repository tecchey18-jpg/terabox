import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

load_dotenv()

@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x
    ])
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 30
    MAX_CONCURRENT_EXTRACTIONS: int = 10
    
    # Timeouts
    REQUEST_TIMEOUT: int = 60
    EXTRACTION_TIMEOUT: int = 120
    
    # Retries
    MAX_RETRIES: int = 5
    RETRY_DELAY: float = 2.0
    
    # Database
    DATABASE_PATH: str = "terabox_bot.db"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "bot.log"
    
    # Proxy (optional)
    PROXY_URL: Optional[str] = os.getenv("PROXY_URL")
    
    # Browser settings
    HEADLESS: bool = True
    USE_BROWSER_FALLBACK: bool = True


def setup_logging(config: Config):
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


config = Config()
logger = setup_logging(config)
