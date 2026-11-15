"""Finds the cheapest way to buy a basket.

Two answers are produced:
  * single-order ranking: every (platform, payment method) pair for the whole
    basket, so you can see e.g. "Instamart + Swiggy HDFC" vs "Amazon Now + Amazon Pay ICICI".
  * split plan: the basket may be spread across platforms if that is cheaper
    even after paying each platform's fees again. Solved exactly with a DP over
    item subsets (fine for baskets up to ~12 distinct items).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import BasketItem, Listing, Offer, OrderQuote, PaymentMethod, PlatformFees
from .pricing import best_payment_quote


@dataclass
class PlatformContext:
    name: str
    fees: PlatformFees
    listings: dict[str, Listing]       # BasketItem.query -> chosen listing


@dataclass
class SplitPlan:
    orders: list[OrderQuote]

    @property
    def effective_cost(self) -> float:
        return round(sum(o.effective_cost for o in self.orders), 2)

    @property
    def pay_now(self) -> float:
        return round(sum(o.pay_now for o in self.orders), 2)


MAX_SPLIT_ITEMS = 12


def rank_single_orders(
    basket: list[BasketItem],
    platforms: list[PlatformContext],
    offers: list[Offer],
    payments: list[PaymentMethod],
    memberships: set[str] | None = None,
    max_eta: Optional[int] = None,
) -> list[OrderQuote]:
    """Every platform x payment combination, complete baskets first, then by cost."""
    quotes: list[OrderQuote] = []
    for ctx in platforms:
        lines, missing = [], []
        for item in basket:
            listing = ctx.listings.get(item.query)
            if listing and listing.available:
                lines.append((listing, item.quantity))
            else:
                missing.append(item.query)
        if not lines:
            continue
        for q in best_payment_quote(ctx.name, lines, ctx.fees, offers, payments, memberships, missing):
            if max_eta is not None and q.eta_minutes is not None and q.eta_minutes > max_eta:
                continue
            quotes.append(q)
    return sorted(quotes, key=lambda q: (len(q.missing), q.effective_cost))


def best_split(
    basket: list[BasketItem],
    platforms: list[PlatformContext],
    offers: list[Offer],
    payments: list[PaymentMethod],
    memberships: set[str] | None = None,
    max_orders: int = 2,
    max_eta: Optional[int] = None,
) -> Optional[SplitPlan]:
    """Cheapest assignment of every item to at most `max_orders` platforms.

    Returns None when some item is unavailable everywhere.
    """
    n = len(basket)
    if n == 0 or n > MAX_SPLIT_ITEMS:
        return None
    full = (1 << n) - 1

    # cost[p][mask] = best OrderQuote for that subset on platform p (or None)
    cost: list[dict[int, OrderQuote]] = []
    for ctx in platforms:
        table: dict[int, OrderQuote] = {}
        avail_mask = 0
        for i, item in enumerate(basket):
            l = ctx.listings.get(item.query)
            if l and l.available:
                avail_mask |= 1 << i
        sub = avail_mask
        while sub:
            lines = [(ctx.listings[basket[i].query], basket[i].quantity) for i in range(n) if sub >> i & 1]
            ranked = best_payment_quote(ctx.name, lines, ctx.fees, offers, payments, memberships)
            ranked = [q for q in ranked if max_eta is None or q.eta_minutes is None or q.eta_minutes <= max_eta]
            if ranked:
                table[sub] = ranked[0]
            sub = (sub - 1) & avail_mask
        cost.append(table)

    # dp over platforms: state = (covered mask, orders used)
    INF = float("inf")
    best: dict[tuple[int, int], tuple[float, list[OrderQuote]]] = {(0, 0): (0.0, [])}
    for table in cost:
        nxt = dict(best)
        for (mask, used), (c, orders) in best.items():
            if used >= max_orders:
                continue
            free = full & ~mask
            for sub, q in table.items():
                if sub & free != sub:
                    continue
                key = (mask | sub, used + 1)
                val = c + q.effective_cost
                if val < nxt.get(key, (INF,))[0]:
                    nxt[key] = (val, orders + [q])
        best = nxt

    finals = [v for (mask, _), v in best.items() if mask == full]
    if not finals:
        return None
    return SplitPlan(min(finals, key=lambda v: v[0])[1])
