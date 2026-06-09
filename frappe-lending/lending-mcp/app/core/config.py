import logging
import os
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


def configure_logging():
    os.makedirs("./logs", exist_ok=True)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.handlers:
        return

    file_handler = TimedRotatingFileHandler(
        "./logs/lending-mcp-api.log",
        when="midnight",
        interval=1,
        backupCount=7,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    detailed_handler = TimedRotatingFileHandler(
        "./logs/detailed.lending-mcp-api.log",
        when="midnight",
        interval=1,
        backupCount=7,
    )
    detailed_handler.setFormatter(formatter)
    detailed_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(detailed_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


class Settings(BaseSettings):
    SERVICE_ID: str = "lending_mcp"
    APP_TITLE: str = "Lending MCP"
    ROOT_PATH: str = ""
    VERSION: str = "0.1.0"
    RELEASE_ID: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: str = "*"
    PERSONA_ID_HEADER: str = "Persona-Id"

    FRAPPE_API_URL: str = "http://backend:8000"
    FRAPPE_SITE_NAME: str = "frontend.localhost"
    FRAPPE_VERIFY_SSL: int = 0
    FRAPPE_API_KEY: str = ""
    FRAPPE_API_SECRET: str = ""
    FRAPPE_USERNAME: str = "Administrator"
    FRAPPE_PASSWORD: str = "admin"

    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    ACCOUNT_SERVICE_URL: str = ""
    ACCOUNT_SERVICE_JWKS_ENDPOINT: str = "/.well-known/jwks.json"
    ACCOUNT_SERVICE_JWKS_CACHE_TTL: int = 600

    USAGE_REPORT_ENDPOINT: str = "/api/v1/usage_reports"
    TRACK_USAGE: int = 0

    PLATFORM_INT_URL: str = ""
    PLATFORM_KEY_SERVICE_NAME: str = "Frappe"

    LICENSE_SERVER_BASE_URL: str = ""
    LICENSE_SERVER_JWKS_ENDPOINT: str = ""
    LICENSE_SERVER_ACTIVATION_ENDPOINT: str = ""
    LICENSE_KEY: str = ""


settings = Settings()
configure_logging()
