import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("BBMP_FW_Report.Config")

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    logger.info(f"Loaded configuration from {env_path}")
else:
    logger.warning(".env file not found, using system environment variables.")


class Config:
    # ThingsBoard Configuration (Loaded strictly from .env)
    TB_HOST = os.getenv("THINGSBOARD_HOST", "").rstrip("/")
    TB_USERNAME = os.getenv("THINGSBOARD_USERNAME", "").strip()
    TB_PASSWORD = os.getenv("THINGSBOARD_PASSWORD", "").strip()
    BBMP_CUSTOMER_ID = os.getenv("BBMP_CUSTOMER_ID", "").strip()
    TARGET_FW_VERSION = os.getenv("TARGET_FW_VERSION", "SL530.55").strip()

    # SMTP Email Configuration (Loaded strictly from .env)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip() or SMTP_USERNAME
    
    # Recipient & BCC Email List (Loaded strictly from .env)
    _recipients_str = os.getenv("RECIPIENT_EMAILS", "")
    RECIPIENT_EMAILS = [r.strip() for r in _recipients_str.split(",") if r.strip()]

    _bcc_str = os.getenv("BCC_EMAILS", "")
    BCC_EMAILS = [r.strip() for r in _bcc_str.split(",") if r.strip()]

    EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[BBMP Panels - Firmware Version Status Report]").strip()
