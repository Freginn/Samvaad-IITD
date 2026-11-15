from quickcompare.config import load_offers, load_payment_methods, load_platforms
from quickcompare.connectors import build_connector
from quickcompare.models import BasketItem, Listing, Offer, OfferType, PaymentMethod, PlatformFees, Realization
from quickcompare.optimizer import PlatformContext, best_split, rank_single_orders
from quickcompare.pricing import quote_order

CARD = PaymentMethod("hdfc", "HDFC", reward_rates={"im": 10, "*": 1})
UPI = PaymentMethod("upi", "UPI")


def L(platform, price, q="x"):
    return Listing(platform=platform, query=q, title=q, unit_price=price, eta_minutes=10)


def test_fees_waived_by_threshold_and_membership():
    fees = PlatformFees(delivery_fee=30, free_delivery_above=199, small_cart_fee=20, small_cart_below=99,
                        membership="one")
    assert fees.total(50, set()) == {"delivery": 30, "small_cart": 20}
    assert fees.total(250, set()) == {}
    assert fees.total(150, {"one"}) == {}


def test_coupon_then_bank_offer_then_card_rewards():
    offers = [
        Offer("c", "flat 50", OfferType.FLAT, 50, platforms=["im"], group="coupon"),
        Offer("c2", "flat 20", OfferType.FLAT, 20, platforms=["im"], group="coupon"),   # loses to c
        Offer("b", "10% hdfc", OfferType.PERCENT, 10, platforms=["im"], payment_method="hdfc",
              max_discount=100, group="bank"),
    ]
    q = quote_order("im", [(L("im", 500), 1)], PlatformFees(), offers, CARD)
    assert [l.amount for l in q.instant] == [50, 45]          # 10% of (500-50)
    assert q.pay_now == 405
    assert q.cashback_total == 40.5                           # 10% card reward on 405
    assert q.effective_cost == 364.5


def test_min_items_cashback_like_amazon_now_6_items():
    o = Offer("a", "50 cb on 6", OfferType.FLAT, 50, platforms=["an"], min_items=6,
              realization=Realization.CASHBACK)
    five = quote_order("an", [(L("an", 20), 5)], PlatformFees(), [o], UPI)
    six = quote_order("an", [(L("an", 20), 6)], PlatformFees(), [o], UPI)
    assert five.cashback_total == 0 and six.cashback_total == 50


def test_split_beats_single_when_items_cheap_in_different_places():
    basket = [BasketItem("a"), BasketItem("b")]
    ctx = [PlatformContext("p1", PlatformFees(), {"a": L("p1", 10, "a"), "b": L("p1", 100, "b")}),
           PlatformContext("p2", PlatformFees(), {"a": L("p2", 100, "a"), "b": L("p2", 10, "b")})]
    plan = best_split(basket, ctx, [], [UPI], max_orders=2)
    assert plan.effective_cost == 20 and len(plan.orders) == 2
    # with a delivery fee per order, a single order wins
    for c in ctx:
        c.fees = PlatformFees(delivery_fee=200)
    assert len(best_split(basket, ctx, [], [UPI], max_orders=2).orders) == 1


def test_sample_data_end_to_end():
    plats = load_platforms()
    basket = [BasketItem("Amul Taaza Milk 1L", 2), BasketItem("Eggs (12 pack)"), BasketItem("Aashirvaad Atta 5kg")]
    ctxs = []
    for n, cfg in plats.items():
        if cfg["category"] != "grocery":
            continue
        c = build_connector(n, cfg)
        ctxs.append(PlatformContext(n, cfg["fees"], {i.query: c.best_listing(i) for i in basket if c.best_listing(i)}))
    ranked = rank_single_orders(basket, ctxs, load_offers(), load_payment_methods())
    assert ranked and ranked[0].effective_cost <= ranked[-1].effective_cost
    assert any(q.missing for q in ranked)   # flipkart_minutes has no eggs in sample data
