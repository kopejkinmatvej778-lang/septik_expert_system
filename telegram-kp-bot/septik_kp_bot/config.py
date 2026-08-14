from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]


def _ids(value: str) -> set[int]:
    result: set[int] = set()
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if part:
            result.add(int(part))
    return result


def _path(value: str | None, default: str) -> Path:
    raw = (value or default).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    allowed_telegram_user_ids: set[int]
    owner_telegram_user_ids: set[int]
    openai_proposal_model: str
    openai_transcription_model: str
    data_dir: Path
    price_catalog_path: Path
    proposal_template_path: Path
    font_regular_path: str | None
    font_bold_path: str | None
    google_service_account_file: Path | None
    google_clients_folder_id: str | None
    google_proposals_folder_id: str | None
    google_contracts_folder_id: str | None
    google_measurements_folder_id: str | None
    google_registry_sheet_id: str | None
    control_panel_api_url: str | None
    control_panel_api_token: str | None
    amocrm_base_url: str | None
    amocrm_access_token: str | None
    amocrm_refresh_token: str | None
    amocrm_client_id: str | None
    amocrm_client_secret: str | None
    amocrm_redirect_uri: str | None


def load_settings(require_bot: bool = True) -> Settings:
    load_dotenv(BASE_DIR / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if require_bot and not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if require_bot and not openai_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    return Settings(
        telegram_bot_token=token,
        openai_api_key=openai_key,
        allowed_telegram_user_ids=_ids(os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")),
        owner_telegram_user_ids=_ids(os.getenv("OWNER_TELEGRAM_USER_IDS", "")),
        openai_proposal_model=os.getenv("OPENAI_PROPOSAL_MODEL", "gpt-4o-mini").strip(),
        openai_transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe").strip(),
        data_dir=_path(os.getenv("DATA_DIR"), "storage"),
        price_catalog_path=_path(os.getenv("PRICE_CATALOG_PATH"), "assets/price-catalog.json"),
        proposal_template_path=_path(os.getenv("PROPOSAL_TEMPLATE_PATH"), "assets/septik-expert-kp-template-blank.png"),
        font_regular_path=os.getenv("FONT_REGULAR_PATH", "").strip() or None,
        font_bold_path=os.getenv("FONT_BOLD_PATH", "").strip() or None,
        google_service_account_file=_path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"), "") if os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip() else None,
        google_clients_folder_id=os.getenv("GOOGLE_CLIENTS_FOLDER_ID", "").strip() or None,
        google_proposals_folder_id=os.getenv("GOOGLE_PROPOSALS_FOLDER_ID", "").strip() or None,
        google_contracts_folder_id=os.getenv("GOOGLE_CONTRACTS_FOLDER_ID", "").strip() or None,
        google_measurements_folder_id=os.getenv("GOOGLE_MEASUREMENTS_FOLDER_ID", "").strip() or None,
        google_registry_sheet_id=os.getenv("GOOGLE_REGISTRY_SHEET_ID", "").strip() or None,
        control_panel_api_url=os.getenv("CONTROL_PANEL_API_URL", "").strip() or None,
        control_panel_api_token=os.getenv("CONTROL_PANEL_API_TOKEN", "").strip() or None,
        amocrm_base_url=os.getenv("AMOCRM_BASE_URL", "").strip().rstrip("/") or None,
        amocrm_access_token=os.getenv("AMOCRM_ACCESS_TOKEN", "").strip() or None,
        amocrm_refresh_token=os.getenv("AMOCRM_REFRESH_TOKEN", "").strip() or None,
        amocrm_client_id=os.getenv("AMOCRM_CLIENT_ID", "").strip() or None,
        amocrm_client_secret=os.getenv("AMOCRM_CLIENT_SECRET", "").strip() or None,
        amocrm_redirect_uri=os.getenv("AMOCRM_REDIRECT_URI", "").strip() or None,
    )
