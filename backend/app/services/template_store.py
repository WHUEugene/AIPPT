from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import UUID

from ..schemas.template import Template, TemplateCreate


class TemplateStore:
    """Persist template definitions inside a JSON file."""

    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text("[]\n", encoding="utf-8")
        self._lock = threading.Lock()

    def list_templates(self) -> List[Template]:
        records = self._load()
        return [Template(**record) for record in records]

    def save_template(self, payload: TemplateCreate) -> Template:
        new_template = Template(**payload.model_dump())
        with self._lock:
            records = self._load()
            records.append(json.loads(new_template.model_dump_json()))
            self._write(records)
        return new_template

    def get_template(self, template_id: UUID) -> Optional[Template]:
        for record in self._load():
            if str(record.get("id")) == str(template_id):
                return Template(**record)
        return None

    def _load(self) -> list[dict]:
        if not self.store_path.exists():
            return []
        raw = self.store_path.read_text(encoding="utf-8") or "[]"
        return json.loads(raw)

    def _write(self, records: Iterable[dict]) -> None:
        data = json.dumps(list(records), indent=2, ensure_ascii=False)
        self.store_path.write_text(data + "\n", encoding="utf-8")


__all__ = ["TemplateStore"]
