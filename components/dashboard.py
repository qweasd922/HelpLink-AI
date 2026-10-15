import html
import streamlit as st
from components.report_card import badge
from services.database_service import compute_stats
from services.rules import CATEGORIES, STATUS_LABEL


def _rows(items) -> str:
    return "".join(f'<div class="hl-sumrow"><span>{label}</span><span class="hl-pill">{n} items</span></div>' for label, n in items)


def render_dashboard(reports: list) -> None:
    s = compute_stats(reports)
    cards = [("Total reports", s["total"], "plain"), ("Open tasks", s["open"], "purple"),
             ("In progress", s["in_progress"], "amber"), ("Resolved", s["resolved"], "green")]
    for col, (label, value, variant) in zip(st.columns(4), cards):
        col.markdown(f'<div class="hl-stat hl-stat-{variant}"><p>{label}</p><b>{value}</b></div>', unsafe_allow_html=True)
    if not s["total"]:
        return
    by_cat = [(html.escape(c), sum(r["category"] == c for r in reports)) for c in CATEGORIES]
    by_status = [(badge(k), sum(r["status"] == k for r in reports)) for k in STATUS_LABEL]
    left, right = st.columns(2)
    left.markdown(f'<div class="hl-panel"><h4>Summary by category</h4>{_rows(x for x in by_cat if x[1])}</div>', unsafe_allow_html=True)
    right.markdown(f'<div class="hl-panel"><h4>Summary by status</h4>{_rows(x for x in by_status if x[1])}</div>', unsafe_allow_html=True)
