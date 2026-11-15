"""Turns a cart on one platform + one payment method into an OrderQuote.

Order of operations (mirrors how Indian quick-commerce checkouts work):
  1. item total (selling prices x quantities)
  2. + fees (delivery / handling / platform / small-cart), membership waivers
  3. - best platform coupon (one per order, per `group`)
  4. - best payment-linked instant discount, computed on the post-coupon amount
  5. cashback offers (deferred), then base card rewards on the amount actually charged
"""
from __future__ import annotations

from .models import (
    AppliedLine,
    Listing,
    Offer,
    OrderQuote,
    PaymentMethod,
    PlatformFees,
    Realization,
)


def _best_per_group(candidates: list[tuple[Offer, float]]) -> list[tuple[Offer, float]]:
    best: dict[str, tuple[Offer, float]] = {}
    for offer, amt in candidates:
        cur = best.get(offer.group)
        if cur is None or amt * offer.value_factor > cur[1] * cur[0].value_factor:
            best[offer.group] = (offer, amt)
    return [v for v in best.values() if v[1] > 0]


def quote_order(
    platform: str,
    lines: list[tuple[Listing, int]],
    fees: PlatformFees,
    offers: list[Offer],
    payment: PaymentMethod,
    memberships: set[str] | None = None,
    missing: list[str] | None = None,
) -> OrderQuote:
    memberships = memberships or set()
    item_total = round(sum(l.unit_price * q for l, q in lines), 2)
    item_count = sum(q for _, q in lines)
    fee_map = fees.total(item_total, memberships) if lines else {}

    eligible = [o for o in offers if o.applies(platform, payment.id, item_total, item_count)]

    # Platform-level coupons first (not tied to a payment method), on item total.
    coupon_like = [o for o in eligible if o.payment_method is None]
    pay_linked = [o for o in eligible if o.payment_method is not None]

    instant: list[AppliedLine] = []
    cashback: list[AppliedLine] = []

    applied_coupons = _best_per_group([(o, o.amount(item_total)) for o in coupon_like])
    for o, amt in applied_coupons:
        target = instant if o.realization == Realization.INSTANT else cashback
        target.append(AppliedLine(o.description, round(amt * o.value_factor, 2), o.realization))

    after_coupons = item_total + sum(fee_map.values()) - sum(l.amount for l in instant)
    applied_pay = _best_per_group([(o, o.amount(max(after_coupons, 0))) for o in pay_linked])
    for o, amt in applied_pay:
        target = instant if o.realization == Realization.INSTANT else cashback
        target.append(AppliedLine(o.description, round(amt * o.value_factor, 2), o.realization))

    charged = item_total + sum(fee_map.values()) - sum(l.amount for l in instant)
    rate = payment.reward_rate(platform)
    if rate and charged > 0:
        reward = charged * rate / 100.0
        if payment.reward_cap_per_txn is not None:
            reward = min(reward, payment.reward_cap_per_txn)
        reward = round(reward * payment.reward_value_factor, 2)
        if reward > 0:
            cashback.append(AppliedLine(f"{payment.name} rewards ({rate:g}%)", reward, Realization.CASHBACK))

    etas = [l.eta_minutes for l, _ in lines if l.eta_minutes is not None]
    return OrderQuote(
        platform=platform,
        payment_method=payment.id,
        listings=lines,
        item_total=item_total,
        fees=fee_map,
        instant=instant,
        cashback=cashback,
        missing=missing or [],
        eta_minutes=max(etas) if etas else None,
    )


def best_payment_quote(
    platform: str,
    lines: list[tuple[Listing, int]],
    fees: PlatformFees,
    offers: list[Offer],
    payments: list[PaymentMethod],
    memberships: set[str] | None = None,
    missing: list[str] | None = None,
) -> list[OrderQuote]:
    """All payment methods for this cart, cheapest effective cost first."""
    quotes = [quote_order(platform, lines, fees, offers, p, memberships, missing) for p in payments]
    return sorted(quotes, key=lambda q: q.effective_cost)
