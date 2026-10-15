import streamlit as st
from html import escape
from components.dashboard import render_dashboard
from components.report_card import CSS, render_card
from services import matching_service as match, notify_service, validation as val
from services.database_service import get_db
from services.rules import CATEGORIES, STATUS_LABEL, RuleError
from services.settings import DEMO

st.set_page_config(page_title="HelpLink AI", page_icon="🤝", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
db = get_db()


def act(fn, *args, ok="Done"):
    try:
        fn(*args)
    except (RuleError, ValueError) as e:
        st.error(str(e)); return
    except Exception as e:
        st.error(f"Something went wrong: {e}"); return
    st.toast(ok)
    st.rerun()


def load_reports() -> list:
    """Feed keeps working on DB failure: falls back to the last successful load, clearly labelled."""
    try:
        rows = db.list_reports()
        st.session_state["last_reports"] = rows
        return rows
    except Exception as e:
        st.error(f"Could not reach the database ({type(e).__name__}). Showing the last loaded data, if any.")
        return st.session_state.get("last_reports", [])


def hero(title, sub):
    st.markdown(f'<div class="hl-head"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def login():
    hero("🤝 HelpLink AI", "See a problem. Share it. Be the solution. · เห็นปัญหา แชร์ปัญหา ร่วมกันแก้")
    if DEMO:
        st.warning("🧪 DEMO MODE: simulated users and sample data. This is NOT real authentication.")
        u = st.selectbox("Sign in as", db.demo_users(), format_func=lambda x: x["display_name"])
        if st.button("Enter demo", type="primary"):
            db.sign_in_demo(u["id"]); st.rerun()
        return
    t_in, t_up = st.tabs(["Sign in", "Sign up"])
    with t_in:
        with st.form("signin_form"):  # a form sends what is typed even if the browser autofilled the boxes
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", type="primary")
        if go:
            if not e.strip() or not p:
                st.error("Please enter both your email and your password.")
            else:
                try:
                    db.sign_in(e.strip(), p); st.rerun()
                except Exception as ex:
                    st.error(f"Sign-in failed: {ex}")
    with t_up:
        with st.form("signup_form"):
            n = st.text_input("Display name")
            e2 = st.text_input("Email")
            p2 = st.text_input("Password (min 8)", type="password")
            role = st.radio("I want to…", ["reporter", "fixer"], horizontal=True,
                            format_func=lambda x: "📣 Report problems" if x == "reporter" else "🔧 Fix problems (get email alerts)")
            go2 = st.form_submit_button("Create account", type="primary")
        if go2:
            try:
                if len(n.strip()) < 1 or len(p2) < 8 or not e2.strip():
                    st.error("Enter a name, an email and a password of at least 8 characters.")
                elif db.sign_up(e2.strip(), p2, n.strip(), role):
                    st.rerun()
                else:
                    st.success("Account created. Confirm your email, then sign in.")
            except Exception as ex:
                st.error(f"Sign-up failed: {ex}")


def submit_completion(rid, up):
    data = up.getvalue()
    val.validate_image(data, up.type)
    db.complete(rid, db.store_photo(data, up.type))


def actions(r, ctx):
    uid, s, k = db.user["id"], r["status"], f"{ctx}_{r['id']}"
    if s == "open" and r["reporter_id"] != uid and db.user["role"] == "fixer":
        if st.button("🙋 Claim task", key=f"c_{k}", type="primary"):
            act(db.claim, r["id"], ok="Task claimed!")
    if s == "open" and r["reporter_id"] == uid and st.button("Cancel report", key=f"x_{k}"):
        act(db.cancel, r["id"])
    if r.get("claimed_by") == uid and s in ("claimed", "in_progress"):
        a, b = st.columns(2)
        if s == "claimed" and a.button("▶ Start work", key=f"s_{k}"):
            act(db.start, r["id"])
        if b.button("Release task", key=f"r_{k}"):
            act(db.release, r["id"])
        up = st.file_uploader("After-photo", type=["jpg", "jpeg", "png", "webp"], key=f"u_{k}")
        if up and st.button("✅ Submit completion", key=f"d_{k}", type="primary"):
            act(submit_completion, r["id"], up, ok="Submitted for confirmation")
    if r["reporter_id"] == uid and s == "awaiting_confirmation":
        if r.get("after_photo_url"):
            st.image(r["after_photo_url"], caption="After-photo from volunteer")
        a, b = st.columns(2)
        if a.button("✔ Confirm completion", key=f"ok_{k}", type="primary"):
            act(db.review, r["id"], "confirmed", ok="Resolved. Thank you!")
        if b.button("↩ Needs more work", key=f"nw_{k}"):
            act(db.review, r["id"], "needs_more_work")


def grid(rows, ctx):
    if not rows:
        st.info("Nothing here yet. Try changing the filters or report a problem.")
    cols = st.columns(2)
    for i, r in enumerate(rows):
        with cols[i % 2], st.container(key=f"card_{ctx}_{r['id']}"):
            render_card(r)
            actions(r, ctx)


def my_rank(reports):
    loc = st.session_state.get("my_loc", (None, None))
    return match.rank_tasks(reports, db.user["skills"], *loc)


def page_home(reports):
    hero("Community Dashboard", "Turning community reports into real-world action · แปลงปัญหาเป็นการลงมือทำ")
    render_dashboard(reports)
    if db.user["role"] == "fixer":
        st.subheader("⭐ Recommended for you")
        for r in my_rank(reports)[:3]:
            with st.container(border=True):
                st.markdown(f"**{r['title']}**  ·  match {r['score']}%")
                st.caption(" · ".join(r["reasons"]))
    st.subheader("Recent reports")
    grid(reports[:4], "home")


def page_feed(reports):
    hero("Community Feed · กระดานติดตามปัญหา", "Real-time updates on problems in your community")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    q = c1.text_input("Search", placeholder="title or description").lower()
    cats = c2.multiselect("Category", CATEGORIES)
    stats = c3.multiselect("Status", list(STATUS_LABEL), format_func=STATUS_LABEL.get)
    sort = c4.selectbox("Sort", ["Open first", "Recommended", "Newest"])
    rows = [r for r in reports if (not q or q in r["title"].lower() or q in r["description"].lower())
            and (not cats or r["category"] in cats) and (not stats or r["status"] in stats)]
    if sort == "Open first":
        rows.sort(key=lambda r: (r["status"] != "open", r["created_at"]), reverse=False)
        rows.sort(key=lambda r: r["status"] != "open")
    elif sort == "Recommended":
        ranked = {r["id"]: r for r in my_rank(rows)}
        for r in ranked.values():
            st.caption(f"{r['title']}: {r['score']}% ({'; '.join(r['reasons'])})")
        rows = list(ranked.values()) + [r for r in rows if r["id"] not in ranked]
    grid(rows, "feed")


def page_report():
    n = st.session_state.setdefault("form_n", 0)
    k = lambda s: f"{s}_{n}"
    hero("Report a problem · แจ้งปัญหาใหม่", "Pick a category and fixers who follow it will be emailed")
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
    st.caption("Fixers who follow the category you choose will be notified by email.")
    title = st.text_input("Title / หัวข้อ", max_chars=120, key=k("title"))
    cat = st.selectbox("Category / หมวดหมู่", CATEGORIES, key=k("cat"))
    desc = st.text_area("Describe the problem or the work needed / รายละเอียด", max_chars=1000, key=k("desc"))
    loc = st.text_input("Location or nearby landmark / สถานที่", max_chars=150, key=k("loc"))
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitude (optional)", value=None, min_value=-90.0, max_value=90.0, format="%.6f", key=k("lat"))
    lon = c2.number_input("Longitude (optional)", value=None, min_value=-180.0, max_value=180.0, format="%.6f", key=k("lon"))
    up = st.file_uploader("Photo (optional) / รูปภาพ", type=["jpg", "jpeg", "png", "webp"], key=k("photo"))

    if st.button("🚀 Publish report", type="primary"):
        try:
            val.validate_report_input(title, loc, lat, lon)
            photo = None
            if up:
                data = up.getvalue(); val.validate_image(data, up.type)
            with st.spinner("Publishing…"):
                if up:
                    photo = db.store_photo(data, up.type)
                report = {"title": title.strip(), "description": desc.strip()[:2000], "photo_url": photo,
                          "category": cat, "location_name": loc.strip(), "latitude": lat, "longitude": lon}
                db.create_report(report)
                status = notify_service.notify_fixers(report, db)  # never raises; report is already saved
        except (ValueError, RuleError) as e:
            st.error(str(e)); return
        except Exception as e:
            st.error(f"Could not publish: {e}"); return
        st.session_state["form_n"] = n + 1
        st.session_state["flash"] = status
        st.rerun()


def page_tasks(reports):
    uid = db.user["id"]
    if db.user["role"] == "reporter":
        hero("My Reports · รายงานของฉัน", "Problems you posted and how they are progressing")
        grid([r for r in reports if r["reporter_id"] == uid], "mine_r")
        return
    hero("My Tasks · งานของฉัน", "Work you are fixing and tasks recommended for you")
    t1, t2 = st.tabs(["I'm fixing", "Recommended"])
    with t1:
        grid([r for r in reports if r.get("claimed_by") == uid], "mine_v")
    with t2:
        st.caption("Score = 40% skill match + 35% proximity + 25% age. Missing data is skipped, never guessed.")
        grid(my_rank(reports), "rec")


def page_profile():
    hero("Profile · โปรไฟล์", "Your role and the categories you follow")
    role = db.user["role"]
    st.write(f"**{db.user['display_name']}** · " + ("🔧 Fixer" if role == "fixer" else "📣 Reporter"))
    if role == "fixer":
        skills = st.multiselect("Categories I want email alerts for", CATEGORIES, default=db.user["skills"])
        if st.button("Save categories"):
            act(db.save_skills, skills, ok="Saved")
        st.subheader("My approximate location (optional, this session only)")
        c1, c2 = st.columns(2)
        la, lo = c1.number_input("Latitude", value=None, format="%.6f"), c2.number_input("Longitude", value=None, format="%.6f")
        st.session_state["my_loc"] = (la, lo) if None not in (la, lo) else (None, None)
    else:
        st.info("Reporters post problems. Fixers who follow the category get an email.")


if not db.user:
    login(); st.stop()

with st.sidebar:
    role_label = "ทีมช่าง · Fixer" if db.user["role"] == "fixer" else "ผู้รายงานปัญหา · Reporter"
    st.markdown(
        '<div class="hl-brand"><div class="hl-logo">🤝</div><div><div class="hl-name">Help<span>Link</span></div>'
        '<div class="hl-sub">Community Fix Platform</div></div></div>'
        f'<div class="hl-role">🛡️ {role_label}</div><div class="hl-user">{escape(db.user["display_name"])}</div>',
        unsafe_allow_html=True)
    menu = (["Home", "Community Feed", "Report a Problem", "My Reports", "Profile"] if db.user["role"] == "reporter"
            else ["Home", "Community Feed", "My Tasks", "Profile"])
    icons = {"Home": "🏠", "Community Feed": "📋", "Report a Problem": "➕", "My Tasks": "🔧", "My Reports": "🗂️", "Profile": "👤"}
    page = st.radio("Menu", menu, label_visibility="collapsed", format_func=lambda x: f"{icons[x]}  {x}")
    if DEMO:
        st.markdown('<div class="hl-demo">🧪 DEMO MODE: simulated data</div>', unsafe_allow_html=True)
        if st.button("Reset demo data"):
            db.reset_demo(); st.rerun()
    if st.button("Sign out"):
        db.sign_out(); st.rerun()

reports = load_reports()
{"Home": lambda: page_home(reports), "Community Feed": lambda: page_feed(reports), "Report a Problem": page_report,
 "My Tasks": lambda: page_tasks(reports), "My Reports": lambda: page_tasks(reports), "Profile": page_profile}[page]()
