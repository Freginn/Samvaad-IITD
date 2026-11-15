"""QuickCompare — Streamlit UI.  Run:  streamlit run app.py"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from quickcompare.config import load_offers, load_payment_methods, load_platforms
from quickcompare.connectors import ManualConnector, build_connector
from quickcompare.models import BasketItem
from quickcompare.optimizer import PlatformContext, best_split, rank_single_orders

st.set_page_config(page_title="QuickCompare", page_icon="🛒", layout="wide")
st.title("🛒 QuickCompare")
st.caption("Cheapest quick delivery across apps, offers and your cards. Sample prices and offers are illustrative.")

platforms_cfg = load_platforms()
offers = load_offers()
all_payments = load_payment_methods()

# ---------------- Sidebar: what to compare, what you own ----------------
with st.sidebar:
    category = st.radio("Category", ["grocery", "food"], horizontal=True)
    names = [n for n, p in platforms_cfg.items() if p["category"] == category]
    chosen = st.multiselect("Apps to compare", names, default=names,
                            format_func=lambda n: platforms_cfg[n]["label"])
    pay_ids = st.multiselect("Cards / payment methods you have", [p.id for p in all_payments],
                             default=[p.id for p in all_payments],
                             format_func=lambda i: next(p.name for p in all_payments if p.id == i))
    memberships = set(st.multiselect("Memberships", ["swiggy_one", "zepto_pass", "prime", "zomato_gold"]))
    max_eta = st.slider("Max delivery time (min)", 5, 60, 30)
    allow_split = st.checkbox("Allow splitting into 2 orders", value=True)

payments = [p for p in all_payments if p.id in pay_ids]

# ---------------- Basket ----------------
st.subheader("Basket")
default_basket = pd.DataFrame([
    {"item": "Amul Taaza Milk 1L", "qty": 2}, {"item": "Britannia Brown Bread", "qty": 1},
    {"item": "Eggs (12 pack)", "qty": 1}, {"item": "Maggi Masala 4-pack", "qty": 1},
    {"item": "Banana (6 pcs)", "qty": 1}, {"item": "Aashirvaad Atta 5kg", "qty": 1},
]) if category == "grocery" else pd.DataFrame([{"item": "Chicken Biryani", "qty": 1}])
basket_df = st.data_editor(default_basket, num_rows="dynamic", key=f"basket_{category}")
basket = [BasketItem(str(r["item"]).strip(), int(r["qty"] or 1))
          for _, r in basket_df.iterrows() if str(r["item"]).strip() and str(r["item"]) != "nan"]

connectors = {n: build_connector(n, platforms_cfg[n]) for n in chosen}

manual = [n for n, c in connectors.items() if isinstance(c, ManualConnector)]
if manual and basket:
    with st.expander(f"Enter prices for apps without an API ({', '.join(platforms_cfg[n]['label'] for n in manual)})",
                     expanded=True):
        cols = st.columns(len(manual))
        for col, n in zip(cols, manual):
            with col:
                st.markdown(f"**{platforms_cfg[n]['label']}**")
                for item in basket:
                    v = st.number_input(item.query, min_value=0.0, step=1.0, key=f"{n}:{item.query}")
                    connectors[n].set_price(item.query, v or None)

if not st.button("Compare", type="primary") and "results" not in st.session_state:
    st.stop()

# ---------------- Fetch & optimise ----------------
contexts, errors = [], []
for n, conn in connectors.items():
    listings = {}
    for item in basket:
        try:
            l = conn.best_listing(item)
        except Exception as e:  # live connectors can fail; keep going with others
            errors.append(f"{platforms_cfg[n]['label']}: {e}")
            break
        if l:
            listings[item.query] = l
    contexts.append(PlatformContext(n, platforms_cfg[n]["fees"], listings))
for e in errors:
    st.warning(e)

ranked = rank_single_orders(basket, contexts, offers, payments, memberships, max_eta)
split = best_split(basket, contexts, offers, payments, memberships, 2 if allow_split else 1, max_eta)
st.session_state["results"] = True

if not ranked:
    st.error("No app has these items within your delivery time.")
    st.stop()

pm_name = {p.id: p.name for p in all_payments}
best = ranked[0]

c1, c2, c3 = st.columns(3)
c1.metric("Best single order", f"₹{best.effective_cost:,.0f}",
          f"{platforms_cfg[best.platform]['label']} · {pm_name[best.payment_method]}", delta_color="off")
c2.metric("Pay now", f"₹{best.pay_now:,.0f}", f"₹{best.cashback_total:,.0f} cashback later", delta_color="off")
if split and len(split.orders) > 1 and split.effective_cost < best.effective_cost - 0.5:
    c3.metric("Split across 2 apps", f"₹{split.effective_cost:,.0f}",
              f"saves ₹{best.effective_cost - split.effective_cost:,.0f} more", delta_color="normal")
    with st.expander("Split plan"):
        for o in split.orders:
            st.write(f"**{platforms_cfg[o.platform]['label']}** with {pm_name[o.payment_method]}: "
                     + ", ".join(f"{l.title} ×{q}" for l, q in o.listings) + f" → ₹{o.effective_cost:,.0f}")

st.subheader("All options")
table = pd.DataFrame([{
    "App": platforms_cfg[q.platform]["label"],
    "Pay with": pm_name[q.payment_method],
    "Items": q.item_total,
    "Fees": q.fee_total,
    "Instant off": round(sum(l.amount for l in q.instant), 2),
    "Pay now": q.pay_now,
    "Cashback": q.cashback_total,
    "Effective": q.effective_cost,
    "ETA": q.eta_minutes,
    "Missing": ", ".join(q.missing),
} for q in ranked])
st.dataframe(table, hide_index=True, use_container_width=True)

st.subheader("Why")
for q in ranked[:5]:
    with st.expander(f"{platforms_cfg[q.platform]['label']} + {pm_name[q.payment_method]} → ₹{q.effective_cost:,.2f}"):
        st.write(f"Items ₹{q.item_total:,.2f}")
        for k, v in q.fees.items():
            st.write(f"+ {k} fee ₹{v:,.2f}")
        for l in q.instant:
            st.write(f"− {l.label}: ₹{l.amount:,.2f}")
        st.write(f"**Pay now ₹{q.pay_now:,.2f}**")
        for l in q.cashback:
            st.write(f"↩ {l.label}: ₹{l.amount:,.2f} later")
        if q.missing:
            st.warning("Not available: " + ", ".join(q.missing))

# ---------------- Order ----------------
st.subheader("Order")
conn = connectors[best.platform]
label = platforms_cfg[best.platform]["label"]
if conn.can_order:
    confirm = st.checkbox(f"I confirm: place this order on {label}, paying ₹{best.pay_now:,.2f} "
                          f"with {pm_name[best.payment_method]}")
    if st.button(f"Place order on {label}", disabled=not confirm):
        res = conn.place_order(best.listings, best.payment_method)
        (st.success if res.placed else st.info)(res.message)
        if res.open_url:
            st.link_button("Complete payment", res.open_url)
else:
    st.info(f"{label} isn't connected for ordering. Open the app and use {pm_name[best.payment_method]} at checkout.")
    for l, qty in best.listings:
        url = conn.deep_link(l.title)
        if url:
            st.link_button(f"{l.title} ×{qty} on {label}", url)
