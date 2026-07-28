import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    chatclipy_base_url: str
    chatclipy_api_token: str
    chatclipy_whatsapp_id: int
    chatclipy_template_name: str
    chatclipy_language_code: str
    webhook_shared_secret: str
    state_db_path: str
    admin_username: str
    admin_password: str


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    return Settings(
        chatclipy_base_url=_require("CHATCLIPY_BASE_URL").rstrip("/"),
        chatclipy_api_token=_require("CHATCLIPY_API_TOKEN"),
        chatclipy_whatsapp_id=int(_require("CHATCLIPY_WHATSAPP_ID")),
        chatclipy_template_name=_require("CHATCLIPY_TEMPLATE_NAME"),
        chatclipy_language_code=os.environ.get("CHATCLIPY_LANGUAGE_CODE", "pt_BR"),
        webhook_shared_secret=_require("WEBHOOK_SHARED_SECRET"),
        state_db_path=os.environ.get("STATE_DB_PATH", "/data/state.db"),
        admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
        admin_password=_require("ADMIN_PASSWORD"),
    )
