import html
import streamlit as st
from services.rules import STATUS_LABEL

# Pastel purple (#B19CD8) theme, matching the CampusFix design.
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
.stApp{background:linear-gradient(135deg,#f8f6fc 0%,#f1f5f9 50%,#f0ecf7 100%)}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp input,.stApp textarea,.stApp button{font-family:'Sarabun','Segoe UI',Roboto,sans-serif}
footer{visibility:hidden}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2rem;max-width:1100px}

/* Sidebar */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#483565 0%,#58407d 45%,#0f172a 100%);border-right:1px solid rgba(108,79,154,.4)}
.hl-brand{display:flex;gap:.8rem;align-items:center;padding:.4rem 0 1rem;border-bottom:1px solid rgba(108,79,154,.35);margin-bottom:1rem}
.hl-logo{background:linear-gradient(135deg,#B19CD8,#9b7ec9);border-radius:16px;padding:.5rem .65rem;font-size:1.4rem;box-shadow:0 0 0 2px rgba(255,255,255,.2)}
.hl-brand-name,.hl-name{color:#fff;font-weight:800;font-size:1.45rem;line-height:1.1}
.hl-brand-name span,.hl-name span{color:#B19CD8}
.hl-brand-sub,.hl-sub{color:#e2daf2;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase}
.hl-role{color:#B19CD8;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:.5rem .8rem;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em}
.hl-who,.hl-user{color:#e2daf2;font-size:.8rem;margin:.4rem .2rem 1rem}
.hl-demo{background:rgba(251,191,36,.15);color:#fde68a;border:1px solid rgba(251,191,36,.35);border-radius:12px;padding:.5rem .8rem;font-size:.75rem;font-weight:700;margin:1rem 0 .5rem}
section[data-testid="stSidebar"] [role="radiogroup"]{gap:.4rem}
section[data-testid="stSidebar"] [role="radiogroup"] label{width:100%;border-radius:16px;padding:.75rem 1rem;border:1px solid transparent;transition:all .2s}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.1)}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,#B19CD8,#8363b4);border-color:rgba(177,156,216,.4);box-shadow:0 8px 20px rgba(0,0,0,.3)}
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not([data-testid="stMarkdownContainer"]){display:none}
section[data-testid="stSidebar"] [role="radiogroup"] label p{color:#f0ecf7;font-weight:600;font-size:.92rem}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:#fff;font-weight:800}
section[data-testid="stSidebar"] .stButton button{width:100%;background:rgba(255,255,255,.1)!important;color:#f0ecf7!important;border:1px solid rgba(255,255,255,.18)!important;border-radius:16px;font-weight:700;padding:.6rem}
section[data-testid="stSidebar"] .stButton button:hover{background:rgba(255,255,255,.2)!important;border-color:#B19CD8!important;color:#fff!important}

/* Buttons */
.stApp button[kind="primary"],.stApp button[kind="primaryFormSubmit"],.stApp button[data-testid="stBaseButton-primary"],.stApp button[data-testid="stBaseButton-primaryFormSubmit"]{background:linear-gradient(90deg,#B19CD8,#8363b4);border:none;color:#fff;border-radius:16px;font-weight:800;box-shadow:0 8px 18px rgba(131,99,180,.3)}
.stApp button[kind="primary"]:hover,.stApp button[kind="primaryFormSubmit"]:hover,.stApp button[data-testid="stBaseButton-primary"]:hover,.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover{filter:brightness(.96);color:#fff}
.stApp button[kind="secondary"],.stApp button[data-testid="stBaseButton-secondary"]{border-radius:16px;border:1px solid #cbbde9;background:#fff;color:#483565;font-weight:700}

/* Inputs */
.stTextInput input,.stTextArea textarea,.stNumberInput input{border-radius:16px!important;background:#f8f6fc!important}
[data-baseweb="select"]>div,[data-baseweb="input"],[data-baseweb="textarea"]{border-radius:16px!important;background:#f8f6fc!important;border-color:#e2daf2!important}

/* Page header */
.hl-head{background:rgba(255,255,255,.92);border:1px solid #f0ecf7;border-radius:24px;padding:1.4rem 1.8rem;box-shadow:0 2px 10px rgba(72,53,101,.06);margin-bottom:1.2rem}
.hl-head h1{font-size:2rem!important;font-weight:900!important;color:#0f172a;margin:0!important;padding:0!important;line-height:1.2}
.hl-head p{color:#475569;margin:.3rem 0 0}

/* Issue cards */
[class*="st-key-card_"]{background:rgba(255,255,255,.96);border:1px solid #f0ecf7;border-radius:24px;box-shadow:0 4px 14px rgba(72,53,101,.08);padding:1.1rem 1.2rem 1.7rem!important;margin-bottom:.9rem;transition:box-shadow .2s}
[class*="st-key-card_"]:hover{box-shadow:0 12px 28px rgba(72,53,101,.16)}
[class*="st-key-card_"] .stButton{margin-top:.9rem}
.hl-row{display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem;margin-bottom:.6rem}
.hl-id{font-family:monospace;font-size:.7rem;font-weight:700;color:#58407d;background:#f8f6fc;border:1px solid #e2daf2;border-radius:6px;padding:.15rem .5rem;white-space:nowrap}
.hl-title{font-size:1.1rem;font-weight:800;color:#0f172a;margin:.2rem 0 .3rem}
.hl-loc{color:#475569;font-size:.85rem;font-weight:600}
.hl-desc{color:#475569;font-size:.85rem;margin:.4rem 0 .2rem}
.hl-foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.5rem;border-top:1px solid #f0ecf7;padding-top:.7rem;margin-top:.6rem;margin-bottom:.5rem;font-size:.75rem;color:#94a3b8}
.hl-chip{display:inline-block;background:#f8f6fc;color:#483565;border:1px solid #f0ecf7;border-radius:8px;padding:.2rem .6rem;font-weight:700;margin-right:.3rem}
.hl-badge{display:inline-block;padding:.2rem .65rem;border-radius:8px;font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;border:1px solid;margin-right:.3rem}

/* Dashboard */
.hl-stat{border-radius:24px;padding:1.2rem 1.4rem;border:1px solid #e2daf2;background:rgba(255,255,255,.95);box-shadow:0 2px 8px rgba(72,53,101,.06)}
.hl-stat p{font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#64748b;margin:0}
.hl-stat b{display:block;font-size:2rem;font-weight:900;color:#2f2145;margin-top:.3rem}
.hl-stat-purple{background:linear-gradient(135deg,#f8f6fc,#e2daf2)}
.hl-stat-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}.hl-stat-amber p{color:#b45309}.hl-stat-amber b{color:#92400e}
.hl-stat-green{background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#a7f3d0}.hl-stat-green p{color:#047857}.hl-stat-green b{color:#065f46}
.hl-panel{background:rgba(255,255,255,.95);border:1px solid #e2daf2;border-radius:24px;padding:1.3rem 1.4rem;margin:1rem 0}
.hl-panel h4{margin:0 0 .8rem;font-weight:800;color:#0f172a}
.hl-sumrow{display:flex;justify-content:space-between;align-items:center;padding:.7rem .9rem;margin-bottom:.5rem;background:rgba(248,246,252,.8);border:1px solid #f0ecf7;border-radius:16px;font-weight:700;font-size:.9rem;color:#334155}
.hl-pill{background:rgba(177,156,216,.3);color:#483565;border:1px solid #cbbde9;border-radius:999px;padding:.15rem .8rem;font-size:.75rem;font-weight:800}
</style>"""

COLORS = {  # (text, background, border)
    "open": ("#483565", "#f0ecf7", "#e2daf2"), "claimed": ("#5b21b6", "#ede9fe", "#ddd6fe"),
    "in_progress": ("#6b21a8", "#f3e8ff", "#e9d5ff"), "awaiting_confirmation": ("#92400e", "#fef3c7", "#fde68a"),
    "resolved": ("#1e293b", "#e2e8f0", "#cbd5e1"), "cancelled": ("#475569", "#f1f5f9", "#e2e8f0"),
}


def badge(status: str) -> str:
    fg, bg, bd = COLORS[status]
    return f'<span class="hl-badge" style="color:{fg};background:{bg};border-color:{bd}">{STATUS_LABEL[status]}</span>'


def render_card(r: dict) -> None:
    e = html.escape  # every user-supplied value is escaped before it goes into HTML
    if r.get("photo_url"):
        st.image(r["photo_url"])
    desc = r.get("description") or ""
    desc = desc if len(desc) <= 160 else desc[:157] + "…"
    foot = f'<span class="hl-chip">{e(r["category"])}</span>'
    if r.get("volunteer_name"):
        foot += f'<span class="hl-chip">🔧 {e(r["volunteer_name"])}</span>'
    st.markdown(
        f'<div class="hl-row"><div>{badge(r["status"])}</div><span class="hl-id">FIX-{e(str(r["id"])[:4].upper())}</span></div>'
        f'<div class="hl-title">{e(r["title"])}</div>'
        f'<div class="hl-loc"><span style="color:#B19CD8">📍</span> {e(r["location_name"])}</div>'
        + (f'<div class="hl-desc">{e(desc)}</div>' if desc else "")
        + f'<div class="hl-foot"><div>{foot}</div><span>{e(str(r["created_at"])[:16].replace("T", " "))}</span></div>',
        unsafe_allow_html=True)
    for f in r.get("safety_flags") or []:
        st.warning(f"⚠️ Needs human review: {f}")
    if r.get("is_demo"):
        st.caption("🧪 Simulated sample data")
