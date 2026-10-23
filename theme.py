"""ChartPilot visual system: flat black + electric purple. No gradients/transitions."""
from __future__ import annotations

CSS = """
<style>
:root {
  --cp-bg:#050408; --cp-panel:#100c19; --cp-panel2:#160f24;
  --cp-line:#39224e; --cp-accent:#a855f7; --cp-accent2:#c084fc;
  --cp-white:#f3ecfc; --cp-muted:#a49ab2;
}
html,body,[data-testid="stAppViewContainer"],.stApp,
[data-testid="stMain"],[data-testid="stHeader"] { background:#050408 !important; color:#f3ecfc !important; }
* { animation:none !important; transition:none !important; scroll-behavior:auto !important; }
[data-testid="stHeader"] { background:transparent !important; }
[data-testid="stSidebar"],[data-testid="stSidebarContent"] { background:#100c19 !important; border-right:1px solid #39224e !important; }
[data-testid="stSidebar"] .stMarkdown p { color:#b8abca; }
[data-testid="stAppViewBlockContainer"] { max-width:1700px; padding:1.6rem 2.5rem 4rem; }
h1,h2,h3,p,label,span { font-family:Inter,Arial,sans-serif; }
h1 {font-size:2.55rem !important;font-weight:900 !important;letter-spacing:-.05em !important;}
h2 {font-size:1.42rem !important;font-weight:800 !important;letter-spacing:-.035em !important;}
h3 {font-size:1.1rem !important;font-weight:750 !important;}
[data-testid="stMetric"] { background:#100c19 !important;border:1px solid #39224e !important;border-radius:0 !important;padding:1.05rem 1.2rem !important; }
[data-testid="stMetricLabel"] p {color:#a49ab2 !important;font-size:.78rem !important;letter-spacing:.04em;text-transform:uppercase;}
[data-testid="stMetricValue"] {color:#f3ecfc !important;}
[data-testid="stVerticalBlockBorderWrapper"] > div, div[data-testid="stExpander"] {border-radius:0 !important;}
[data-testid="stExpander"] {background:#100c19 !important;border:1px solid #39224e !important;}
[data-baseweb="tab-list"] {gap:0 !important;border-bottom:1px solid #39224e !important;}
button[data-baseweb="tab"] {background:#100c19 !important;color:#b8abca !important;border-radius:0 !important;margin:0 6px 0 0 !important;border:1px solid #39224e !important;border-bottom:0 !important;padding:12px 18px !important;}
button[data-baseweb="tab"][aria-selected="true"] {background:#8b3fe2 !important;color:white !important;}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"] {display:none !important;}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"] {background:#9e47f5 !important;color:#07030e !important;border:2px solid #9e47f5 !important;border-radius:0 !important;font-weight:900 !important;}
.stButton button[kind="secondary"],.stDownloadButton button {background:#1b102b !important;color:#f3ecfc !important;border:1px solid #7243a4 !important;border-radius:0 !important;}
button, [data-baseweb="select"] > div, input, textarea, [data-testid="stFileUploaderDropzone"] {border-radius:0 !important;}
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {background:#170f24 !important;border:1px solid #553278 !important;}
[data-testid="stFileUploaderDropzone"] {background:#130c1e !important;border:1px dashed #8551b7 !important;}
[data-testid="stFileUploaderDropzone"] button {background:#9e47f5 !important;color:#0a0610 !important;border-radius:0 !important;}
hr {border-color:#39224e !important;}
[data-testid="stAlert"] {border-radius:0 !important;border:1px solid #54377a !important;}
[data-testid="stDataFrame"] {border:1px solid #39224e !important;}
.cp-eyebrow {text-transform:uppercase;font-weight:850;letter-spacing:.18em;font-size:.75rem;color:#b77dff;margin:0 0 .4rem;}
.cp-title {font-size:2.85rem;font-weight:950;letter-spacing:-.06em;line-height:1.1;margin:0;color:#faf4ff;}
.cp-lead {color:#baafc9;font-size:1rem;margin:.6rem 0 1.4rem;}
.cp-rule {height:3px;background:#a855f7;border:0;margin:1.3rem 0;}
.cp-slab {background:#100c19;border:1px solid #39224e;padding:1.1rem 1.3rem;margin:.2rem 0 1rem;}
.cp-kicker {text-transform:uppercase;letter-spacing:.14em;font-size:.72rem;font-weight:850;color:#c084fc;}
.cp-brand {font-size:1.55rem;font-weight:950;letter-spacing:-.035em;color:#f3ecfc;}
.cp-brand b {color:#b568ff;}
.cp-pill {display:inline-block;background:#231335;border:1px solid #8150b5;color:#e4c9ff;font-weight:800;font-size:.74rem;letter-spacing:.05em;padding:5px 10px;margin-right:6px;}
.cp-strip {background:#180e28;border-left:4px solid #aa58ff;color:#dcc7ef;padding:.85rem 1rem;margin:1rem 0;}
.cp-signal {background:#170f25;border:2px solid #a855f7;padding:1.1rem 1.4rem;margin:.45rem 0 1rem;}
.cp-signal strong {font-size:2.2rem;letter-spacing:-.045em;color:#f7edff;}
.cp-tiny {font-size:.76rem;color:#a79ab8;}
.cp-footer {font-size:.77rem;color:#8b809e;border-top:1px solid #39224e;padding-top:1rem;margin-top:2.3rem;}

/* === SIDEBAR / V2.1 — dedicated editorial navigation, flat colors only === */
[data-testid="stSidebar"] {
  background:#08060d !important;
  border-right:2px solid #43235c !important;
}
[data-testid="stSidebarContent"] {
  background:#08060d !important;
  padding:0 0.85rem 1.4rem !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  gap:0.38rem !important;
}
.cp-sidebar-brand {
  padding:1.25rem 0.25rem 1.05rem;
  border-bottom:1px solid #342142;
  margin-bottom:0.8rem;
}
.cp-sidebar-brand-row {display:flex;align-items:center;gap:0.9rem;}
.cp-sidebar-monogram {
  width:48px;height:48px;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;color:#f8edff;background:#301449;border:1px solid #9853eb;
  font-weight:950;font-size:1.2rem;letter-spacing:-.1em;position:relative;
}
.cp-sidebar-monogram span {
  position:absolute;right:-5px;top:-7px;background:#ac66f5;color:#08050c;
  border:2px solid #08060d;font-size:.55rem;line-height:1;padding:3px;
}
.cp-sidebar-name {
  color:#f5edff;font-size:1.36rem;font-weight:950;line-height:1.1;
  white-space:nowrap;letter-spacing:-.065em;
}
.cp-sidebar-name span {color:#bf80ff;}
.cp-sidebar-tagline {
  color:#8d7f9b;font-size:.62rem;letter-spacing:.10em;font-weight:750;margin-top:0.38rem;
}
.cp-sidebar-version {
  margin-top:1.1rem;color:#d0b0ef;font-size:.68rem;font-weight:850;
  letter-spacing:.05em;display:flex;align-items:center;gap:.42rem;
}
.cp-version-right {margin-left:auto;color:#827289;font-size:.61rem;}
.cp-status-dot {
  display:inline-block;vertical-align:middle;width:7px;height:7px;
  flex-shrink:0;background:#a855f7;border:1px solid #d1a9fa;
}
.cp-status-inactive {background:#594e60;border-color:#817086;}
.cp-side-section {
  display:flex;align-items:center;gap:.58rem;
  color:#b7a3c9;font-weight:900;letter-spacing:.14em;font-size:.67rem;
  margin:1.05rem .24rem .48rem;
  padding-bottom:.5rem;border-bottom:1px solid #25192f;
}
.cp-side-section-number {color:#be79f5;font-size:.65rem;}
.cp-side-section-market {margin-top:1.1rem;}
.cp-side-section-status {margin-top:1.05rem;}
/* Navigation uses real buttons: no browser radio dots, no fragile radio selectors. */
[data-testid="stSidebar"] .st-key-cp_navigation [data-testid="stVerticalBlock"] {
  gap:.20rem !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation .stButton {
  margin:0 !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button,
[data-testid="stSidebar"] [data-testid="stButton"] button[id^="cp_nav_"] {
  width:100% !important;
  min-height:43px !important;
  padding:.64rem .83rem !important;
  display:flex !important;
  justify-content:flex-start !important;
  text-align:left !important;
  border-radius:0 !important;
  box-shadow:none !important;
  background:#100a18 !important;
  color:#c9bdd5 !important;
  border:1px solid #26182f !important;
  border-left:3px solid transparent !important;
  font-size:.79rem !important;
  font-weight:830 !important;
  letter-spacing:.025em !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button p,
[data-testid="stSidebar"] .st-key-cp_navigation button span {
  font-size:.79rem !important;
  font-weight:830 !important;
  color:inherit !important;
  line-height:1.25 !important;
  white-space:normal !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button:hover {
  background:#1e102e !important;
  color:#fbf4ff !important;
  border-color:#68408c !important;
  border-left-color:#8452ad !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button[kind="primary"],
[data-testid="stSidebar"] .st-key-cp_navigation button[data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] .st-key-cp_navigation button[data-testid="stBaseButton-primaryFormSubmit"] {
  background:#2a123f !important;
  border:1px solid #7843a3 !important;
  border-left:4px solid #c475ff !important;
  color:#faf0ff !important;
  font-weight:900 !important;
  padding-left:.76rem !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button[kind="primary"]:hover,
[data-testid="stSidebar"] .st-key-cp_navigation button[data-testid="stBaseButton-primary"]:hover {
  background:#32164b !important;
  border-left-color:#d79aff !important;
}
[data-testid="stSidebar"] .st-key-cp_navigation button:focus-visible {
  outline:2px solid #dba5ff !important;
  outline-offset:2px !important;
}
/* Market controls are a distinct and quieter control surface. */
:is(.st-key-cp_market_controls,[data-testid="st-key-cp_market_controls"]) {
  background:#100a18 !important;border:1px solid #30203e !important;
  border-top:2px solid #63348e !important;padding:.75rem .72rem .85rem !important;
}
:is(.st-key-cp_market_controls,[data-testid="st-key-cp_market_controls"]) [data-testid="stWidgetLabel"] p {
  font-size:.65rem !important;font-weight:850 !important;color:#a48db9 !important;
  letter-spacing:.10em !important;
}
:is(.st-key-cp_market_controls,[data-testid="st-key-cp_market_controls"]) [data-baseweb="select"] > div {
  background:#1a1027 !important;border:1px solid #4e3069 !important;
  min-height:36px !important;color:#e9dcf6 !important;font-size:.77rem !important;
}
:is(.st-key-cp_market_controls,[data-testid="st-key-cp_market_controls"]) [data-testid="stVerticalBlock"] {
  gap:.3rem !important;
}
.cp-side-status-card {
  background:#120b1a;border:1px solid #38234b;padding:.85rem .82rem .73rem;
}
.cp-side-status-title {
  font-size:.62rem;font-weight:900;letter-spacing:.095em;color:#bd94dc;
  display:flex;align-items:center;gap:.5rem;margin:0 0 .55rem;
}
.cp-side-status-main {color:#f5edff;font-weight:850;font-size:.82rem;line-height:1.25;overflow-wrap:anywhere;}
.cp-side-status-sub {color:#9585a7;font-size:.72rem;line-height:1.4;overflow-wrap:anywhere;margin:.26rem 0 .7rem;}
.cp-side-status-bottom {
  border-top:1px solid #2c1d39;padding-top:.62rem;
  font-size:.65rem;font-weight:700;letter-spacing:.04em;color:#9d8bab;
  display:flex;justify-content:space-between;
}
.cp-side-status-bottom b {color:#e5ccf8;}
.cp-side-footer {
  margin:1.15rem .1rem .55rem;padding:.82rem .65rem 0;
  border-top:1px solid #342043;color:#83738f;font-size:.67rem;line-height:1.45;
}
.cp-side-footer-line {
  display:flex;justify-content:space-between;align-items:center;
  font-size:.63rem;letter-spacing:.06em;font-weight:850;color:#977eaa;margin-bottom:.5rem;
}
.cp-side-footer-line strong {color:#c596f2;}

@media(max-width:900px) {
 [data-testid="stAppViewBlockContainer"]{padding:1rem 1rem 3rem;}
 h1,.cp-title {font-size:2rem !important;}
 button[data-baseweb="tab"] {padding:9px 8px !important;font-size:.77rem;}
}
</style>
"""

def apply_theme(st):
    st.markdown(CSS, unsafe_allow_html=True)

def label(st, eyebrow: str, title: str, lead: str = ""):
    from html import escape
    st.markdown(
        '<div class="cp-eyebrow">'+escape(eyebrow)+'</div>'
        '<div class="cp-title">'+escape(title)+'</div>'
        '<div class="cp-lead">'+escape(lead)+'</div>',
        unsafe_allow_html=True
    )
