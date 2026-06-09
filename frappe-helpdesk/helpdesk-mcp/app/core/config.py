from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_TITLE: str = "Frappe Helpdesk MCP"
    VERSION: str = "0.1.0"
    ALLOWED_ORIGINS: str = "*"

    FRAPPE_API_URL: str = "http://frappe:8000"
    FRAPPE_SITE_NAME: str = "helpdesk.localhost"
    FRAPPE_VERIFY_SSL: int = 0
    FRAPPE_API_KEY: str = ""
    FRAPPE_API_SECRET: str = ""
    FRAPPE_USERNAME: str = "Administrator"
    FRAPPE_PASSWORD: str = "admin"


settings = Settings()
