"""Connector interface: each delivery app implements search and (optionally) ordering."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

from ..models import BasketItem, Listing


@dataclass
class OrderResult:
    placed: bool
    message: str
    order_id: Optional[str] = None
    open_url: Optional[str] = None   # where the user finishes checkout, if not placed


class Connector(ABC):
    can_order: bool = False

    def __init__(self, name: str, cfg: dict):
        self.name = name
        self.cfg = cfg

    @abstractmethod
    def search(self, query: str, location: Optional[str] = None) -> list[Listing]:
        """Candidate listings for a query, best match first."""

    def best_listing(self, item: BasketItem, location: Optional[str] = None) -> Optional[Listing]:
        hits = [l for l in self.search(item.query, location) if l.available]
        return min(hits, key=lambda l: l.unit_price) if hits else None

    def deep_link(self, query: str) -> Optional[str]:
        tpl = self.cfg.get("deep_link")
        return tpl.format(q=quote_plus(query)) if tpl else None

    def place_order(self, lines: list[tuple[Listing, int]], payment_method: str,
                    coupon: Optional[str] = None) -> OrderResult:
        """Default: no ordering API, so hand the user off to the app."""
        first = lines[0][0].query if lines else ""
        return OrderResult(
            placed=False,
            message=f"{self.cfg.get('label', self.name)} isn't connected for ordering; open the app to check out.",
            open_url=self.deep_link(first),
        )
