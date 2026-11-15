"""Core data types shared by connectors, the pricing engine and the optimizer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OfferType(str, Enum):
    PERCENT = "percent"
    FLAT = "flat"


class Realization(str, Enum):
    INSTANT = "instant"      # reduces the amount you pay at checkout
    CASHBACK = "cashback"    # credited later (wallet, statement, points)


@dataclass(frozen=True)
class BasketItem:
    """What the user wants, platform-agnostic."""
    query: str               # e.g. "Amul Taaza milk 1L"
    quantity: int = 1


@dataclass(frozen=True)
class Listing:
    """One platform's match for a BasketItem."""
    platform: str
    query: str
    title: str
    unit_price: float        # selling price per unit, after the platform's own markdown
    mrp: Optional[float] = None
    available: bool = True
    product_id: Optional[str] = None
    eta_minutes: Optional[int] = None


@dataclass
class PlatformFees:
    delivery_fee: float = 0.0
    free_delivery_above: Optional[float] = None
    handling_fee: float = 0.0
    platform_fee: float = 0.0
    small_cart_fee: float = 0.0
    small_cart_below: Optional[float] = None
    # Membership (Swiggy One, Zepto Pass, Prime...) waives delivery fee when owned.
    membership: Optional[str] = None

    def total(self, item_total: float, memberships: set[str]) -> dict[str, float]:
        fees: dict[str, float] = {}
        waived = self.membership is not None and self.membership in memberships
        free = self.free_delivery_above is not None and item_total >= self.free_delivery_above
        if self.delivery_fee and not (waived or free):
            fees["delivery"] = self.delivery_fee
        if self.handling_fee:
            fees["handling"] = self.handling_fee
        if self.platform_fee:
            fees["platform"] = self.platform_fee
        if self.small_cart_fee and self.small_cart_below is not None and item_total < self.small_cart_below:
            fees["small_cart"] = self.small_cart_fee
        return fees


@dataclass
class Offer:
    """A discount or cashback rule.

    `platforms` empty means "any platform"; `payment_method` None means the
    offer does not depend on how you pay (e.g. a platform coupon).
    Offers sharing a `group` are mutually exclusive: only the best one in a
    group is applied (platforms typically allow one coupon + one bank offer).
    """
    id: str
    description: str
    type: OfferType
    value: float
    realization: Realization = Realization.INSTANT
    platforms: list[str] = field(default_factory=list)
    payment_method: Optional[str] = None
    min_order: float = 0.0
    min_items: int = 0
    max_discount: Optional[float] = None
    group: str = "coupon"
    # Fraction of face value a cashback is really worth to you
    # (1.0 for cash/statement credit, ~0.25-0.5 for hard-to-use points).
    value_factor: float = 1.0

    def applies(self, platform: str, payment_method: Optional[str], item_total: float, item_count: int) -> bool:
        if self.platforms and platform not in self.platforms:
            return False
        if self.payment_method is not None and self.payment_method != payment_method:
            return False
        return item_total >= self.min_order and item_count >= self.min_items

    def amount(self, base: float) -> float:
        raw = base * self.value / 100.0 if self.type == OfferType.PERCENT else self.value
        if self.max_discount is not None:
            raw = min(raw, self.max_discount)
        return round(min(raw, base), 2)


@dataclass
class PaymentMethod:
    id: str
    name: str
    # Base card rewards on every spend, per platform (e.g. Swiggy HDFC: 10% on Swiggy).
    # Key "*" is the default rate for any other platform.
    reward_rates: dict[str, float] = field(default_factory=dict)
    reward_value_factor: float = 1.0
    reward_cap_per_txn: Optional[float] = None

    def reward_rate(self, platform: str) -> float:
        return self.reward_rates.get(platform, self.reward_rates.get("*", 0.0))


@dataclass
class AppliedLine:
    label: str
    amount: float            # positive = you save/receive this much
    realization: Realization


@dataclass
class OrderQuote:
    """The full cost picture for one order on one platform with one payment method."""
    platform: str
    payment_method: str
    listings: list[tuple[Listing, int]]
    item_total: float
    fees: dict[str, float]
    instant: list[AppliedLine]
    cashback: list[AppliedLine]
    missing: list[str] = field(default_factory=list)
    eta_minutes: Optional[int] = None

    @property
    def fee_total(self) -> float:
        return round(sum(self.fees.values()), 2)

    @property
    def pay_now(self) -> float:
        return round(self.item_total + self.fee_total - sum(l.amount for l in self.instant), 2)

    @property
    def cashback_total(self) -> float:
        return round(sum(l.amount for l in self.cashback), 2)

    @property
    def effective_cost(self) -> float:
        """What the order really costs you once cashback lands."""
        return round(self.pay_now - self.cashback_total, 2)
