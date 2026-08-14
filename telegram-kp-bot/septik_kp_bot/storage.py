from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def now_iso() -> str:
    return datetime.now(ZoneInfo("Europe/Moscow")).isoformat(timespec="seconds")


class ProposalStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.proposals_dir = data_dir / "proposals"
        self.uploads_dir = data_dir / "uploads"
        self.rendered_dir = data_dir / "rendered"
        for path in (self.proposals_dir, self.uploads_dir, self.rendered_dir):
            path.mkdir(parents=True, exist_ok=True)

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def proposal_dir(self, proposal_id: str) -> Path:
        return self.proposals_dir / proposal_id

    def proposal_json_path(self, proposal_id: str) -> Path:
        return self.proposal_dir(proposal_id) / "proposal.json"

    def rendered_path(self, proposal_id: str) -> Path:
        return self.proposal_dir(proposal_id) / f"{proposal_id}.png"

    def upload_path(self, proposal_id: str, suffix: str) -> Path:
        suffix = suffix if suffix.startswith(".") else f".{suffix}"
        return self.uploads_dir / f"{proposal_id}{suffix}"

    def save(self, record: dict[str, Any]) -> None:
        proposal_id = str(record["proposal_id"])
        record["updated_at"] = now_iso()
        path = self.proposal_json_path(proposal_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, user_id: int, chat_id: int, source_text: str, result: dict[str, Any]) -> dict[str, Any]:
        proposal_id = self.new_id()
        record = {
            "proposal_id": proposal_id,
            "status": "draft_text",
            "telegram_user_id": user_id,
            "telegram_chat_id": chat_id,
            "source_text": source_text,
            "corrections": [],
            "payload": result["payload"],
            "calculation_text": result["calculation_text"],
            "missing_data": result["missing_data"],
            "warnings": result["warnings"],
            "ai_payload": result["ai_payload"],
            "render_result": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.save(record)
        return record

    def load(self, proposal_id: str) -> dict[str, Any]:
        path = self.proposal_json_path(proposal_id)
        return json.loads(path.read_text(encoding="utf-8"))
