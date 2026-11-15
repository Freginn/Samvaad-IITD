"""Loads platform fees, offers and the user's payment methods from YAML."""
from __future__ import annotations

from pathlib import Path

import yaml

from .models import Offer, OfferType, PaymentMethod, PlatformFees, Realization

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_platforms(path: Path = DATA_DIR / "platforms.yaml") -> dict[str, dict]:
    """name -> {"label", "category", "fees": PlatformFees, "deep_link", "connector"}"""
    raw = _load(path).get("platforms", {})
    out = {}
    for name, p in raw.items():
        out[name] = {
            "label": p.get("label", name),
            "category": p.get("category", "grocery"),
            "fees": PlatformFees(**p.get("fees", {})),
            "deep_link": p.get("deep_link"),
            "connector": p.get("connector", "mock"),
        }
    return out


def _offer(d: dict) -> Offer:
    d = dict(d)
    d["type"] = OfferType(d["type"])
    d["realization"] = Realization(d.get("realization", "instant"))
    return Offer(**d)


def load_offers(path: Path = DATA_DIR / "offers.yaml") -> list[Offer]:
    return [_offer(o) for o in _load(path).get("offers", [])]


def load_payment_methods(path: Path = DATA_DIR / "payment_methods.yaml") -> list[PaymentMethod]:
    return [PaymentMethod(**p) for p in _load(path).get("payment_methods", [])]
