"""Serves fictional prices from data/sample_catalog.json so the app runs offline."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from ..config import DATA_DIR
from ..models import Listing
from .base import Connector


@lru_cache(maxsize=1)
def _catalog() -> dict:
    with open(DATA_DIR / "sample_catalog.json", encoding="utf-8") as f:
        return json.load(f)["catalog"]


class MockConnector(Connector):
    def search(self, query: str, location: Optional[str] = None) -> list[Listing]:
        q = query.lower()
        out = []
        for title, row in _catalog().get(self.name, {}).items():
            if q in title.lower() or title.lower() in q:
                out.append(Listing(platform=self.name, query=query, title=row["title"],
                                   unit_price=row["unit_price"], mrp=row.get("mrp"),
                                   eta_minutes=row.get("eta_minutes"), product_id=title))
        return out
