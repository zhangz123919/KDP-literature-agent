from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

from research_memory import get_active_project, list_items
from ui import section_title


def _count(kind: str) -> int:
    try:
        return len(list_items(kind))
    except Exception:
        return 0


def _safe(s) -> str:
    return html.escape(str(s or ""))


def _page(key: str):
    return (st.session_state.get("_kdp_nav_pages") or {}).get(key)


def _page_link(key: str, label: str, icon: str | None = None, help_text: str | None = None):
    page = _page(key)
    if page is None:
        st.button(label, disabled=True, width="stretch")
        return
    st.page_link(page, label=label, icon=icon, help=help_text, width="stretch")


def _entry_group(title: str, note: str, items):
    st.markdown(
        f"""
<div class="entry-group-head">
  <div class="entry-group-title">{title}</div>
  <div class="entry-group-note">{note}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    for key, label, icon, help_text in items:
        _page_link(key, label, icon, help_text)


def _growth_component():
    # 独立 iframe 渲染 SVG/CSS 动画，避免 Markdown 把 SVG 源码显示出来。
    component_html = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>
html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:transparent;font-family:"Microsoft YaHei",Arial,sans-serif}
.stage{position:relative;width:100%;height:455px;overflow:hidden;background:radial-gradient(circle at 51% 47%,rgba(35,151,176,.16),transparent 25%),radial-gradient(circle at 51% 51%,rgba(20,91,159,.08),transparent 55%)}
.meta{position:absolute;z-index:5;right:18px;top:12px;text-align:right;font-size:9px;line-height:1.65;letter-spacing:.12em;font-weight:800;color:#667F92}
.legend{position:absolute;z-index:5;left:15px;bottom:12px;padding:8px 10px;border-left:2px solid #168E9C;background:rgba(248,251,251,.78);font-size:9px;line-height:1.55;color:#658093}
svg{width:100%;height:100%;display:block}
.front{stroke-dasharray:11 11;animation:front 5.5s linear infinite}@keyframes front{to{stroke-dashoffset:-88}}
.flow{stroke-dasharray:6 10;animation:flow 4.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-96}}
.crystal{transform-origin:260px 335px;animation:grow 7s ease-in-out infinite}@keyframes grow{0%,100%{transform:scale(.985)}50%{transform:scale(1.018)}}
.crack{stroke-dasharray:150;stroke-dashoffset:150;animation:crack 8.4s ease-in-out infinite}@keyframes crack{0%,38%{stroke-dashoffset:150;opacity:.05}58%,82%{stroke-dashoffset:0;opacity:.88}100%{stroke-dashoffset:150;opacity:.05}}
.ion{animation:ion 6.2s ease-in-out infinite}.i2{animation-delay:-1.5s}.i3{animation-delay:-3.1s}.i4{animation-delay:-4.4s}@keyframes ion{0%{transform:translateY(17px);opacity:.03}25%{opacity:.72}78%{opacity:.62}100%{transform:translateY(-72px);opacity:.03}}
</style>
</head>
<body>
<div class="stage">
  <div class="meta">KDP GROWTH SCHEMATIC<br>生长界面 · 传质/温度场 · 裂纹萌生<br>动态示意，非数值模拟结果</div>
  <div class="legend">水溶液生长 → 界面推进 → 局部应力 → 裂纹萌生</div>
  <svg viewBox="0 0 520 455" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="crystalFill" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#FAFDFD" stop-opacity=".96"/><stop offset="46%" stop-color="#B8DEE6" stop-opacity=".60"/><stop offset="100%" stop-color="#438FC2" stop-opacity=".38"/></linearGradient>
      <linearGradient id="faceBlue" x1="0" x2="1"><stop offset="0%" stop-color="#195FA6" stop-opacity=".17"/><stop offset="100%" stop-color="#14A1A4" stop-opacity=".49"/></linearGradient>
      <radialGradient id="solutionFill"><stop offset="0%" stop-color="#8DD4DF" stop-opacity=".26"/><stop offset="72%" stop-color="#438FB9" stop-opacity=".12"/><stop offset="100%" stop-color="#205D92" stop-opacity=".02"/></radialGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="3.1" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>

    <ellipse cx="267" cy="366" rx="192" ry="56" fill="url(#solutionFill)" stroke="#357FAC" stroke-opacity=".22"/>
    <ellipse cx="267" cy="366" rx="151" ry="38" fill="none" stroke="#2C87A9" stroke-opacity=".20"/>
    <ellipse cx="267" cy="366" rx="112" ry="25" fill="none" stroke="#1A69A2" stroke-opacity=".16"/>

    <path class="flow" d="M82 333 C125 278,162 274,195 236" fill="none" stroke="#168E9C" stroke-opacity=".55" stroke-width="2"/>
    <path class="flow" d="M447 333 C407 282,378 270,344 238" fill="none" stroke="#168E9C" stroke-opacity=".50" stroke-width="2"/>
    <path class="flow" d="M102 386 C155 421,209 411,234 397" fill="none" stroke="#2469A7" stroke-opacity=".30" stroke-width="1.6"/>
    <path class="flow" d="M430 386 C383 420,337 412,303 398" fill="none" stroke="#2469A7" stroke-opacity=".30" stroke-width="1.6"/>

    <g class="ion"><circle cx="140" cy="324" r="5" fill="#0E9AA7" opacity=".55"/></g>
    <g class="ion i2"><circle cx="391" cy="315" r="4" fill="#D9852F" opacity=".58"/></g>
    <g class="ion i3"><circle cx="183" cy="349" r="3.6" fill="#557BC1" opacity=".50"/></g>
    <g class="ion i4"><circle cx="349" cy="347" r="4.4" fill="#0E9AA7" opacity=".48"/></g>

    <g class="crystal">
      <polygon points="205,164 260,106 318,162 335,327 304,369 219,369 186,327" fill="url(#crystalFill)" stroke="#1766A4" stroke-opacity=".74" stroke-width="2.2"/>
      <polygon points="205,164 260,106 260,174 186,327" fill="#FFFFFF" fill-opacity=".30" stroke="#5BA7C5" stroke-opacity=".34"/>
      <polygon points="260,106 318,162 335,327 260,174" fill="url(#faceBlue)" stroke="#3986AF" stroke-opacity=".34"/>
      <polygon points="186,327 260,174 335,327 304,369 219,369" fill="#2C80B0" fill-opacity=".11" stroke="#2974A0" stroke-opacity=".26"/>
      <path class="front" d="M198 211 L260 148 L325 210" fill="none" stroke="#0C99A0" stroke-opacity=".62" stroke-width="1.8"/>
      <path class="front" d="M193 249 L260 185 L329 248" fill="none" stroke="#145A9F" stroke-opacity=".48" stroke-width="1.6"/>
      <path class="front" d="M190 288 L260 222 L332 287" fill="none" stroke="#0C99A0" stroke-opacity=".42" stroke-width="1.5"/>
      <path d="M228 180 C241 221,225 270,245 331" fill="none" stroke="#6B63B5" stroke-opacity=".36" stroke-width="1.5"/>
      <path d="M289 171 C275 222,299 273,279 343" fill="none" stroke="#6B63B5" stroke-opacity=".29" stroke-width="1.5"/>
      <path d="M212 297 C246 283,285 284,319 301" fill="none" stroke="#D9852F" stroke-opacity=".34" stroke-width="1.5"/>
      <path class="crack" d="M292 192 L279 221 L294 244 L273 269 L287 294 L270 319" fill="none" stroke="#D97F32" stroke-width="3.2" stroke-linecap="round" filter="url(#glow)"/>
    </g>

    <g font-size="10.5" fill="#536D82">
      <text x="45" y="267">过饱和溶液 / 对流</text><line x1="146" y1="264" x2="188" y2="251" stroke="#557C97" stroke-opacity=".44"/>
      <text x="354" y="162">生长界面</text><line x1="349" y1="166" x2="317" y2="182" stroke="#557C97" stroke-opacity=".44"/>
      <text x="362" y="242">局部应力场</text><line x1="356" y1="246" x2="303" y2="268" stroke="#6B63B5" stroke-opacity=".46"/>
      <text x="359" y="300">裂纹萌生 / 扩展</text><line x1="354" y1="304" x2="286" y2="292" stroke="#D9852F" stroke-opacity=".52"/>
    </g>
  </svg>
</div>
</body>
</html>
    """
    components.html(component_html, height=455, scrolling=False)


def home_page():
    project = get_active_project() or {}
    project_name = _safe(project.get("name", "KDP研究主项目"))
    project_status = _safe(project.get("status", "进行中"))

    counts = {
        "evidence": _count("evidence"),
        "hypothesis": _count("hypothesis"),
        "experiment": _count("experiment"),
        "calculation": _count("calculation") + _count("calculation_result"),
    }

    st.markdown(
        """
<style>
.home-shell{border-top:3px solid #145A9F;border-bottom:1px solid rgba(24,68,105,.14);background:#F7F7F3;padding:28px 32px 20px}
.home-eyebrow{display:flex;align-items:center;gap:11px;font-size:10px;font-weight:900;letter-spacing:.14em;color:#527087}.home-eyebrow:before{content:"";width:32px;height:2px;background:#145A9F;display:block}
.home-title{margin:22px 0 15px;color:#102F4B;font-size:49px;line-height:1.07;font-weight:890;letter-spacing:-.035em}.home-title span{color:#145A9F}
.home-deck{color:#536D82;font-size:16px;line-height:1.9;max-width:760px}
.home-objective{margin-top:24px;padding:15px 17px;border-left:3px solid #0F9298;background:rgba(15,146,152,.045);color:#3B5A71;font-size:12px;line-height:1.75}
.home-axis{margin-top:22px;display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid rgba(25,75,112,.13);border-bottom:1px solid rgba(25,75,112,.13)}
.home-axis-cell{padding:11px 8px 11px 0}.home-axis-no{font-size:8px;font-weight:900;letter-spacing:.13em;color:#9AA8B4}.home-axis-name{margin-top:4px;font-size:11px;font-weight:820;color:#294A63}
.state-strip{margin-top:14px;display:grid;grid-template-columns:2fr repeat(4,1fr);background:#fff;border:1px solid rgba(24,68,105,.10);border-radius:12px;overflow:hidden}
.state-cell{padding:15px 18px;border-right:1px solid rgba(24,68,105,.08)}.state-cell:last-child{border-right:none}.state-k{font-size:9px;letter-spacing:.12em;font-weight:900;color:#91A0AD}.state-v{margin-top:4px;font-size:18px;font-weight:850;color:#163650}.state-n{margin-top:3px;font-size:10px;color:#80909E}
.entry-group-head{margin:0 0 8px;padding-bottom:8px;border-bottom:1px solid rgba(24,68,105,.10)}.entry-group-title{font-size:15px;font-weight:850;color:#1A3B55}.entry-group-note{margin-top:3px;font-size:10px;line-height:1.5;color:#8795A1}
div[data-testid="stPageLink"] a{min-height:42px;border-radius:7px!important;border:1px solid rgba(24,68,105,.10)!important;background:#FCFCFA!important;color:#2A485F!important;box-shadow:none!important;transition:all .15s ease}div[data-testid="stPageLink"] a:hover{transform:translateX(3px);border-color:rgba(20,90,159,.30)!important;background:#F3F8FA!important}
.research-loop{display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid rgba(24,68,105,.13);border-bottom:1px solid rgba(24,68,105,.13);background:#F8F8F5}.loop-cell{padding:17px 14px;min-height:101px;border-right:1px solid rgba(24,68,105,.08)}.loop-cell:last-child{border-right:none}.loop-no{font-size:8px;font-weight:900;letter-spacing:.12em;color:#A1ADB7}.loop-title{margin-top:9px;font-size:13px;font-weight:850;color:#1D3E57}.loop-note{margin-top:5px;font-size:10px;line-height:1.45;color:#7C8D9A}
.data-boundary{margin-top:6px;padding:13px 15px;border-left:3px solid #6E6AB7;background:rgba(110,106,183,.035);color:#6F7F8D;font-size:10px;line-height:1.65}
@media(max-width:1250px){.home-title{font-size:42px}.state-strip{grid-template-columns:repeat(2,1fr)}.research-loop{grid-template-columns:repeat(3,1fr)}}
</style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        left, right = st.columns([1.05, .95], gap="large")
        with left:
            st.markdown(
                f"""
<div class="home-shell">
  <div class="home-eyebrow">KDP 晶体生长 · 缺陷 · 开裂</div>
  <div class="home-title">KDP晶体缺陷与开裂<br><span>研究工作台</span></div>
  <div class="home-deck">面向水溶液法生长KDP晶体，围绕生长条件、原生缺陷、局部应力与裂纹萌生，统一管理文献证据、实验记录、计算任务与阶段判断。</div>
  <div class="home-objective"><b>研究链：</b> 文献依据 → 科学假设 → 实验检验 → 理论验证 → 下一轮研究决策。平台负责把各环节的证据和记录持续关联起来。</div>
  <div class="home-axis">
    <div class="home-axis-cell"><div class="home-axis-no">01</div><div class="home-axis-name">证据</div></div>
    <div class="home-axis-cell"><div class="home-axis-no">02</div><div class="home-axis-name">假设</div></div>
    <div class="home-axis-cell"><div class="home-axis-no">03</div><div class="home-axis-name">实验</div></div>
    <div class="home-axis-cell"><div class="home-axis-no">04</div><div class="home-axis-name">计算</div></div>
    <div class="home-axis-cell"><div class="home-axis-no">05</div><div class="home-axis-name">决策</div></div>
  </div>
</div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            _growth_component()

    st.markdown(
        f"""
<div class="state-strip">
  <div class="state-cell"><div class="state-k">当前项目</div><div class="state-v">{project_name}</div><div class="state-n">状态：{project_status}</div></div>
  <div class="state-cell"><div class="state-k">项目证据</div><div class="state-v">{counts['evidence']}</div><div class="state-n">已沉淀文献证据</div></div>
  <div class="state-cell"><div class="state-k">科学假设</div><div class="state-v">{counts['hypothesis']}</div><div class="state-n">待验证 / 验证中</div></div>
  <div class="state-cell"><div class="state-k">实验记录</div><div class="state-v">{counts['experiment']}</div><div class="state-n">受保护实验索引</div></div>
  <div class="state-cell"><div class="state-k">计算任务</div><div class="state-v">{counts['calculation']}</div><div class="state-n">任务与结果</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title("研究模块", "按当前科研任务直接进入；站内切换保留当前项目上下文")

    row1 = st.columns(4, gap="medium")
    with row1[0]:
        _entry_group("项目与总览", "查看研究状态与项目记忆", [
            ("overview", "科研驾驶舱", ":material/dashboard:", "查看当前研究状态、证据和专题概览"),
            ("project", "研究总控台", ":material/account_tree:", "管理项目问题、假设与研究记忆"),
        ])
    with row1[1]:
        _entry_group("文献与知识", "从证据进入", [
            ("literature", "文献中心", ":material/library_books:", "检索、筛选和沉淀KDP文献证据"),
            ("knowledge", "知识图谱", ":material/hub:", "查看来源—机制—结果—具体论文证据网络"),
            ("topics", "专题调研", ":material/travel_explore:", "围绕具体研究问题形成专题调研"),
            ("compare", "多文献比较", ":material/compare_arrows:", "比较多篇论文的方法、证据与结论"),
        ])
    with row1[2]:
        _entry_group("实验与验证", "从现象和变量进入", [
            ("diagnosis", "开裂诊断", ":material/crisis_alert:", "排查开裂变量并结合历史实验"),
            ("experiment", "对照实验设计", ":material/fact_check:", "把假设转化为可证伪实验"),
            ("experiment_log", "实验记录与数据积累", ":material/database:", "记录真实实验并为后续机器学习积累数据"),
        ])
    with row1[3]:
        _entry_group("理论与机理", "从机制问题进入", [
            ("theory", "理论计算规划与分析", ":material/science:", "规划DFT / MD / FEA并回填结果"),
            ("gaps", "研究空白", ":material/lightbulb:", "识别证据薄弱区与待核科学问题"),
        ])

    row2 = st.columns(3, gap="medium")
    with row2[0]:
        _entry_group("方向与分析", "形成研究判断", [
            ("direction", "研究方向决策", ":material/explore:", "形成候选课题与阶段路线"),
            ("ai", "AI科研助手", ":material/forum:", "结合项目记忆开展证据整合与科研分析"),
        ])
    with row2[1]:
        _entry_group("成果与复盘", "沉淀阶段结果", [
            ("reports", "报告中心", ":material/description:", "生成阶段报告与汇报材料"),
            ("audit", "数据审计", ":material/monitor_heart:", "检查证据、分类和项目记录完整性"),
        ])
    with row2[2]:
        st.markdown('<div class="data-boundary"><b>数据边界：</b> 文献与普通项目记忆可参与智能分析；受保护实验原始数据由实验保险库单独控制。</div>', unsafe_allow_html=True)

    section_title("研究闭环", "文献、实验和理论验证共同服务于同一个科学问题")
    st.markdown(
        """
<div class="research-loop">
  <div class="loop-cell"><div class="loop-no">01 · 证据</div><div class="loop-title">建立依据</div><div class="loop-note">核心论文、方法、共识与争议</div></div>
  <div class="loop-cell"><div class="loop-no">02 · 假设</div><div class="loop-title">形成问题</div><div class="loop-note">把现象转成可验证、可否证假设</div></div>
  <div class="loop-cell"><div class="loop-no">03 · 实验</div><div class="loop-title">对照检验</div><div class="loop-note">真实条件、失败与结果连续积累</div></div>
  <div class="loop-cell"><div class="loop-no">04 · 计算</div><div class="loop-title">机制验证</div><div class="loop-note">DFT / MD / FEA解释局部过程</div></div>
  <div class="loop-cell"><div class="loop-no">05 · 综合</div><div class="loop-title">交叉判断</div><div class="loop-note">比较文献、实验和计算是否一致</div></div>
  <div class="loop-cell"><div class="loop-no">06 · 迭代</div><div class="loop-title">下一轮研究</div><div class="loop-note">更新假设并规划实验、表征与计算</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )
