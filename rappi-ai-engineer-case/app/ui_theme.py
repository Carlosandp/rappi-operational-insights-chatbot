"""
ui_theme.py — Design tokens and CSS injection for Rappi Ops Analytics.
Supports light and dark palettes explicitly — never depends on Streamlit defaults.
"""

import streamlit as st

# ── Design token palettes ─────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg":            "#F8FAFC",
        "surface":       "#FFFFFF",
        "surface_alt":   "#F1F5F9",
        "text":          "#0F172A",
        "text_muted":    "#475569",
        "border":        "#CBD5E1",
        "primary":       "#FF5A3D",
        "primary_hover": "#EA580C",
        "success":       "#16A34A",
        "warning_bg":    "#FEF3C7",
        "warning_text":  "#92400E",
        "error_bg":      "#FEE2E2",
        "error_text":    "#991B1B",
        "chip_bg":       "#EFF6FF",
        "chip_text":     "#1D4ED8",
        "chip_intent_bg":"#F5F3FF",
        "chip_intent_tx":"#6D28D9",
        "user_bubble":   "#EFF6FF",
        "user_bubble_tx":"#1E3A8A",
        "bot_bubble":    "#FFFFFF",
        "bot_bubble_tx": "#111827",
        "sidebar_bg":    "#1E293B",
        "sidebar_text":  "#F8FAFC",
        "plot_bg":       "#FFFFFF",
        "plot_paper":    "rgba(0,0,0,0)",
        "axis_color":    "#475569",
        "grid_color":    "#E2E8F0",
    },
    "dark": {
        "bg":            "#0F172A",
        "surface":       "#1E293B",
        "surface_alt":   "#111827",
        "text":          "#F8FAFC",
        "text_muted":    "#CBD5E1",
        "border":        "#334155",
        "primary":       "#FF5A3D",
        "primary_hover": "#FB923C",
        "success":       "#22C55E",
        "warning_bg":    "#FEF3C7",
        "warning_text":  "#92400E",
        "error_bg":      "#FEE2E2",
        "error_text":    "#991B1B",
        "chip_bg":       "#1E3A5F",
        "chip_text":     "#93C5FD",
        "chip_intent_bg":"#3B1F4E",
        "chip_intent_tx":"#C084FC",
        "user_bubble":   "#1E3A5F",
        "user_bubble_tx":"#E0F2FE",
        "bot_bubble":    "#1E293B",
        "bot_bubble_tx": "#F1F5F9",
        "sidebar_bg":    "#0F172A",
        "sidebar_text":  "#F8FAFC",
        "plot_bg":       "rgba(0,0,0,0)",
        "plot_paper":    "rgba(0,0,0,0)",
        "axis_color":    "#CBD5E1",
        "grid_color":    "#334155",
    },
}

# Default to dark — matches the product aesthetic
DEFAULT_MODE = "dark"


def get_tokens(mode: str = DEFAULT_MODE) -> dict:
    return THEMES.get(mode, THEMES[DEFAULT_MODE])


def inject_css(t: dict):
    """Inject full CSS palette. Every component has explicit colors — no Streamlit defaults."""
    st.markdown(f"""
<style>
/* ── App background ───────────────────────── */
.stApp, .main {{
  background: {t['bg']} !important;
  color: {t['text']} !important;
}}

/* ── Sidebar ──────────────────────────────── */
[data-testid="stSidebar"] {{
  background: {t['sidebar_bg']} !important;
}}
[data-testid="stSidebar"],
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
  color: {t['sidebar_text']} !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div {{
  background: rgba(255,255,255,0.08) !important;
  color: {t['sidebar_text']} !important;
  border-color: rgba(255,255,255,0.15) !important;
}}

/* ── Tabs ─────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
  background: {t['surface']} !important;
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
  border: 1px solid {t['border']};
}}
.stTabs [data-baseweb="tab"] {{
  color: {t['text_muted']} !important;
  background: transparent !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  padding: 8px 20px !important;
  transition: all 0.2s !important;
}}
.stTabs [aria-selected="true"] {{
  background: {t['primary']} !important;
  color: white !important;
}}

/* ── Buttons ──────────────────────────────── */
.stButton > button[kind="primary"] {{
  background: {t['primary']} !important;
  color: white !important;
  border: 1px solid {t['primary']} !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  padding: 8px 20px !important;
  transition: all 0.15s !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: {t['primary_hover']} !important;
  border-color: {t['primary_hover']} !important;
  box-shadow: 0 4px 12px rgba(255, 90, 61, 0.35) !important;
}}
.stButton > button[kind="secondary"] {{
  background: {t['surface']} !important;
  color: {t['text']} !important;
  border: 1.5px solid {t['border']} !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  padding: 7px 16px !important;
  transition: all 0.15s !important;
  cursor: pointer !important;
}}
.stButton > button[kind="secondary"]:hover {{
  background: {t['surface_alt']} !important;
  color: {t['primary']} !important;
  border-color: {t['primary']} !important;
  box-shadow: 0 2px 8px rgba(255, 90, 61, 0.15) !important;
}}

/* ── Text input ───────────────────────────── */
.stTextInput > div > div > input {{
  background: {t['surface']} !important;
  color: {t['text']} !important;
  border: 1.5px solid {t['border']} !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
  font-size: 0.95rem !important;
}}
.stTextInput > div > div > input:focus {{
  border-color: {t['primary']} !important;
  box-shadow: 0 0 0 3px rgba(255, 90, 61, 0.12) !important;
}}
.stTextInput > div > div > input::placeholder {{
  color: {t['text_muted']} !important;
}}

/* ── Expanders ────────────────────────────── */
.stExpander {{
  border: 1px solid {t['border']} !important;
  border-radius: 10px !important;
  background: {t['surface']} !important;
  margin-bottom: 8px !important;
}}
[data-testid="stExpander"] summary {{
  color: {t['text']} !important;
  font-weight: 600 !important;
  padding: 10px 14px !important;
}}
[data-testid="stExpanderDetails"] {{
  background: {t['surface']} !important;
  color: {t['text']} !important;
}}

/* ── Metrics (stat cards) ─────────────────── */
[data-testid="metric-container"] {{
  background: {t['surface']} !important;
  border: 1px solid {t['border']} !important;
  border-radius: 10px !important;
  padding: 12px !important;
}}
[data-testid="metric-container"] * {{
  color: {t['text']} !important;
}}
[data-testid="stMetricValue"] {{
  color: {t['primary']} !important;
  font-weight: 800 !important;
}}

/* ── Dataframe ────────────────────────────── */
[data-testid="stDataFrame"] {{
  border: 1px solid {t['border']} !important;
  border-radius: 8px !important;
}}

/* ── Select / multiselect ─────────────────── */
.stSelectbox > div > div,
.stMultiSelect > div > div {{
  background: {t['surface']} !important;
  color: {t['text']} !important;
  border-color: {t['border']} !important;
}}

/* ── Chat bubbles ─────────────────────────── */
.chat-user {{
  background: {t['user_bubble']} !important;
  border-left: 4px solid {t['primary']};
  padding: 14px 18px;
  border-radius: 0 10px 10px 0;
  margin-bottom: 6px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}
.chat-user, .chat-user *, .chat-user b {{
  color: {t['user_bubble_tx']} !important;
}}
.chat-bot {{
  background: {t['bot_bubble']} !important;
  border-left: 4px solid #3B82F6;
  padding: 14px 18px;
  border-radius: 0 10px 10px 0;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.chat-bot, .chat-bot *, .chat-bot b {{
  color: {t['bot_bubble_tx']} !important;
}}

/* ── Filter chips ─────────────────────────── */
.filter-chip {{
  display: inline-block;
  background: {t['chip_bg']};
  color: {t['chip_text']} !important;
  border: 1px solid {t['chip_text']}40;
  border-radius: 20px;
  padding: 2px 11px;
  font-size: 0.76rem;
  margin: 2px 3px 2px 0;
  font-weight: 600;
}}
.filter-chip.intent {{
  background: {t['chip_intent_bg']};
  color: {t['chip_intent_tx']} !important;
  border-color: {t['chip_intent_tx']}40;
}}

/* ── Trace bar ────────────────────────────── */
.trace-bar {{
  background: {t['surface_alt']};
  border: 1px solid {t['border']};
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 0.76rem;
  color: {t['text_muted']} !important;
  margin: 4px 0 8px;
}}
.trace-bar * {{ color: {t['text_muted']} !important; }}

/* ── Status bar ───────────────────────────── */
.status-bar {{
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: 10px;
  padding: 9px 18px;
  font-size: 0.78rem;
  display: flex;
  gap: 22px;
  align-items: center;
  margin-bottom: 18px;
  color: {t['text_muted']};
}}
.s-ok   {{ color: {t['success']} !important; font-weight: 700; }}
.s-warn {{ color: #FBBF24 !important; font-weight: 700; }}

/* ── Warning box ──────────────────────────── */
.trivial-warning {{
  background: {t['warning_bg']};
  border-left: 4px solid #F59E0B;
  padding: 8px 14px;
  border-radius: 0 8px 8px 0;
  font-size: 0.84rem;
  margin-bottom: 10px;
}}
.trivial-warning, .trivial-warning * {{ color: {t['warning_text']} !important; }}

/* ── Insight cards ────────────────────────── */
.insight-card {{
  background: {t['bot_bubble']};
  border-radius: 0 10px 10px 0;
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}}
.insight-card, .insight-card * {{ color: {t['bot_bubble_tx']} !important; }}
.insight-cat   {{ font-size: 0.78rem; font-weight: 700; margin-bottom: 4px; }}
.insight-title {{ font-weight: 700; font-size: 0.97rem; margin-bottom: 8px; }}
.insight-field {{ font-size: 0.87rem; margin-bottom: 5px; }}

/* ── Suggestions label ────────────────────── */
.sug-label {{
  font-size: 0.82rem;
  font-weight: 600;
  color: {t['text_muted']} !important;
  margin: 10px 0 4px;
}}

/* ── Section headers ──────────────────────── */
h1, h2, h3, h4 {{ color: {t['text']} !important; }}
p, li, span {{ color: {t['text']} !important; }}
.stCaption {{ color: {t['text_muted']} !important; }}

/* ── Radio ────────────────────────────────── */
.stRadio label {{ color: {t['text']} !important; }}
.stRadio div   {{ color: {t['text']} !important; }}

/* ── Checkbox ─────────────────────────────── */
.stCheckbox label {{ color: {t['text']} !important; }}

/* ── Download button ──────────────────────── */
[data-testid="stDownloadButton"] > button {{
  background: {t['surface']} !important;
  color: {t['text']} !important;
  border: 1.5px solid {t['border']} !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}}
[data-testid="stDownloadButton"] > button:hover {{
  border-color: {t['primary']} !important;
  color: {t['primary']} !important;
}}
</style>
""", unsafe_allow_html=True)


def apply_plotly_theme(fig, t: dict):
    """Apply palette tokens to a Plotly figure — call after building every chart."""
    fig.update_layout(
        paper_bgcolor=t["plot_paper"],
        plot_bgcolor=t["plot_bg"],
        font=dict(family="Inter, sans-serif", size=12, color=t["text"]),
        title_font_color=t["text"],
        legend=dict(font=dict(color=t["text"]), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(color=t["axis_color"], gridcolor=t["grid_color"],
                   linecolor=t["border"], zerolinecolor=t["border"]),
        yaxis=dict(color=t["axis_color"], gridcolor=t["grid_color"],
                   linecolor=t["border"], zerolinecolor=t["border"]),
    )
    return fig
