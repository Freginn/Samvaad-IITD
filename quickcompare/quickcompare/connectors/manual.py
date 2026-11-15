"""For apps without an API: prices are typed in by the user (or pasted from the app)."""
from __future__ import annotations

from typing import Optional

from ..models import Listing
from .base import Connector


class ManualConnector(Connector):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.prices: dict[str, float] = {}

    def set_price(self, query: str, unit_price: Optional[float]) -> None:
        if unit_price is None:
            self.prices.pop(query, None)
        else:
            self.prices[query] = unit_price

    def search(self, query: str, location: Optional[str] = None) -> list[Listing]:
        if query not in self.prices:
            return []
        return [Listing(platform=self.name, query=query, title=query, unit_price=self.prices[query])]
