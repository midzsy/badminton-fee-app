import streamlit as st
import pandas as pd
import calendar
import urllib.parse
import base64
import sqlite3
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(
    page_title="Badminton Fee Calculator",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "badminton_data.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def db_get(key, default=None):
    conn = get_conn()
    row  = conn.execute(
        "SELECT value FROM app_state WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else default

def db_set(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
        (key, json.dumps(value))
    )
    conn.commit()
    conn.close()

def db_delete(key):
    conn = get_conn()
    conn.execute("DELETE FROM app_state WHERE key=?", (key,))
    conn.commit()
    conn.close()

# ─── Load persisted state into session_state on first run ─────────────────────
if "db_loaded" not in st.session_state:
    st.session_state.player_list       = db_get("player_list",       [])
    st.session_state.att_state         = db_get("att_state",         {})
    st.session_state.excluded_sessions = set(db_get("excluded_sessions", []))
    st.session_state.session_hours     = db_get("session_hours",     {})
    st.session_state.db_loaded         = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #1B2A4A; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 2rem 2.5rem; max-width: 1200px; }
.stApp { background: #F4F6F9; }

.main .block-container,
.main .block-container p,
.main .block-container span,
.main .block-container label,
.main .block-container div { color: #1B2A4A !important; }

.page-header {
    background: linear-gradient(135deg, #1B2A4A 0%, #243656 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    display: flex; align-items: center; gap: 18px;
}
.page-header-title { color: #fff; font-size: 26px; font-weight: 600; letter-spacing: -0.5px; margin: 0; }
.page-header-sub   { color: rgba(255,255,255,0.55); font-size: 13px; margin: 2px 0 0 0; }

.section-card {
    background: #ffffff; border-radius: 14px; padding: 24px 28px;
    margin-bottom: 20px; border: 1px solid #E8ECF2;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.section-title {
    font-size: 13px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #7B8DB0 !important;
    margin-bottom: 18px; display: flex; align-items: center; gap: 8px;
}
.section-title::after { content: ''; flex: 1; height: 1px; background: #E8ECF2; }

.cal-wrap { border-radius: 12px; overflow: hidden; border: 1px solid #E8ECF2; }
.cal-header {
    background: #1B2A4A; padding: 14px 20px;
    display: flex; align-items: center; justify-content: space-between;
}
.cal-month { color: #fff; font-size: 15px; font-weight: 600; }
.cal-legend { display: flex; gap: 16px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: rgba(255,255,255,0.6) !important; }
.legend-dot  { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.day-headers { display: grid; grid-template-columns: repeat(7,1fr); background: #F8F9FC; border-bottom: 1px solid #E8ECF2; }
.day-hdr     { padding: 9px 4px; text-align: center; font-size: 11px; font-weight: 700; letter-spacing: 0.07em; color: #9BAAC4 !important; }
.day-hdr.match { color: #1B2A4A !important; }
.cal-grid    { display: grid; grid-template-columns: repeat(7,1fr); background: #fff; }
.cal-cell    { min-height: 76px; border-right: 1px solid #E8ECF2; border-bottom: 1px solid #E8ECF2; padding: 8px 10px; }
.cal-cell:nth-child(7n) { border-right: none; }
.cal-cell.empty         { background: #FAFBFC; }
.cal-cell.match-cell    { background: #EEF3FF; }
.cal-cell.excluded-cell { background: #FAFBFC; opacity: 0.55; }
.date-num { font-size: 13px; font-weight: 600; color: #1B2A4A !important; margin-bottom: 5px; }
.cal-cell.empty .date-num { color: #C8D0DC !important; font-weight: 400; }
.match-pill {
    display: inline-flex; align-items: center;
    background: #1B2A4A; color: #fff !important;
    border-radius: 5px; padding: 2px 8px; font-size: 11px; font-weight: 600;
}
.match-pill.off { background: #E8ECF2; color: #9BAAC4 !important; text-decoration: line-through; }

.metric-row  { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin-bottom: 20px; }
.metric-card { background: #fff; border-radius: 12px; padding: 20px 22px; border: 1px solid #E8ECF2; }
.metric-card.accent { background: linear-gradient(135deg,#1B2A4A 0%,#2E4170 100%); border-color: transparent; }
.metric-label { font-size: 11px; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; color: #9BAAC4 !important; margin-bottom: 6px; }
.metric-card.accent .metric-label { color: rgba(255,255,255,0.55) !important; }
.metric-value { font-size: 26px; font-weight: 600; color: #1B2A4A !important; font-family: 'DM Mono', monospace; }
.metric-card.accent .metric-value { color: #fff !important; }
.metric-sub   { font-size: 11px; color: #B0BBCF !important; margin-top: 4px; }

.summary-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 22px; }
.summary-card { background: #F8F9FC; border-radius: 10px; padding: 16px 18px; border: 1px solid #E8ECF2; }
.summary-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: #9BAAC4 !important; margin-bottom: 5px; }
.summary-value { font-size: 20px; font-weight: 600; color: #1B2A4A !important; font-family: 'DM Mono', monospace; }
.summary-card.highlight { background: #EEF3FF; border-color: #C5D3F5; }
.summary-card.highlight .summary-value { color: #2E4AB5 !important; }

.player-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 4px 0; }
.player-chip  {
    background: #EEF3FF; color: #2E4AB5 !important;
    border: 1px solid #C5D3F5; border-radius: 20px;
    padding: 4px 14px; font-size: 13px; font-weight: 500;
}

.wa-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    background: #25D366; color: #fff !important;
    border-radius: 8px; padding: 10px 20px;
    font-size: 13px; font-weight: 600;
    text-decoration: none; width: 100%;
}
.wa-btn:hover { background: #1da851; }

/* ══ SIDEBAR ══ */
section[data-testid="stSidebar"] { background: #1B2A4A !important; border-right: none; }
section[data-testid="stSidebar"] > div { background: #1B2A4A !important; }
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    color: rgba(255,255,255,0.55) !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.07em !important; text-transform: uppercase !important;
}
section[data-testid="stSidebar"] .stNumberInput > div {
    background: #ffffff !important; border-radius: 8px !important;
    overflow: hidden !important; border: none !important; gap: 0 !important;
}
section[data-testid="stSidebar"] .stNumberInput > div > div {
    background: transparent !important; border: none !important;
    border-radius: 0 !important; gap: 0 !important;
    display: flex !important; align-items: stretch !important;
}
section[data-testid="stSidebar"] .stNumberInput > div > div > input {
    background: #ffffff !important; border: none !important;
    border-left: 1px solid #E8ECF2 !important;
    border-right: 1px solid #E8ECF2 !important;
    border-radius: 0 !important; color: #1B2A4A !important;
    -webkit-text-fill-color: #1B2A4A !important;
    text-align: center !important; font-weight: 600 !important; font-size: 14px !important;
}
section[data-testid="stSidebar"] .stNumberInput button {
    background: #ffffff !important; border: none !important; border-radius: 0 !important;
    color: #1B2A4A !important; -webkit-text-fill-color: #1B2A4A !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    min-width: 36px !important; flex-shrink: 0 !important;
}
section[data-testid="stSidebar"] .stNumberInput button:hover {
    background: #E24B4A !important; color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
section[data-testid="stSidebar"] .stNumberInput button svg { fill: #1B2A4A !important; stroke: #1B2A4A !important; }
section[data-testid="stSidebar"] .stNumberInput button:hover svg { fill: #ffffff !important; stroke: #ffffff !important; }
section[data-testid="stSidebar"] .stNumberInput button p { color: #1B2A4A !important; -webkit-text-fill-color: #1B2A4A !important; }
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
    background-color: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important; color: #fff !important; -webkit-text-fill-color: #fff !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] span,
section[data-testid="stSidebar"] [data-baseweb="select"] div[class*="ValueContainer"],
section[data-testid="stSidebar"] [data-baseweb="select"] div[class*="singleValue"],
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] [data-baseweb="select"] input {
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: rgba(255,255,255,0.6) !important; }
section[data-testid="stSidebar"] .stTextInput > div > div {
    background-color: rgba(255,255,255,0.9) !important;
    border: 1px solid rgba(255,255,255,0.3) !important; border-radius: 8px !important;
}
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background-color: transparent !important; border: none !important;
    color: #1B2A4A !important; -webkit-text-fill-color: #1B2A4A !important;
}
section[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: rgba(0,0,0,0.35) !important; -webkit-text-fill-color: rgba(0,0,0,0.35) !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.12) !important; color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important; width: 100%; font-size: 13px !important;
}
section[data-testid="stSidebar"] .stButton button:hover { background: rgba(255,255,255,0.18) !important; }
section[data-testid="stSidebar"] .stFormSubmitButton button { display: none !important; }
section[data-testid="stSidebar"] p { color: #fff !important; -webkit-text-fill-color: #fff !important; }

.stDownloadButton button {
    background: #1B2A4A !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 500 !important; font-size: 13px !important; width: 100%;
}
.stDownloadButton button:hover { background: #243656 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #F0F2F7; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"]      { border-radius: 8px; font-size: 13px; font-weight: 500; color: #7B8DB0; padding: 6px 18px; }
.stTabs [aria-selected="true"]    { background: #fff !important; color: #1B2A4A !important; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
hr { border-color: #E8ECF2 !important; margin: 12px 0 !important; }
</style>
""", unsafe_allow_html=True)

DAY_NAMES   = {0: "Mon", 1: "Tue", 3: "Thu", 4: "Fri"}
DEFAULT_HRS = {0: 1,     1: 1,     3: 1,     4: 2}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_match_days(year, month, session_hours):
    cal_data = calendar.monthcalendar(year, month)
    result   = []
    for week in cal_data:
        for dow, name in DAY_NAMES.items():
            if week[dow] != 0:
                label = f"{name}-{week[dow]}"
                if label not in session_hours:
                    session_hours[label] = DEFAULT_HRS[dow]
                result.append({
                    "dow": dow, "day": name, "date": week[dow],
                    "label": label, "hours": session_hours[label]
                })
    return result

def build_calendar_html(year, month, all_match_days, excluded_set):
    days_in_month = calendar.monthrange(year, month)[1]
    first_dow_raw = calendar.monthrange(year, month)[0]
    first_dow_sun = (first_dow_raw + 1) % 7
    match_lookup  = {m["date"]: m for m in all_match_days}
    day_order     = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    match_names   = {"Mon", "Tue", "Thu", "Fri"}
    headers = "".join([
        f'<div class="day-hdr{" match" if d in match_names else ""}">{d}</div>'
        for d in day_order
    ])
    cells = "".join(['<div class="cal-cell empty"></div>'] * first_dow_sun)
    for d in range(1, days_in_month + 1):
        dow  = (first_dow_sun + d - 1) % 7
        info = match_lookup.get(d)
        if info:
            label    = info["label"]
            hrs      = info["hours"]
            excl     = label in excluded_set
            cell_cls = "cal-cell match-cell" + (" excluded-cell" if excl else "")
            pill_cls = "match-pill" + (" off" if excl else "")
            cells += (
                f'<div class="{cell_cls}">'
                f'<div class="date-num">{d}</div>'
                f'<div class="{pill_cls}">{info["day"]} · {hrs}hr{"s" if hrs > 1 else ""}</div>'
                f'</div>'
            )
        else:
            is_weekend = (dow == 0 or dow == 6)
            cell_cls   = "cal-cell" + (" empty" if is_weekend else "")
            cells += f'<div class="{cell_cls}"><div class="date-num">{d}</div></div>'
    remainder = (first_dow_sun + days_in_month) % 7
    if remainder:
        cells += "".join(['<div class="cal-cell empty"></div>'] * (7 - remainder))
    return f"""
    <div class="cal-wrap">
        <div class="cal-header">
            <span class="cal-month">{calendar.month_name[month]} {year}</span>
            <div class="cal-legend">
                <div class="legend-item"><div class="legend-dot" style="background:#fff;border:1px solid rgba(255,255,255,0.3)"></div>Match day</div>
                <div class="legend-item"><div class="legend-dot" style="background:rgba(255,255,255,0.25)"></div>Excluded</div>
            </div>
        </div>
        <div class="day-headers">{headers}</div>
        <div class="cal-grid">{cells}</div>
    </div>"""

def generate_jpg(results_df, month_name, year, currency,
                 total_court, total_shuttle, grand_total, avg):
    s      = currency
    ROW_H  = 36
    HEAD_H = 100
    SUMM_H = 80
    FOOT_H = 50
    W      = 900
    H      = HEAD_H + SUMM_H + (len(results_df) + 2) * ROW_H + 60 + FOOT_H
    img    = Image.new("RGB", (W, H), color=(244, 246, 249))
    draw   = ImageDraw.Draw(img)

    def load_fonts():
        for bold, reg in [
            ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]:
            try:
                return (ImageFont.truetype(bold, 22), ImageFont.truetype(bold, 14),
                        ImageFont.truetype(reg,  13), ImageFont.truetype(reg,  11))
            except Exception:
                continue
        d = ImageFont.load_default()
        return d, d, d, d

    font_t, font_b, font_sm, font_xs = load_fonts()

    draw.rectangle([0, 0, W, HEAD_H], fill=(27, 42, 74))
    draw.text((W//2, 30), "Badminton Fee Report",                  font=font_t,  fill="white",       anchor="mm")
    draw.text((W//2, 58), f"{month_name} {year}  |  {s}",         font=font_sm, fill=(150,180,220), anchor="mm")
    draw.text((W//2, 80), f"Grand Total: {s} {grand_total:,.2f}", font=font_b,  fill=(255,220,100), anchor="mm")

    y      = HEAD_H + 12
    card_w = (W - 60) // 4
    for i, (lbl, val, fill) in enumerate([
        ("Court Cost",   f"{s} {total_court:,.2f}",   (238,243,255)),
        ("Shuttle Cost", f"{s} {total_shuttle:,.2f}",  (238,243,255)),
        ("Avg / Player", f"{s} {avg:,.2f}",            (238,243,255)),
        ("Grand Total",  f"{s} {grand_total:,.2f}",    (197,211,245)),
    ]):
        cx = 15 + i * (card_w + 15)
        draw.rounded_rectangle([cx, y, cx + card_w, y + 56], radius=8, fill=fill)
        draw.text((cx + card_w//2, y + 16), lbl, font=font_xs, fill=(100,120,160), anchor="mm")
        draw.text((cx + card_w//2, y + 38), val, font=font_b,  fill=(27,42,74),   anchor="mm")

    y      = HEAD_H + SUMM_H + 10
    cols   = ["#","Player","Sessions","Hours",f"Court ({s})",f"Shuttle ({s})",f"Total ({s})"]
    widths = [40, 190, 100, 90, 120, 120, 120]
    xs     = [15]
    for w in widths[:-1]: xs.append(xs[-1] + w)

    draw.rectangle([15, y, W-15, y+ROW_H], fill=(27,42,74))
    for col, x, w in zip(cols, xs, widths):
        draw.text((x+w//2, y+ROW_H//2), col, font=font_xs, fill="white", anchor="mm")
    y += ROW_H

    for i, (_, row) in enumerate(results_df.iterrows()):
        fill = (245,247,252) if i % 2 == 0 else (255,255,255)
        draw.rectangle([15, y, W-15, y+ROW_H], fill=fill)
        for v, x, w in zip([str(i+1), str(row["Player"]), str(row["Sessions"]),
            str(row["Hours"]), f"{row['Court Fee']:.2f}",
            f"{row['Shuttle Fee']:.2f}", f"{row['Total']:.2f}"], xs, widths):
            draw.text((x+w//2, y+ROW_H//2), v, font=font_sm, fill=(27,42,74), anchor="mm")
        y += ROW_H

    draw.rectangle([15, y, W-15, y+ROW_H], fill=(27,42,74))
    for v, x, w in zip(["","TOTAL",str(int(results_df["Sessions"].sum())),
        str(round(results_df["Hours"].sum(),1)),
        f"{results_df['Court Fee'].sum():.2f}",
        f"{results_df['Shuttle Fee'].sum():.2f}",
        f"{results_df['Total'].sum():.2f}"], xs, widths):
        draw.text((x+w//2, y+ROW_H//2), v, font=font_b, fill="white", anchor="mm")
    y += ROW_H + 20
    draw.text((W//2, y+14), "Generated by BadmintonFee Calculator",
              font=font_xs, fill=(160,160,160), anchor="mm")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.getvalue()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-size:32px;margin-bottom:2px">🏸</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:16px;font-weight:600;color:#fff;margin-bottom:2px">BadmintonFee</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:24px">Court Fee Calculator</p>', unsafe_allow_html=True)

    st.markdown('<p style="font-size:10px;font-weight:700;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">PERIOD</p>', unsafe_allow_html=True)
    year  = st.number_input("Year",  value=2026, min_value=2000, max_value=2100)
    month = st.number_input("Month", value=5,    min_value=1,    max_value=12)

    st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:16px 0">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;font-weight:700;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">COSTS</p>', unsafe_allow_html=True)
    currency      = st.selectbox("Currency", ["AED", "USD", "GBP", "EUR", "MYR", "SGD"])
    cost_per_hour = st.number_input("Court cost / hour", value=55.0, min_value=0.0)
    num_tubes     = st.number_input("Shuttle tubes",     value=3,    min_value=0)
    cost_per_tube = st.number_input("Cost / tube",       value=15.0, min_value=0.0)

    st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:16px 0">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;font-weight:700;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">PLAYERS</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:6px">Type name and press Enter</p>', unsafe_allow_html=True)

    with st.form("add_player_form", clear_on_submit=True):
        new_player = st.text_input("Add player name", placeholder="e.g. Ali", label_visibility="collapsed")
        submitted  = st.form_submit_button("Add")
        if submitted:
            name = new_player.strip()
            if name and name not in st.session_state.player_list:
                st.session_state.player_list.append(name)
                db_set("player_list", st.session_state.player_list)
                st.rerun()
            elif name in st.session_state.player_list:
                st.warning(f"{name} already added.")

    for i, p in enumerate(st.session_state.player_list):
        c1, c2 = st.columns([3, 1])
        c1.markdown(f'<p style="color:#fff;font-size:13px;padding-top:6px;margin:0">👤 {p}</p>', unsafe_allow_html=True)
        if c2.button("✕", key=f"remove_{i}"):
            st.session_state.player_list.pop(i)
            st.session_state.att_state.pop(p, None)
            db_set("player_list", st.session_state.player_list)
            db_set("att_state",   st.session_state.att_state)
            st.rerun()

    if st.session_state.player_list:
        st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:12px 0">', unsafe_allow_html=True)
        if st.button("🗑 Clear All Players"):
            st.session_state.player_list = []
            st.session_state.att_state   = {}
            db_set("player_list", [])
            db_set("att_state",   {})
            st.rerun()

CURRENCY_SYMBOLS = {"AED": "د.إ", "USD": "$", "GBP": "£", "EUR": "€", "MYR": "RM", "SGD": "S$"}
sym = CURRENCY_SYMBOLS.get(currency, currency)

st.markdown(f"""
<div class="page-header">
    <div style="font-size:38px">🏸</div>
    <div>
        <p class="page-header-title">Badminton Fee Calculator</p>
        <p class="page-header-sub">{calendar.month_name[month]} {year} &nbsp;·&nbsp; {currency} &nbsp;·&nbsp; Court {sym}{cost_per_hour:.0f}/hr</p>
    </div>
</div>
""", unsafe_allow_html=True)

all_match_days = get_match_days(year, month, st.session_state.session_hours)

tab1, tab2 = st.tabs(["📅  Schedule & Attendance", "💰  Fee Breakdown"])

with tab1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Match Days</div>', unsafe_allow_html=True)
    st.markdown(
        build_calendar_html(year, month, all_match_days, st.session_state.excluded_sessions),
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    all_labels        = [m["label"] for m in all_match_days]
    excluded_selected = st.multiselect(
        "Exclude match days", options=all_labels,
        default=[s for s in st.session_state.excluded_sessions if s in all_labels],
        placeholder="Select days to exclude..."
    )
    if set(excluded_selected) != st.session_state.excluded_sessions:
        st.session_state.excluded_sessions = set(excluded_selected)
        db_set("excluded_sessions", list(st.session_state.excluded_sessions))

    included_days = [m for m in all_match_days if m["label"] not in st.session_state.excluded_sessions]
    if included_days:
        with st.expander("Adjust hours per session"):
            cols = st.columns(len(included_days))
            for i, m in enumerate(included_days):
                new_hrs = cols[i].number_input(
                    m["label"], value=float(m["hours"]),
                    min_value=0.5, max_value=8.0, step=0.5, key=f"hrs_{m['label']}"
                )
                if new_hrs != st.session_state.session_hours.get(m["label"]):
                    st.session_state.session_hours[m["label"]] = new_hrs
                    db_set("session_hours", st.session_state.session_hours)
    st.markdown('</div>', unsafe_allow_html=True)

    all_match_days = get_match_days(year, month, st.session_state.session_hours)
    included_days  = [m for m in all_match_days if m["label"] not in st.session_state.excluded_sessions]
    total_hours    = sum(m["hours"] for m in included_days)
    total_court    = total_hours * cost_per_hour

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-label">Active Sessions</div>
            <div class="metric-value">{len(included_days)}</div>
            <div class="metric-sub">of {len(all_match_days)} total</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Hours</div>
            <div class="metric-value">{total_hours:.1f}</div>
            <div class="metric-sub">hours on court</div>
        </div>
        <div class="metric-card accent">
            <div class="metric-label">Court Cost</div>
            <div class="metric-value">{sym}{total_court:,.2f}</div>
            <div class="metric-sub">{sym}{cost_per_hour:.0f}/hr × {total_hours:.1f}hrs</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.player_list:
        chips = "".join([f'<span class="player-chip">👤 {p}</span>' for p in st.session_state.player_list])
        st.markdown(
            f'<div class="section-card"><div class="section-title">Players ({len(st.session_state.player_list)})</div>'
            f'<div class="player-chips">{chips}</div></div>',
            unsafe_allow_html=True
        )

    player_list  = st.session_state.player_list
    session_cols = [m["label"] for m in included_days]

    if player_list and included_days:
        att_changed = False
        for p in player_list:
            if p not in st.session_state.att_state:
                st.session_state.att_state[p] = {col: True for col in session_cols}
                att_changed = True
            else:
                for col in session_cols:
                    if col not in st.session_state.att_state[p]:
                        st.session_state.att_state[p][col] = True
                        att_changed = True
        if att_changed:
            db_set("att_state", st.session_state.att_state)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Player Attendance</div>', unsafe_allow_html=True)

        for player in player_list:
            all_selected = all(st.session_state.att_state[player].get(col, True) for col in session_cols)
            attended     = sum(1 for col in session_cols if st.session_state.att_state[player].get(col, True))
            cols = st.columns([1.5] + [1] * len(session_cols))
            cols[0].markdown(
                f'<p style="color:#1B2A4A;font-weight:600;font-size:14px;margin-bottom:4px">'
                f'{player} <span style="color:#7B8DB0;font-weight:400;font-size:12px">{attended}/{len(session_cols)}</span></p>',
                unsafe_allow_html=True
            )
            toggle = cols[0].checkbox("All", value=all_selected, key=f"toggle_{player}")
            if toggle != all_selected:
                for col in session_cols:
                    st.session_state.att_state[player][col] = toggle
                db_set("att_state", st.session_state.att_state)
                st.rerun()

            for i, col in enumerate(session_cols):
                val = cols[i + 1].checkbox(
                    col, value=st.session_state.att_state[player].get(col, True),
                    key=f"att_{player}_{col}"
                )
                if val != st.session_state.att_state[player].get(col, True):
                    st.session_state.att_state[player][col] = val
                    db_set("att_state", st.session_state.att_state)
            st.divider()

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("👈 Add players in the sidebar to set attendance.")

with tab2:
    player_list    = st.session_state.player_list
    all_match_days = get_match_days(year, month, st.session_state.session_hours)
    included_days  = [m for m in all_match_days if m["label"] not in st.session_state.excluded_sessions]
    session_cols   = [m["label"] for m in included_days]
    total_hours    = sum(m["hours"] for m in included_days)

    if not player_list or not included_days:
        st.info("👈 Add players and configure sessions in the Schedule tab first.")
    else:
        total_court   = total_hours * cost_per_hour
        total_shuttle = num_tubes * cost_per_tube
        grand_total   = total_court + total_shuttle
        month_name    = calendar.month_name[month]

        results = []
        for player in player_list:
            player_hrs = sum(
                m["hours"] for m in included_days
                if st.session_state.att_state.get(player, {}).get(m["label"], True)
            )
            sessions_attended = sum(
                1 for m in included_days
                if st.session_state.att_state.get(player, {}).get(m["label"], True)
            )
            results.append({
                "Player":     player,
                "Sessions":   sessions_attended,
                "Hours":      round(player_hrs, 1),
                "_hours_raw": player_hrs
            })

        total_player_hours = sum(r["_hours_raw"] for r in results)
        for r in results:
            court_fee   = (r["_hours_raw"] / total_player_hours * total_court) if total_player_hours else 0
            shuttle_fee = total_shuttle / len(results) if results else 0
            r["Court Fee"]   = round(court_fee,   2)
            r["Shuttle Fee"] = round(shuttle_fee, 2)
            r["Total"]       = round(court_fee + shuttle_fee, 2)
            r.pop("_hours_raw")

        results_df = pd.DataFrame(results).sort_values("Player").reset_index(drop=True)
        avg        = grand_total / len(results) if results else 0

        st.markdown(f"""
        <div class="summary-grid">
            <div class="summary-card"><div class="summary-label">Court Cost</div><div class="summary-value">{sym}{total_court:,.2f}</div></div>
            <div class="summary-card"><div class="summary-label">Shuttle Cost</div><div class="summary-value">{sym}{total_shuttle:,.2f}</div></div>
            <div class="summary-card"><div class="summary-label">Avg per Player</div><div class="summary-value">{sym}{avg:,.2f}</div></div>
            <div class="summary-card highlight"><div class="summary-label">Grand Total</div><div class="summary-value">{sym}{grand_total:,.2f}</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Fee Breakdown</div>', unsafe_allow_html=True)

        totals = pd.DataFrame([{
            "Player":      "TOTAL",
            "Sessions":    results_df["Sessions"].sum(),
            "Hours":       round(results_df["Hours"].sum(), 1),
            "Court Fee":   round(results_df["Court Fee"].sum(), 2),
            "Shuttle Fee": round(results_df["Shuttle Fee"].sum(), 2),
            "Total":       round(results_df["Total"].sum(), 2),
        }])
        display_df = pd.concat([results_df, totals], ignore_index=True)
        display_df.index = list(range(1, len(results_df) + 1)) + [""]

        st.dataframe(
            display_df, use_container_width=True,
            column_config={
                "Court Fee":   st.column_config.NumberColumn(f"Court Fee ({sym})",   format="%.2f"),
                "Shuttle Fee": st.column_config.NumberColumn(f"Shuttle Fee ({sym})", format="%.2f"),
                "Total":       st.column_config.NumberColumn(f"Total ({sym})",        format="%.2f"),
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Export & Share ──
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Export & Share</div>', unsafe_allow_html=True)

        csv_bytes = results_df.to_csv(index=False).encode("utf-8")

        xl_buf = BytesIO()
        att_export = pd.DataFrame([
            {"Player": p, **{col: st.session_state.att_state.get(p, {}).get(col, True) for col in session_cols}}
            for p in player_list
        ])
        with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
            results_df.to_excel(writer, index=False, sheet_name="Fees")
            att_export.to_excel(writer, index=False, sheet_name="Attendance")
        xl_bytes = xl_buf.getvalue()

        jpg_bytes = generate_jpg(
            results_df, month_name, year, currency,
            total_court, total_shuttle, grand_total, avg
        )

        col_csv, col_xl, col_jpg = st.columns(3)
        col_csv.download_button(
            "⬇ CSV", csv_bytes, "badminton_fees.csv", "text/csv",
            use_container_width=True
        )
        col_xl.download_button(
            "⬇ Excel", xl_bytes, "badminton_fees.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        col_jpg.download_button(
            "⬇ JPG", jpg_bytes,
            f"badminton_fees_{month_name}_{year}.jpg", "image/jpeg",
            use_container_width=True
        )

        jpg_b64 = base64.b64encode(jpg_bytes).decode()
        wa_text = urllib.parse.quote(
            f"🏸 Badminton Fee Report — {month_name} {year}\n"
            f"Grand Total: {currency} {grand_total:,.2f}\n"
            f"(See attached image for full breakdown)"
        )
        wa_link = f"https://wa.me/?text={wa_text}"

        st.markdown(f"""
        <div style="margin-top:20px">
            <p style="font-size:12px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;
                      color:#7B8DB0;margin-bottom:14px">Share on WhatsApp</p>
            <div style="display:flex;gap:16px;align-items:flex-start">
                <div style="flex:1;min-width:0">
                    <img src="data:image/jpeg;base64,{jpg_b64}"
                         style="width:100%;border-radius:10px;border:1px solid #E8ECF2;display:block"/>
                </div>
                <div style="flex:0 0 170px;display:flex;flex-direction:column;gap:10px;padding-top:4px">
                    <a href="{wa_link}" target="_blank" class="wa-btn">💬 Open WhatsApp</a>
                    <p style="font-size:11px;color:#9BAAC4;text-align:center;margin:0;line-height:1.5">
                        Download the JPG above, then attach it in the WhatsApp chat
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
