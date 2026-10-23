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
