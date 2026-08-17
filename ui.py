
from __future__ import annotations

import html
from typing import Iterable, Sequence

import plotly.graph_objects as go
import streamlit as st


# ---- Design tokens ---------------------------------------------------------

COLORS = {
    # “国科蓝系”视觉语言：以孔雀蓝/科研蓝为品牌轴，
    # 不是复制学校官网，而是用于专业科研工作台的低饱和延展。
    "ink": "#132A43",
    "muted": "#5B6D82",
    "primary": "#1359A6",
    "primary2": "#2F73C9",
    "cyan": "#0E9AA7",
    "teal": "#16877F",
    "orange": "#D9852F",
    "red": "#C65353",
    "violet": "#6B63B5",
    "green": "#3C8C6E",
    "line": "#D7E0E9",
    "soft": "#F3F6F8",
    "surface": "#FFFFFF",
    "dark": "#102A43",
    "dark2": "#153B63",
}


def apply_theme():
    st.markdown(
        f"""
<style>
:root {{
    --kdp-ink: {COLORS["ink"]};
    --kdp-muted: {COLORS["muted"]};
    --kdp-primary: {COLORS["primary"]};
    --kdp-cyan: {COLORS["cyan"]};
    --kdp-line: {COLORS["line"]};
    --kdp-surface: {COLORS["surface"]};
    --kdp-soft: {COLORS["soft"]};
    --kdp-dark: {COLORS["dark"]};
}}

html, body, [class*="css"] {{
    font-family: Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}}

.stApp {{
    background:
        radial-gradient(circle at 80% 0%, rgba(91,91,214,.055), transparent 30rem),
        radial-gradient(circle at 8% 42%, rgba(25,182,201,.04), transparent 28rem),
        #F6F8FC;
    color: var(--kdp-ink);
}}

.block-container {{
    max-width: 1540px;
    padding-top: 2.15rem;
    padding-bottom: 4rem;
}}

header[data-testid="stHeader"] {{
    background: rgba(246,248,252,.72);
    backdrop-filter: blur(16px);
}}

[data-testid="stToolbar"] {{
    opacity: .82;
}}

section[data-testid="stSidebar"] {{
    background:
        radial-gradient(circle at 25% 8%, rgba(91,91,214,.22), transparent 14rem),
        linear-gradient(180deg, #0B1220 0%, #101C2F 100%);
    border-right: 1px solid rgba(255,255,255,.07);
}}

section[data-testid="stSidebar"] * {{
    color: #EAF0F8;
}}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: #B9C5D6;
}}

section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,.08);
}}

section[data-testid="stSidebar"] a {{
    border-radius: 11px !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    margin: 2px 4px;
    padding-top: 8px;
    padding-bottom: 8px;
    transition: all .18s ease;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: rgba(255,255,255,.065);
    transform: translateX(2px);
}}

section[data-testid="stSidebar"] [aria-current="page"] {{
    background: linear-gradient(90deg, rgba(91,91,214,.36), rgba(25,182,201,.10)) !important;
    box-shadow: inset 3px 0 0 #7C7CFF;
}}

section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {{
    color: #7889A1 !important;
    font-size: 11px !important;
    letter-spacing: .12em;
    text-transform: uppercase;
    padding-top: 16px;
}}

h1, h2, h3 {{
    color: var(--kdp-ink);
    letter-spacing: -.025em;
}}

h1 {{
    font-size: 2.15rem !important;
    font-weight: 760 !important;
}}

h2 {{
    font-size: 1.45rem !important;
    font-weight: 720 !important;
}}

h3 {{
    font-size: 1.1rem !important;
    font-weight: 700 !important;
}}

p, label, .stCaption {{
    color: var(--kdp-muted);
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid rgba(213,222,235,.92) !important;
    border-radius: 18px !important;
    background: rgba(255,255,255,.88) !important;
    box-shadow: 0 12px 30px rgba(20,32,51,.045);
}}

div[data-testid="stForm"] {{
    border: 1px solid rgba(213,222,235,.92);
    border-radius: 18px;
    background: rgba(255,255,255,.9);
    padding: 1rem;
}}

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {{
    background: rgba(255,255,255,.96) !important;
    border-color: #D8E1EE !important;
    border-radius: 12px !important;
    min-height: 44px;
    box-shadow: none !important;
}}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {{
    border-color: #7777E8 !important;
    box-shadow: 0 0 0 3px rgba(91,91,214,.10) !important;
}}

.stButton > button,
.stDownloadButton > button {{
    border-radius: 11px !important;
    border: 1px solid #D7DFEB !important;
    min-height: 42px;
    font-weight: 650 !important;
    transition: all .18s ease;
    box-shadow: none !important;
}}

.stButton > button:hover,
.stDownloadButton > button:hover {{
    transform: translateY(-1px);
    border-color: #A9B3C4 !important;
    box-shadow: 0 8px 22px rgba(20,32,51,.07) !important;
}}

.stButton > button[kind="primary"] {{
    color: white !important;
    border: none !important;
    background: linear-gradient(135deg, #5656D6 0%, #6D5EF7 54%, #28A8C7 140%) !important;
    box-shadow: 0 9px 22px rgba(91,91,214,.22) !important;
}}

.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 12px 28px rgba(91,91,214,.28) !important;
}}

button[data-baseweb="tab"] {{
    border-radius: 10px 10px 0 0;
    font-weight: 650;
    color: #738198;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    color: #4646BE !important;
}}

div[data-testid="stDataFrame"] {{
    border: 1px solid #DFE6EF;
    border-radius: 15px;
    overflow: hidden;
    background: white;
    box-shadow: 0 9px 26px rgba(20,32,51,.035);
}}

[data-testid="stAlert"] {{
    border-radius: 14px;
    border: 1px solid rgba(217,225,237,.85);
}}

[data-testid="stStatusWidget"] {{
    border-radius: 15px;
}}

.kdp-brand {{
    padding: 16px 12px 9px 12px;
    margin-bottom: 5px;
}}

.kdp-brand-mark {{
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border-radius: 11px;
    color: white;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: .04em;
    background:
        linear-gradient(145deg, rgba(124,124,255,.95), rgba(37,178,202,.9));
    box-shadow: 0 10px 26px rgba(91,91,214,.28);
    margin-bottom: 12px;
}}

.kdp-brand-title {{
    color: #F4F7FB;
    font-size: 15px;
    font-weight: 730;
    letter-spacing: .01em;
}}

.kdp-brand-sub {{
    color: #8394AC;
    font-size: 11px;
    line-height: 1.6;
    margin-top: 4px;
}}

.kdp-ai-badge {{
    margin: 12px 8px 8px 8px;
    border: 1px solid rgba(255,255,255,.085);
    border-radius: 12px;
    padding: 10px 11px;
    background: rgba(255,255,255,.035);
}}

.kdp-dot {{
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #58D6A7;
    box-shadow: 0 0 0 4px rgba(88,214,167,.08);
    margin-right: 8px;
}}

.kdp-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 10px;
    font-weight: 760;
    letter-spacing: .16em;
    text-transform: uppercase;
    color: #5C64C7;
    background: rgba(91,91,214,.075);
    border: 1px solid rgba(91,91,214,.11);
    border-radius: 999px;
    padding: 6px 10px;
    margin-bottom: 12px;
}}

.kdp-hero {{
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(211,220,233,.82);
    border-radius: 22px;
    padding: 25px 28px 24px 28px;
    margin-bottom: 22px;
    background:
        radial-gradient(circle at 88% 0%, rgba(91,91,214,.105), transparent 22rem),
        radial-gradient(circle at 0% 100%, rgba(25,182,201,.06), transparent 18rem),
        rgba(255,255,255,.91);
    box-shadow:
        0 18px 50px rgba(20,32,51,.055),
        inset 0 1px 0 rgba(255,255,255,.75);
}}

.kdp-hero::after {{
    content: "";
    position: absolute;
    right: -40px;
    top: -70px;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    border: 1px solid rgba(91,91,214,.08);
    box-shadow:
        0 0 0 34px rgba(91,91,214,.025),
        0 0 0 74px rgba(25,182,201,.018);
    pointer-events: none;
}}

.kdp-hero-title {{
    color: #152238;
    font-size: 29px;
    font-weight: 790;
    letter-spacing: -.035em;
    line-height: 1.2;
    position: relative;
    z-index: 1;
}}

.kdp-hero-sub {{
    color: #68778C;
    font-size: 13px;
    line-height: 1.7;
    margin-top: 8px;
    max-width: 900px;
    position: relative;
    z-index: 1;
}}

.kdp-metric-grid {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin: 2px 0 22px 0;
}}

.kdp-metric-card {{
    position: relative;
    overflow: hidden;
    min-height: 104px;
    padding: 16px 17px 14px 17px;
    border-radius: 16px;
    border: 1px solid rgba(215,224,236,.92);
    background: rgba(255,255,255,.93);
    box-shadow: 0 10px 28px rgba(20,32,51,.035);
}}

.kdp-metric-card::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--accent, #5B5BD6);
}}

.kdp-metric-label {{
    font-size: 11px;
    color: #758399;
    font-weight: 650;
    margin-bottom: 8px;
}}

.kdp-metric-value {{
    color: #17243A;
    font-size: 25px;
    font-weight: 780;
    letter-spacing: -.035em;
    line-height: 1;
}}

.kdp-metric-note {{
    color: #8A97AA;
    font-size: 10px;
    line-height: 1.45;
    margin-top: 8px;
}}

.kdp-section-head {{
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 12px;
    margin: 25px 0 11px 0;
}}

.kdp-section-title {{
    color: #17243A;
    font-size: 18px;
    font-weight: 760;
    letter-spacing: -.02em;
}}

.kdp-section-sub {{
    color: #7B889B;
    font-size: 11px;
    line-height: 1.5;
    margin-top: 3px;
}}

.kdp-chain-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin: 4px 0 8px 0;
}}

.kdp-chain-step {{
    position: relative;
    border: 1px solid #DEE6F0;
    border-radius: 15px;
    padding: 14px 15px 13px 15px;
    background: linear-gradient(180deg, #FFFFFF, #FAFBFD);
    min-height: 100px;
}}

.kdp-chain-kicker {{
    color: #8A96A8;
    font-size: 10px;
    font-weight: 760;
    letter-spacing: .11em;
    margin-bottom: 8px;
}}

.kdp-chain-name {{
    color: #1A2940;
    font-size: 14px;
    font-weight: 730;
    margin-bottom: 6px;
}}

.kdp-chain-desc {{
    color: #6F7D91;
    font-size: 10.5px;
    line-height: 1.55;
}}

.kdp-soft-note {{
    border: 1px solid #DDE5F0;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(91,91,214,.055), rgba(25,182,201,.025));
    padding: 12px 14px;
    color: #65758B;
    font-size: 11.5px;
    line-height: 1.65;
    margin: 5px 0 14px 0;
}}

.kdp-mini-card {{
    border: 1px solid #DEE6F0;
    background: rgba(255,255,255,.92);
    border-radius: 14px;
    padding: 13px 14px;
    margin-bottom: 9px;
}}

.kdp-mini-title {{
    color: #1A2940;
    font-size: 12.5px;
    font-weight: 730;
}}

.kdp-mini-text {{
    color: #708096;
    font-size: 10.5px;
    line-height: 1.55;
    margin-top: 5px;
}}

@media (max-width: 1100px) {{
    .kdp-metric-grid {{ grid-template-columns: repeat(3, 1fr); }}
    .kdp-chain-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}

@media (max-width: 720px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    .kdp-metric-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .kdp-chain-grid {{ grid-template-columns: 1fr; }}
    .kdp-hero {{ padding: 21px 20px; }}
    .kdp-hero-title {{ font-size: 24px; }}
}}

/* ========================================================================
   Scholarly Workspace refinement
   ======================================================================== */

:root {{
    --lab-navy: #12233F;
    --lab-blue: #2457D6;
    --lab-blue-2: #2F6BEE;
    --lab-cyan: #0EA5B7;
    --lab-ink: #142033;
    --lab-text: #26364D;
    --lab-muted: #52637A;
    --lab-subtle: #6E7D91;
    --lab-line: #D9E1EA;
    --lab-line-strong: #C9D4E1;
    --lab-bg: #F5F7FA;
    --lab-paper: #FFFFFF;
    --lab-soft-blue: #EEF4FF;
}}

.stApp {{
    background:
        linear-gradient(rgba(18,35,63,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(18,35,63,.018) 1px, transparent 1px),
        #F7F8FA !important;
    background-size: 32px 32px !important;
    color: var(--lab-ink) !important;
}}

.block-container {{
    max-width: 1480px !important;
    padding-top: 1.55rem !important;
    padding-bottom: 4.5rem !important;
    padding-left: 2.2rem !important;
    padding-right: 2.2rem !important;
}}

header[data-testid="stHeader"] {{
    background: rgba(247,248,250,.94) !important;
    border-bottom: 1px solid rgba(217,225,234,.75);
    backdrop-filter: blur(12px);
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFD 100%) !important;
    border-right: 1px solid #DCE3EC !important;
    box-shadow: 8px 0 28px rgba(18,35,63,.025) !important;
}}

section[data-testid="stSidebar"] * {{
    color: #253650 !important;
}}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: #5F6F84 !important;
}}

section[data-testid="stSidebar"] hr {{
    border-color: #E4E9F0 !important;
}}

section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {{
    color: #7C8999 !important;
    font-size: 10.5px !important;
    font-weight: 760 !important;
    letter-spacing: .085em !important;
    text-transform: none !important;
    padding-top: 18px !important;
    padding-bottom: 5px !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    margin: 2px 7px !important;
    padding: 9px 10px !important;
    border-radius: 10px !important;
    transition: background .15s ease, color .15s ease !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: #F0F4FA !important;
    transform: none !important;
}}

section[data-testid="stSidebar"] [aria-current="page"] {{
    background: #EAF1FF !important;
    color: #1747B5 !important;
    box-shadow: inset 3px 0 0 #2F6BEE !important;
}}

section[data-testid="stSidebar"] [aria-current="page"] * {{
    color: #1747B5 !important;
    font-weight: 700 !important;
}}

.kdp-brand {{
    padding: 17px 15px 12px 15px !important;
    margin-bottom: 2px !important;
}}

.kdp-brand-mark {{
    width: 38px !important;
    height: 38px !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    background: #173F96 !important;
    box-shadow: none !important;
    margin-bottom: 11px !important;
    font-size: 12px !important;
}}

.kdp-brand-title {{
    color: #142A4B !important;
    font-size: 15px !important;
    font-weight: 780 !important;
}}

.kdp-brand-sub {{
    color: #758398 !important;
    font-size: 10.5px !important;
    line-height: 1.55 !important;
}}

.kdp-ai-badge {{
    margin: 13px 12px 8px 12px !important;
    border: 1px solid #DDE5EE !important;
    border-radius: 10px !important;
    padding: 10px 11px !important;
    background: #F8FAFD !important;
    box-shadow: none !important;
}}

.kdp-ai-badge * {{
    color: #53647A !important;
}}

.kdp-dot {{
    box-shadow: none !important;
}}

html, body, [class*="css"] {{
    font-family: "Inter", "SF Pro Text", "PingFang SC", "Microsoft YaHei", Arial, sans-serif !important;
}}

h1, h2, h3, h4 {{
    color: #12233F !important;
}}

h1 {{
    font-size: 2.05rem !important;
    font-weight: 780 !important;
    letter-spacing: -.035em !important;
}}

h2 {{
    font-size: 1.42rem !important;
    font-weight: 750 !important;
}}

h3 {{
    font-size: 1.08rem !important;
    font-weight: 720 !important;
}}

p,
[data-testid="stMarkdownContainer"] p,
label,
.stCaption,
[data-testid="stCaptionContainer"] {{
    color: #52637A !important;
    line-height: 1.65 !important;
}}

[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label[data-baseweb="form-control-label"] {{
    color: #31445F !important;
    font-size: 12.5px !important;
    font-weight: 680 !important;
}}

.kdp-hero {{
    border: 1px solid #D7E0EA !important;
    border-radius: 16px !important;
    padding: 23px 26px 22px 26px !important;
    margin-bottom: 20px !important;
    background:
        linear-gradient(90deg, rgba(36,87,214,.035), transparent 45%),
        #FFFFFF !important;
    box-shadow: 0 6px 20px rgba(18,35,63,.035) !important;
}}

.kdp-hero::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 18px;
    bottom: 18px;
    width: 4px;
    border-radius: 0 4px 4px 0;
    background: #2F6BEE;
}}

.kdp-hero::after {{
    width: 220px !important;
    height: 220px !important;
    right: -72px !important;
    top: -94px !important;
    border: 1px solid rgba(36,87,214,.07) !important;
    box-shadow:
        0 0 0 30px rgba(36,87,214,.018),
        0 0 0 65px rgba(14,165,183,.012) !important;
}}

.kdp-eyebrow {{
    color: #3158A7 !important;
    background: #F1F5FC !important;
    border: 1px solid #DFE7F2 !important;
    letter-spacing: .11em !important;
    font-size: 9.5px !important;
    font-weight: 760 !important;
    padding: 5px 9px !important;
    margin-bottom: 10px !important;
}}

.kdp-hero-title {{
    color: #12233F !important;
    font-size: 30px !important;
    font-weight: 800 !important;
    letter-spacing: -.04em !important;
}}

.kdp-hero-sub {{
    color: #56677E !important;
    font-size: 12.5px !important;
    line-height: 1.7 !important;
    max-width: 980px !important;
}}

.kdp-metric-grid {{
    gap: 11px !important;
    margin-bottom: 22px !important;
}}

.kdp-metric-card {{
    min-height: 106px !important;
    padding: 16px 17px 15px 18px !important;
    border-radius: 13px !important;
    border: 1px solid #DAE2EC !important;
    background: #FFFFFF !important;
    box-shadow: 0 4px 15px rgba(18,35,63,.03) !important;
}}

.kdp-metric-label {{
    color: #5E6F84 !important;
    font-size: 11px !important;
    font-weight: 690 !important;
}}

.kdp-metric-value {{
    color: #12233F !important;
    font-size: 26px !important;
    font-weight: 800 !important;
}}

.kdp-metric-note {{
    color: #738196 !important;
    font-size: 10.5px !important;
}}

.kdp-section-title {{
    color: #152A48 !important;
    font-size: 18px !important;
    font-weight: 770 !important;
}}

.kdp-section-sub {{
    color: #66778D !important;
    font-size: 11.5px !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid #D9E1EA !important;
    border-radius: 14px !important;
    background: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(18,35,63,.025) !important;
}}

div[data-testid="stForm"] {{
    border: 1px solid #D9E1EA !important;
    border-radius: 14px !important;
    background: #FFFFFF !important;
    box-shadow: none !important;
}}

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {{
    background: #FFFFFF !important;
    border: 1px solid #CCD7E4 !important;
    border-radius: 9px !important;
    min-height: 43px !important;
    box-shadow: 0 1px 2px rgba(18,35,63,.015) !important;
}}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
input,
textarea {{
    color: #25364E !important;
    font-size: 13px !important;
}}

input::placeholder,
textarea::placeholder {{
    color: #8995A5 !important;
    opacity: 1 !important;
}}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {{
    border-color: #4A72CF !important;
    box-shadow: 0 0 0 3px rgba(47,107,238,.075) !important;
}}

[data-testid="stRadio"] label p,
[data-testid="stCheckbox"] label p {{
    color: #3D4E65 !important;
    font-weight: 560 !important;
}}

.stButton > button,
.stDownloadButton > button {{
    border-radius: 9px !important;
    border: 1px solid #CAD5E2 !important;
    background: #FFFFFF !important;
    color: #263B57 !important;
    min-height: 41px !important;
    font-weight: 680 !important;
    box-shadow: none !important;
}}

.stButton > button:hover,
.stDownloadButton > button:hover {{
    transform: none !important;
    background: #F6F9FD !important;
    border-color: #AEBFD2 !important;
    box-shadow: none !important;
}}

.stButton > button[kind="primary"] {{
    color: #FFFFFF !important;
    border: 1px solid #2457D6 !important;
    background: #2457D6 !important;
    box-shadow: 0 4px 12px rgba(36,87,214,.16) !important;
}}

.stButton > button[kind="primary"]:hover {{
    background: #1E4CBF !important;
    border-color: #1E4CBF !important;
}}

button[data-baseweb="tab"] {{
    color: #607188 !important;
    font-weight: 650 !important;
    border-radius: 0 !important;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    color: #1747B5 !important;
    font-weight: 740 !important;
}}

[data-testid="stSegmentedControl"] button {{
    background: #FFFFFF !important;
    border-color: #D6DFEA !important;
    color: #52637A !important;
    font-weight: 640 !important;
}}

[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] button[data-active="true"] {{
    background: #EAF1FF !important;
    color: #1747B5 !important;
    border-color: #B8CBEF !important;
}}

div[data-testid="stDataFrame"] {{
    border: 1px solid #D9E1EA !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    box-shadow: none !important;
}}

[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border: 1px solid #D7E0EB !important;
    box-shadow: none !important;
}}

[data-testid="stExpander"] {{
    border: 1px solid #D9E1EA !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
}}

.kdp-chain-step {{
    border: 1px solid #D9E1EA !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    box-shadow: none !important;
}}

.kdp-chain-name {{
    color: #182D4B !important;
}}

.kdp-chain-desc {{
    color: #596A80 !important;
    font-size: 10.8px !important;
}}

.kdp-soft-note {{
    border: 1px solid #D7E1F1 !important;
    border-left: 3px solid #5A79C9 !important;
    border-radius: 9px !important;
    background: #F7F9FD !important;
    color: #506178 !important;
}}

.kdp-mini-card {{
    border: 1px solid #D9E1EA !important;
    background: #FFFFFF !important;
    border-radius: 11px !important;
    box-shadow: none !important;
}}

.kdp-mini-title {{
    color: #182D4B !important;
}}

.kdp-mini-text {{
    color: #5F7086 !important;
}}

[data-testid="stMetricLabel"] p {{
    color: #52637A !important;
    font-weight: 650 !important;
}}

[data-testid="stMetricValue"] {{
    color: #1C3150 !important;
}}

button:disabled,
input:disabled,
textarea:disabled,
[aria-disabled="true"] {{
    opacity: .76 !important;
}}

@media (max-width: 720px) {{
    .block-container {{
        padding-left: .9rem !important;
        padding-right: .9rem !important;
    }}

    .kdp-hero {{
        padding: 20px 18px !important;
    }}

    .kdp-hero-title {{
        font-size: 25px !important;
    }}
}}


/* =======================================================================
   FINAL VISUAL SYSTEM · 国科蓝科研期刊风
   ======================================================================= */

:root {{
    --ns-blue: #1359A6;
    --ns-blue-2: #2F73C9;
    --ns-deep: #103B70;
    --ns-ink: #132A43;
    --ns-cyan: #0E9AA7;
    --ns-teal: #16877F;
    --ns-orange: #D9852F;
    --ns-paper: #FBFBF8;
    --ns-bg: #F4F5F4;
    --ns-line: #D7E0E9;
    --ns-muted: #5B6D82;
}}

/* 页面像“科研期刊工作台”，而不是 AI 聊天后台 */
.stApp {{
    background:
        linear-gradient(90deg, rgba(19,89,166,.018) 1px, transparent 1px),
        linear-gradient(rgba(19,89,166,.018) 1px, transparent 1px),
        #F5F6F4 !important;
    background-size: 44px 44px !important;
}}

.block-container {{
    max-width: 1510px !important;
    padding-top: 1.35rem !important;
    padding-left: 2.35rem !important;
    padding-right: 2.35rem !important;
}}

/* 顶栏 */
header[data-testid="stHeader"] {{
    background: rgba(250,250,247,.94) !important;
    border-bottom: 1px solid rgba(19,89,166,.09) !important;
}}

/* 侧栏：不黑、不苍白；淡蓝灰底 + 品牌区 */
section[data-testid="stSidebar"] {{
    background:
        linear-gradient(180deg, #F7F9FC 0%, #F1F5F8 100%) !important;
    border-right: 1px solid #D5DFE9 !important;
    box-shadow: 10px 0 30px rgba(22,57,94,.035) !important;
}}

section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {{
    color: #657891 !important;
    font-size: 10.5px !important;
    font-weight: 800 !important;
    letter-spacing: .055em !important;
    padding-top: 17px !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    margin: 2px 8px !important;
    padding: 9px 11px !important;
    border-radius: 9px !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: rgba(19,89,166,.055) !important;
}}

section[data-testid="stSidebar"] [aria-current="page"] {{
    background: #E7F0FA !important;
    color: #0E4D91 !important;
    box-shadow: inset 3px 0 0 #1359A6 !important;
}}

section[data-testid="stSidebar"] [aria-current="page"] * {{
    color: #0E4D91 !important;
    font-weight: 760 !important;
}}

/* 品牌区：形成自己的 KDP/DKDP 识别，不直接套 AI 产品 logo */
.kdp-brand {{
    position: relative;
    overflow: hidden;
    margin: 9px 8px 7px 8px !important;
    padding: 15px 14px 14px 14px !important;
    border-radius: 14px !important;
    background:
        radial-gradient(circle at 92% 10%, rgba(255,255,255,.22), transparent 34%),
        linear-gradient(135deg, #103F7B 0%, #1359A6 62%, #1D72B4 100%) !important;
    box-shadow: 0 9px 25px rgba(16,63,123,.13) !important;
}}

.kdp-brand::after {{
    content: "KH₂PO₄ · KD₂PO₄";
    position: absolute;
    right: 12px;
    bottom: 9px;
    color: rgba(255,255,255,.42);
    font-size: 8.8px;
    letter-spacing: .06em;
}}

.kdp-brand-mark {{
    width: 36px !important;
    height: 36px !important;
    border-radius: 9px !important;
    background: rgba(255,255,255,.14) !important;
    border: 1px solid rgba(255,255,255,.26) !important;
    color: white !important;
    box-shadow: none !important;
    font-size: 11px !important;
}}

.kdp-brand-title {{
    color: #FFFFFF !important;
    font-size: 15px !important;
    font-weight: 790 !important;
    letter-spacing: .01em !important;
}}

.kdp-brand-sub {{
    color: rgba(244,249,255,.76) !important;
    font-size: 10.3px !important;
    line-height: 1.45 !important;
}}

/* 模型状态降权，不抢品牌 */
.kdp-ai-badge {{
    background: transparent !important;
    border: 0 !important;
    border-top: 1px solid #DFE6ED !important;
    border-radius: 0 !important;
    margin: 10px 13px 3px 13px !important;
    padding: 10px 2px 4px 2px !important;
}}
.kdp-ai-badge * {{ color: #62758C !important; }}

/* Hero：白纸 + 国科蓝书脊 + 化学式水印 */
.kdp-hero {{
    position: relative;
    min-height: 118px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    border: 1px solid #D4DEE8 !important;
    border-radius: 15px !important;
    padding: 23px 31px 23px 31px !important;
    background:
        linear-gradient(100deg, rgba(19,89,166,.042), transparent 48%),
        #FCFCFA !important;
    box-shadow: 0 6px 18px rgba(18,54,91,.035) !important;
}}

.kdp-hero::before {{
    width: 5px !important;
    top: 20px !important;
    bottom: 20px !important;
    background: linear-gradient(180deg, #1359A6, #2F73C9) !important;
}}

.kdp-hero::after {{
    content: "KDP / DKDP" !important;
    width: auto !important;
    height: auto !important;
    right: 28px !important;
    top: 26px !important;
    border: 0 !important;
    box-shadow: none !important;
    color: rgba(19,89,166,.055) !important;
    font-size: 54px !important;
    font-weight: 850 !important;
    letter-spacing: -.04em !important;
    transform: none !important;
}}

.kdp-eyebrow {{
    width: fit-content;
    color: #1359A6 !important;
    background: #ECF3FA !important;
    border: 1px solid #D8E6F3 !important;
    border-radius: 999px !important;
    font-size: 9px !important;
    letter-spacing: .095em !important;
}}

.kdp-hero-title {{
    color: #102A43 !important;
    font-size: 31px !important;
    font-weight: 820 !important;
    letter-spacing: -.035em !important;
}}

.kdp-hero-sub {{
    color: #52677F !important;
    font-size: 13px !important;
    max-width: 970px !important;
}}

/* 指标卡：用“书脊色”而非彩虹卡 */
.kdp-metric-grid {{
    gap: 10px !important;
}}

.kdp-metric-card {{
    min-height: 110px !important;
    padding: 17px 18px 15px 19px !important;
    border: 1px solid #D6E0E9 !important;
    border-radius: 12px !important;
    background: #FEFEFC !important;
    box-shadow: 0 4px 13px rgba(18,54,91,.026) !important;
}}
.kdp-metric-card::before {{
    width: 3px !important;
    border-radius: 0 3px 3px 0 !important;
}}
.kdp-metric-label {{
    color: #5A6D84 !important;
    font-size: 11.2px !important;
}}
.kdp-metric-value {{
    color: #102A43 !important;
    font-size: 27px !important;
}}
.kdp-metric-note {{
    color: #748397 !important;
    font-size: 10.6px !important;
}}

/* 编辑式“数据观察” */
.kdp-insight-strip {{
    display: grid;
    grid-template-columns: repeat(var(--cols, 3), minmax(0,1fr));
    gap: 10px;
    margin: 1px 0 22px 0;
}}
.kdp-insight {{
    position: relative;
    padding: 13px 15px 13px 16px;
    border-top: 1px solid #CFD9E4;
    border-bottom: 1px solid #CFD9E4;
    background: rgba(255,255,253,.50);
}}
.kdp-insight::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 13px;
    bottom: 13px;
    width: 2px;
    background: var(--accent, #1359A6);
}}
.kdp-insight-kicker {{
    color: #718196;
    font-size: 9.5px;
    font-weight: 780;
    letter-spacing: .08em;
    margin-bottom: 5px;
}}
.kdp-insight-title {{
    color: #16324F;
    font-size: 15px;
    font-weight: 770;
    line-height: 1.35;
}}
.kdp-insight-note {{
    color: #60738A;
    font-size: 10.8px;
    margin-top: 4px;
}}

/* 研究链条：像科研流程图，不再四张 AI 卡片 */
.kdp-chain-grid {{
    position: relative;
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 0 !important;
    margin: 6px 0 25px 0 !important;
    border-top: 1px solid #CAD6E2;
    border-bottom: 1px solid #CAD6E2;
    background: rgba(255,255,253,.52);
}}
.kdp-chain-step {{
    position: relative;
    min-height: 112px !important;
    padding: 17px 19px 15px 19px !important;
    border: 0 !important;
    border-right: 1px solid #D7E0E9 !important;
    border-radius: 0 !important;
    background: transparent !important;
}}
.kdp-chain-step:last-child {{ border-right: 0 !important; }}
.kdp-chain-step::before {{
    content: "";
    position: absolute;
    top: -4px;
    left: 19px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #1359A6;
    box-shadow: 0 0 0 4px #EDF3F9;
}}
.kdp-chain-kicker {{
    color: #1359A6 !important;
    font-size: 9.5px !important;
    letter-spacing: .085em !important;
}}
.kdp-chain-name {{
    color: #17324E !important;
    font-size: 14.5px !important;
    font-weight: 780 !important;
    margin-top: 6px !important;
}}
.kdp-chain-desc {{
    color: #607287 !important;
    font-size: 10.8px !important;
    line-height: 1.55 !important;
}}

/* 小标题更像论文栏目 */
.kdp-section-head {{
    margin-top: 27px !important;
    margin-bottom: 11px !important;
}}
.kdp-section-title {{
    position: relative;
    color: #17324E !important;
    font-size: 18px !important;
    font-weight: 790 !important;
    padding-left: 11px;
}}
.kdp-section-title::before {{
    content: "";
    position: absolute;
    left: 0;
    top: .18em;
    bottom: .18em;
    width: 3px;
    border-radius: 3px;
    background: #1359A6;
}}
.kdp-section-sub {{
    color: #66788C !important;
    margin-left: 11px;
    margin-top: 3px;
    font-size: 11.5px !important;
}}

/* 表单/容器：去“所有东西都是大圆角卡片”的AI味 */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid #D5DFE8 !important;
    border-radius: 11px !important;
    background: #FDFDFC !important;
    box-shadow: 0 3px 10px rgba(18,54,91,.02) !important;
}}
div[data-testid="stForm"] {{
    border-radius: 11px !important;
    background: #FDFDFC !important;
}}

/* 字体清晰度 */
p, label, .stCaption,
[data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"] {{
    color: #53677E !important;
}}
[data-testid="stWidgetLabel"] p,
label[data-baseweb="form-control-label"] {{
    color: #2B445F !important;
    font-weight: 700 !important;
    font-size: 12.8px !important;
}}
input::placeholder, textarea::placeholder {{
    color: #8190A2 !important;
}}

/* 输入区更像实验软件 */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {{
    border-color: #C8D5E2 !important;
    border-radius: 7px !important;
    background: #FFFFFF !important;
}}
div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {{
    border-color: #1359A6 !important;
    box-shadow: 0 0 0 2px rgba(19,89,166,.09) !important;
}}

/* 主按钮：单一国科蓝，不要霓虹/AI渐变 */
.stButton > button[kind="primary"] {{
    background: #1359A6 !important;
    border: 1px solid #1359A6 !important;
    color: #FFFFFF !important;
    border-radius: 7px !important;
    box-shadow: 0 4px 10px rgba(19,89,166,.15) !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #0F4B8D !important;
    border-color: #0F4B8D !important;
}}

/* 普通按钮减少圆润感 */
.stButton > button,
.stDownloadButton > button {{
    border-radius: 7px !important;
}}

/* Segmented control：彻底消除默认红色 */
[data-testid="stSegmentedControl"] button,
[data-testid="stSegmentedControl"] [role="radio"],
[data-testid="stSegmentedControl"] label {{
    border-color: #CFD9E4 !important;
    color: #50647B !important;
    background: #FCFCFA !important;
}}
[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"],
[data-testid="stSegmentedControl"] label:has(input:checked) {{
    border-color: #1359A6 !important;
    color: #0E4D91 !important;
    background: #EAF2FA !important;
}}
[data-testid="stSegmentedControl"] label:has(input:checked) * {{
    color: #0E4D91 !important;
}}

/* Radio 默认红点也替换为科研蓝 */
[data-testid="stRadio"] input:checked + div,
[data-testid="stRadio"] [aria-checked="true"] > div:first-child {{
    border-color: #1359A6 !important;
}}
[data-testid="stRadio"] svg {{
    color: #1359A6 !important;
}}

/* 表格更像数据库，不像AI卡片 */
div[data-testid="stDataFrame"] {{
    border-radius: 8px !important;
    border-color: #D4DEE8 !important;
    box-shadow: none !important;
}}

/* 提示条 */
.kdp-soft-note {{
    border: 0 !important;
    border-left: 3px solid #1359A6 !important;
    border-radius: 0 !important;
    background: #EEF4F9 !important;
    color: #50657C !important;
    padding: 11px 13px !important;
}}

/* API 用量和 st.metric */
[data-testid="stMetricValue"] {{
    color: #15324F !important;
}}
[data-testid="stMetricLabel"] p {{
    color: #607287 !important;
}}

/* Plotly外部容器不再有默认大白块感 */
[data-testid="stPlotlyChart"] {{
    border-top: 1px solid rgba(203,215,227,.72);
    padding-top: 5px;
}}

/* 手机 */
@media (max-width: 800px) {{
    .kdp-insight-strip {{ grid-template-columns: 1fr !important; }}
    .kdp-chain-grid {{ grid-template-columns: 1fr !important; }}
    .kdp-chain-step {{
        border-right: 0 !important;
        border-bottom: 1px solid #D7E0E9 !important;
    }}
    .kdp-hero::after {{ display:none !important; }}
}}


/* ===== screenshot acceptance fixes ===== */
section[data-testid="stSidebar"] .kdp-brand .kdp-brand-title {{
    color: #FFFFFF !important;
}}
section[data-testid="stSidebar"] .kdp-brand .kdp-brand-sub {{
    color: rgba(247,251,255,.82) !important;
}}
section[data-testid="stSidebar"] .kdp-brand .kdp-brand-mark {{
    color: #FFFFFF !important;
}}
section[data-testid="stSidebar"] .kdp-brand::after {{
    color: rgba(255,255,255,.52) !important;
}}

.stButton > button[kind="primary"],
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {{
    color: #FFFFFF !important;
}}

div[data-baseweb="textarea"] textarea,
div[data-baseweb="input"] input {{
    color: #243B55 !important;
    font-weight: 500 !important;
}}

/* 小屏和笔记本上也保证 Hero 不显得过大 */
@media (max-width: 1280px) {{
    .kdp-hero-title {{
        font-size: 28px !important;
    }}
    .kdp-hero {{
        min-height: 108px !important;
    }}
}}

</style>
""",
        unsafe_allow_html=True,
    )


def sidebar_brand():
    st.sidebar.markdown(
        """
<div class="kdp-brand">
    <div class="kdp-brand-mark">KDP</div>
    <div class="kdp-brand-title">KDP / DKDP 研究工作台</div>
    <div class="kdp-brand-sub">晶体缺陷 · 生长 · 开裂<br>Evidence → Mechanism → Validation</div>
</div>
""",
        unsafe_allow_html=True,
    )


def sidebar_ai_status(ok: bool, model: str):
    color = "#58D6A7" if ok else "#F3AA62"
    label = model if ok else "离线功能可用"
    st.sidebar.markdown(
        f"""
<div class="kdp-ai-badge">
    <div style="font-size:11px;color:#8FA0B8;margin-bottom:5px;">MODEL SERVICE</div>
    <div style="font-size:12px;font-weight:650;color:#EAF0F8;">
        <span class="kdp-dot" style="background:{color};"></span>{html.escape(label)}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("文献优先级不删库；联网检索按需参与分析，结果保留来源。")


def page_header(title: str, subtitle: str, eyebrow: str = "KDP / DKDP RESEARCH WORKSPACE"):
    st.markdown(
        f"""
<div class="kdp-hero">
    <div class="kdp-eyebrow">{html.escape(eyebrow)}</div>
    <div class="kdp-hero-title">{html.escape(title)}</div>
    <div class="kdp-hero-sub">{html.escape(subtitle)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def metric_cards(cards: Sequence[dict]):
    parts = ['<div class="kdp-metric-grid">']
    for i, card in enumerate(cards):
        accent = card.get("accent", ["#5B5BD6", "#19B6C9", "#22A699", "#F28C52", "#8B6FD9", "#E46A76"][i % 6])
        parts.append(
            f"""
<div class="kdp-metric-card" style="--accent:{accent};">
  <div class="kdp-metric-label">{html.escape(str(card.get("label","")))}</div>
  <div class="kdp-metric-value">{html.escape(str(card.get("value","")))}</div>
  <div class="kdp-metric-note">{html.escape(str(card.get("note","")))}</div>
</div>
"""
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)



def insight_strip(items: Sequence[dict]):
    """编辑式数据观察条，用于突出真正值得先看的信息。"""
    if not items:
        return
    cols = max(1, min(len(items), 4))
    parts = [f'<div class="kdp-insight-strip" style="--cols:{cols};">']
    palette = [COLORS["primary"], COLORS["cyan"], COLORS["orange"], COLORS["teal"]]
    for i, item in enumerate(items):
        accent = item.get("accent", palette[i % len(palette)])
        parts.append(
            f"""
<div class="kdp-insight" style="--accent:{accent};">
  <div class="kdp-insight-kicker">{html.escape(str(item.get("kicker","DATA NOTE")))}</div>
  <div class="kdp-insight-title">{html.escape(str(item.get("title","")))}</div>
  <div class="kdp-insight-note">{html.escape(str(item.get("note","")))}</div>
</div>
"""
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def section_title(title: str, subtitle: str = ""):
    st.markdown(
        f"""
<div class="kdp-section-head">
  <div>
    <div class="kdp-section-title">{html.escape(title)}</div>
    <div class="kdp-section-sub">{html.escape(subtitle)}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def soft_note(text: str):
    st.markdown(
        f'<div class="kdp-soft-note">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def research_chain():
    items = [
        ("01", "缺陷 / 应力来源", "点缺陷 · 杂质 · 包裹体 · 位错 · 生长 · 籽晶 · 加工 · 固定约束"),
        ("02", "局部机制", "氢键与晶格畸变 · 缺陷态 · 生长界面 · 热—力应力"),
        ("03", "宏观后果", "吸收 / 散射 · 裂纹萌生 · LIDT下降 · 激光损伤"),
        ("04", "证据与控制", "DFT / MD / FEA + Raman / FTIR / XRD / AFM / 光热 / 对照实验"),
    ]
    body = ['<div class="kdp-chain-grid">']
    for n, title, desc in items:
        body.append(
            f"""
<div class="kdp-chain-step">
  <div class="kdp-chain-kicker">PATH {n}</div>
  <div class="kdp-chain-name">{html.escape(title)}</div>
  <div class="kdp-chain-desc">{html.escape(desc)}</div>
</div>
"""
        )
    body.append("</div>")
    st.markdown("".join(body), unsafe_allow_html=True)


def mini_cards(items: Iterable[tuple[str, str]]):
    for title, text in items:
        st.markdown(
            f"""
<div class="kdp-mini-card">
  <div class="kdp-mini-title">{html.escape(str(title))}</div>
  <div class="kdp-mini-text">{html.escape(str(text))}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def style_plot(fig: go.Figure, *, dark: bool = False, height: int | None = None):
    if dark:
        bg = "#0B1220"
        paper = "#0B1220"
        text = "#DDE7F4"
        grid = "rgba(154,172,198,.12)"
        muted = "#96A8BF"
    else:
        bg = "rgba(255,255,252,0)"
        paper = "rgba(255,255,252,0)"
        text = COLORS["ink"]
        grid = "rgba(180,195,210,.36)"
        muted = "#5D7187"

    fig.update_layout(
        paper_bgcolor=paper,
        plot_bgcolor=bg,
        font=dict(
            family='Inter, "PingFang SC", "Microsoft YaHei", Arial',
            size=12,
            color=text,
        ),
        margin=dict(l=24, r=18, t=42, b=24),
        hoverlabel=dict(
            bgcolor="#101C2F" if dark else "#FFFFFF",
            bordercolor="#31415A" if dark else "#D9E2ED",
            font=dict(color="#F4F7FB" if dark else COLORS["ink"], size=12),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=muted, size=11),
        ),
    )
    if height:
        fig.update_layout(height=height)

    fig.update_xaxes(
        showgrid=True,
        gridcolor=grid,
        zeroline=False,
        linecolor=grid,
        tickfont=dict(color=muted),
        title_font=dict(color=muted),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=grid,
        zeroline=False,
        linecolor=grid,
        tickfont=dict(color=muted),
        title_font=dict(color=muted),
    )
    return fig


def plotly(fig: go.Figure, *, dark: bool = False, height: int | None = None, key: str | None = None, config: dict | None = None):
    style_plot(fig, dark=dark, height=height)
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        key=key,
        config=config or {"displaylogo": False},
    )


def evidence_table(data, height=430):
    cols = [
        "题名",
        "年份",
        "_证据层级",
        "V5推荐等级",
        "详细二级分类",
        "_方法标签",
        "DOI",
    ]
    cols = [c for c in cols if c in data.columns]

    config = {}
    if "V5科研优先分" in data.columns:
        config["V5科研优先分"] = st.column_config.ProgressColumn(
            "科研优先分",
            min_value=0,
            max_value=100,
            format="%.1f",
        )

    st.dataframe(
        data[cols],
        width="stretch",
        height=height,
        hide_index=True,
        column_config=config or None,
    )


def sources_block(src):
    if not src:
        return
    with st.expander("依据文献", expanded=False):
        for x in src:
            doi = x.get("DOI", "")
            st.markdown(
                f"**[{x.get('编号','')}]** {x.get('题名','')}  "
                f"<span style='color:#8390A3;'>({x.get('年份','')})</span>  "
                f"<span style='color:#6D5EF7;'>DOI: {doi}</span>",
                unsafe_allow_html=True,
            )
