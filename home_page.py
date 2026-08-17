
from __future__ import annotations

import html

import streamlit as st

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


def _page_link(
    key: str,
    label: str,
    icon: str | None = None,
    help_text: str | None = None,
):
    page = _page(key)
    if page is None:
        st.button(label, disabled=True, width="stretch")
        return
    st.page_link(
        page,
        label=label,
        icon=icon,
        help=help_text,
        width="stretch",
    )


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
/* ============================================================
   KDP HOME — research workstation, not AI landing page
   ============================================================ */
.kdp-home{
    position:relative;
    overflow:hidden;
    border-top:3px solid #145A9F;
    border-bottom:1px solid rgba(24,68,105,.14);
    background:#F7F7F3;
    min-height:535px;
    padding:0;
}
.kdp-home:before{
    content:"";position:absolute;inset:0;
    background-image:
      linear-gradient(rgba(23,75,111,.032) 1px,transparent 1px),
      linear-gradient(90deg,rgba(23,75,111,.032) 1px,transparent 1px);
    background-size:34px 34px;
    pointer-events:none;
}
.home-copy{
    position:relative;z-index:3;
    width:54%;
    padding:58px 40px 42px 58px;
}
.home-eyebrow{
    display:flex;align-items:center;gap:12px;
    font-size:10px;font-weight:900;letter-spacing:.16em;color:#527087
}
.home-eyebrow:before{
    content:"";display:inline-block;width:36px;height:2px;background:#145A9F
}
.home-title{
    margin:26px 0 18px;
    color:#102F4B;
    font-size:54px;line-height:1.06;
    letter-spacing:-.038em;font-weight:890;
}
.home-title span{color:#145A9F}
.home-deck{
    max-width:760px;
    color:#516A7F;
    font-size:17px;
    line-height:1.9;
}
.home-deck strong{color:#264E6C}
.home-question{
    margin-top:29px;
    padding:18px 0 18px 18px;
    border-left:3px solid #0F9298;
    max-width:730px;
    color:#36566F;
    font-size:13px;line-height:1.8;
    background:linear-gradient(90deg,rgba(15,146,152,.05),transparent)
}
.home-question b{color:#173E5D}
.home-chain{
    margin-top:27px;
    display:grid;grid-template-columns:repeat(5,1fr);
    max-width:760px;
    border-top:1px solid rgba(25,75,112,.14);
    border-bottom:1px solid rgba(25,75,112,.14)
}
.home-chain-cell{padding:13px 10px 12px 0}
.home-chain-no{font-size:9px;font-weight:900;letter-spacing:.13em;color:#9AA8B4}
.home-chain-name{margin-top:5px;font-size:12px;font-weight:820;color:#294A63}

/* ============================================================
   Animated KDP growth schematic
   ============================================================ */
.growth-stage{
    position:absolute;right:0;top:0;
    width:46%;height:100%;
    display:flex;align-items:center;justify-content:center;
    overflow:hidden;
    background:
      radial-gradient(circle at 52% 46%,rgba(43,151,176,.16),transparent 26%),
      radial-gradient(circle at 55% 52%,rgba(20,91,159,.08),transparent 55%);
}
.growth-stage:before{
    content:"";position:absolute;inset:0;
    background:
      linear-gradient(115deg,transparent 0 48%,rgba(255,255,255,.38) 49%,transparent 50%),
      linear-gradient(20deg,transparent 0 68%,rgba(28,91,137,.035) 69%,transparent 70%);
}
.growth-caption{
    position:absolute;right:29px;top:28px;text-align:right;
    z-index:4;
    color:#647E92;
    font-size:9px;font-weight:900;line-height:1.7;letter-spacing:.15em
}
.growth-svg{
    position:relative;z-index:2;
    width:96%;height:92%;
    filter:drop-shadow(0 16px 32px rgba(22,74,112,.10));
}
.g-crystal{
    transform-origin:260px 345px;
    animation:gCrystalPulse 7s ease-in-out infinite;
}
@keyframes gCrystalPulse{
    0%,100%{transform:scaleY(.975)}
    50%{transform:scaleY(1.015)}
}
.g-front{
    stroke-dasharray:11 11;
    animation:gFront 5.5s linear infinite;
}
@keyframes gFront{
    to{stroke-dashoffset:-88}
}
.g-flow{
    stroke-dasharray:6 10;
    animation:gFlow 4.5s linear infinite;
}
@keyframes gFlow{
    to{stroke-dashoffset:-96}
}
.g-crack{
    stroke-dasharray:125;
    stroke-dashoffset:125;
    animation:gCrack 8s ease-in-out infinite;
}
@keyframes gCrack{
    0%,38%{stroke-dashoffset:125;opacity:.08}
    58%,82%{stroke-dashoffset:0;opacity:.82}
    100%{stroke-dashoffset:125;opacity:.08}
}
.g-ion{animation:gIon 6s ease-in-out infinite}
.g-ion.i2{animation-delay:-1.4s}.g-ion.i3{animation-delay:-2.8s}.g-ion.i4{animation-delay:-4.1s}
@keyframes gIon{
    0%{transform:translateY(18px);opacity:.05}
    25%{opacity:.75}
    75%{opacity:.65}
    100%{transform:translateY(-76px);opacity:.05}
}

/* ============================================================
   Status strip
   ============================================================ */
.state-strip{
    margin-top:16px;
    display:grid;grid-template-columns:2fr repeat(4,1fr);
    background:#fff;
    border:1px solid rgba(24,68,105,.10);
    border-radius:14px;
    overflow:hidden
}
.state-cell{padding:16px 19px;border-right:1px solid rgba(24,68,105,.08)}
.state-cell:last-child{border-right:none}
.state-k{font-size:9px;letter-spacing:.14em;font-weight:900;color:#91A0AD}
.state-v{margin-top:4px;font-size:19px;font-weight:850;color:#163650}
.state-n{margin-top:3px;font-size:11px;color:#80909E}

/* ============================================================
   Module index
   ============================================================ */
.entry-group-head{
    margin:0 0 9px;
    padding-bottom:9px;
    border-bottom:1px solid rgba(24,68,105,.10)
}
.entry-group-title{font-size:15px;font-weight:850;color:#1A3B55}
.entry-group-note{margin-top:4px;font-size:10px;line-height:1.55;color:#8795A1}
div[data-testid="stPageLink"] a{
    min-height:43px;
    border-radius:7px!important;
    border:1px solid rgba(24,68,105,.10)!important;
    background:#FCFCFA!important;
    color:#2A485F!important;
    box-shadow:none!important;
    transition:all .15s ease
}
div[data-testid="stPageLink"] a:hover{
    transform:translateX(3px);
    border-color:rgba(20,90,159,.30)!important;
    background:#F3F8FA!important
}
.research-loop{
    display:grid;grid-template-columns:repeat(6,1fr);
    border-top:1px solid rgba(24,68,105,.13);
    border-bottom:1px solid rgba(24,68,105,.13);
    background:#F8F8F5
}
.loop-cell{padding:18px 15px;min-height:105px;border-right:1px solid rgba(24,68,105,.08)}
.loop-cell:last-child{border-right:none}
.loop-no{font-size:9px;font-weight:900;letter-spacing:.13em;color:#A1ADB7}
.loop-title{margin-top:10px;font-size:14px;font-weight:850;color:#1D3E57}
.loop-note{margin-top:5px;font-size:10px;line-height:1.5;color:#7C8D9A}
.home-footnote{
    margin:18px 0 4px;
    padding:13px 16px;
    border-left:3px solid #6E6AB7;
    background:rgba(110,106,183,.035);
    color:#6F7F8D;
    font-size:11px;line-height:1.7
}
@media(max-width:1250px){
    .home-title{font-size:44px}
    .home-copy{width:62%}
    .growth-stage{width:40%;opacity:.72}
    .home-chain{grid-template-columns:repeat(3,1fr)}
    .state-strip{grid-template-columns:repeat(2,1fr)}
    .research-loop{grid-template-columns:repeat(3,1fr)}
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="kdp-home">
  <div class="home-copy">
    <div class="home-eyebrow">KDP 晶体生长 · 缺陷 · 开裂</div>
    <div class="home-title">KDP晶体缺陷与开裂<br><span>研究工作台</span></div>
    <div class="home-deck">
      面向<strong>水溶液法生长KDP晶体</strong>，围绕生长条件、原生缺陷、局部应力与裂纹萌生，
      统一管理文献证据、实验记录、计算任务与阶段判断。
    </div>
    <div class="home-question">
      <b>核心目标：</b>把“文献怎么说、实验发生了什么、理论如何解释、下一步如何验证”
      放在同一条可追溯的研究链上，而不是分散在不同文件、聊天记录和临时笔记中。
    </div>
    <div class="home-chain">
      <div class="home-chain-cell"><div class="home-chain-no">01</div><div class="home-chain-name">证据</div></div>
      <div class="home-chain-cell"><div class="home-chain-no">02</div><div class="home-chain-name">假设</div></div>
      <div class="home-chain-cell"><div class="home-chain-no">03</div><div class="home-chain-name">实验</div></div>
      <div class="home-chain-cell"><div class="home-chain-no">04</div><div class="home-chain-name">计算</div></div>
      <div class="home-chain-cell"><div class="home-chain-no">05</div><div class="home-chain-name">决策</div></div>
    </div>
  </div>

  <div class="growth-stage">
    <div class="growth-caption">KDP GROWTH SCHEMATIC<br>生长界面 · 浓度/温度场 · 裂纹萌生<br>动态示意，非数值模拟结果</div>
    <svg class="growth-svg" viewBox="0 0 520 470" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="crystalFill" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#F8FCFD" stop-opacity=".90"/>
          <stop offset="48%" stop-color="#A8D9E5" stop-opacity=".50"/>
          <stop offset="100%" stop-color="#3E8CC2" stop-opacity=".34"/>
        </linearGradient>
        <linearGradient id="faceBlue" x1="0" x2="1">
          <stop offset="0%" stop-color="#195FA6" stop-opacity=".20"/>
          <stop offset="100%" stop-color="#14A1A4" stop-opacity=".52"/>
        </linearGradient>
        <radialGradient id="solutionFill">
          <stop offset="0%" stop-color="#8DD4DF" stop-opacity=".26"/>
          <stop offset="70%" stop-color="#438FB9" stop-opacity=".13"/>
          <stop offset="100%" stop-color="#205D92" stop-opacity=".03"/>
        </radialGradient>
        <filter id="softGlow">
          <feGaussianBlur stdDeviation="3.2" result="coloredBlur"/>
          <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- solution / vessel -->
      <ellipse cx="270" cy="374" rx="188" ry="56" fill="url(#solutionFill)" stroke="#357FAC" stroke-opacity=".22"/>
      <ellipse cx="270" cy="374" rx="150" ry="38" fill="none" stroke="#2C87A9" stroke-opacity=".22"/>
      <ellipse cx="270" cy="374" rx="112" ry="25" fill="none" stroke="#1A69A2" stroke-opacity=".18"/>

      <!-- convection / supersaturation flux -->
      <path class="g-flow" d="M92 337 C128 284, 163 282, 193 246" fill="none" stroke="#168E9C" stroke-opacity=".55" stroke-width="2"/>
      <path class="g-flow" d="M438 337 C403 286, 376 276, 345 243" fill="none" stroke="#168E9C" stroke-opacity=".50" stroke-width="2"/>
      <path class="g-flow" d="M115 390 C163 421, 207 414, 232 401" fill="none" stroke="#2469A7" stroke-opacity=".32" stroke-width="1.6"/>
      <path class="g-flow" d="M425 390 C380 420, 335 415, 304 401" fill="none" stroke="#2469A7" stroke-opacity=".32" stroke-width="1.6"/>

      <!-- ions / solute -->
      <g class="g-ion i1"><circle cx="144" cy="323" r="5" fill="#0E9AA7" opacity=".55"/></g>
      <g class="g-ion i2"><circle cx="390" cy="315" r="4" fill="#D9852F" opacity=".58"/></g>
      <g class="g-ion i3"><circle cx="185" cy="350" r="3.6" fill="#557BC1" opacity=".50"/></g>
      <g class="g-ion i4"><circle cx="350" cy="348" r="4.4" fill="#0E9AA7" opacity=".48"/></g>

      <!-- growing crystal -->
      <g class="g-crystal">
        <!-- body -->
        <polygon points="205,168 260,111 317,166 334,331 303,371 220,371 188,331"
                 fill="url(#crystalFill)" stroke="#1766A4" stroke-opacity=".72" stroke-width="2.2"/>
        <!-- facets -->
        <polygon points="205,168 260,111 260,177 188,331" fill="#FFFFFF" fill-opacity=".26" stroke="#5BA7C5" stroke-opacity=".36"/>
        <polygon points="260,111 317,166 334,331 260,177" fill="url(#faceBlue)" stroke="#3986AF" stroke-opacity=".32"/>
        <polygon points="188,331 260,177 334,331 303,371 220,371" fill="#2C80B0" fill-opacity=".12" stroke="#2974A0" stroke-opacity=".28"/>

        <!-- growth layers -->
        <path class="g-front" d="M198 214 L260 151 L324 213" fill="none" stroke="#0C99A0" stroke-opacity=".58" stroke-width="1.8"/>
        <path class="g-front" d="M194 251 L260 188 L328 250" fill="none" stroke="#145A9F" stroke-opacity=".48" stroke-width="1.6"/>
        <path class="g-front" d="M191 289 L260 225 L331 288" fill="none" stroke="#0C99A0" stroke-opacity=".42" stroke-width="1.5"/>

        <!-- internal stress field -->
        <path d="M229 183 C241 223, 224 270, 245 332" fill="none" stroke="#6B63B5" stroke-opacity=".34" stroke-width="1.4"/>
        <path d="M289 174 C275 224, 299 274, 279 345" fill="none" stroke="#6B63B5" stroke-opacity=".28" stroke-width="1.4"/>
        <path d="M213 300 C246 286, 285 287, 318 304" fill="none" stroke="#D9852F" stroke-opacity=".34" stroke-width="1.5"/>

        <!-- crack path -->
        <path class="g-crack" d="M292 196 L279 224 L294 247 L273 271 L287 296 L270 320"
              fill="none" stroke="#D97F32" stroke-width="3.2" stroke-linecap="round" filter="url(#softGlow)"/>
      </g>

      <!-- annotations -->
      <g font-family="Microsoft YaHei, sans-serif" font-size="11" fill="#49667D">
        <text x="42" y="278">过饱和溶液 / 对流</text>
        <line x1="145" y1="274" x2="188" y2="260" stroke="#557C97" stroke-opacity=".45"/>

        <text x="352" y="169">生长界面</text>
        <line x1="349" y1="173" x2="317" y2="188" stroke="#557C97" stroke-opacity=".45"/>

        <text x="364" y="248">局部应力场</text>
        <line x1="358" y1="252" x2="303" y2="272" stroke="#6B63B5" stroke-opacity=".45"/>

        <text x="360" y="305">裂纹萌生 / 扩展</text>
        <line x1="354" y1="309" x2="286" y2="296" stroke="#D9852F" stroke-opacity=".52"/>

        <text x="84" y="420">晶体—溶液界面</text>
        <line x1="190" y1="414" x2="221" y2="372" stroke="#557C97" stroke-opacity=".40"/>
      </g>

      <text x="260" y="452" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
            font-size="10" font-weight="700" fill="#758A9B" letter-spacing="2">
        GROWTH → DEFECT → STRESS → CRACK
      </text>
    </svg>
  </div>
</div>

<div class="state-strip">
  <div class="state-cell"><div class="state-k">当前项目</div><div class="state-v">{project_name}</div><div class="state-n">状态：{project_status}</div></div>
  <div class="state-cell"><div class="state-k">项目证据</div><div class="state-v">{counts["evidence"]}</div><div class="state-n">已沉淀文献证据</div></div>
  <div class="state-cell"><div class="state-k">科学假设</div><div class="state-v">{counts["hypothesis"]}</div><div class="state-n">待验证 / 验证中</div></div>
  <div class="state-cell"><div class="state-k">实验记录</div><div class="state-v">{counts["experiment"]}</div><div class="state-n">受保护实验索引</div></div>
  <div class="state-cell"><div class="state-k">计算任务</div><div class="state-v">{counts["calculation"]}</div><div class="state-n">任务与结果</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title(
        "研究模块",
        "按当前科研任务直接进入；所有模块共享同一个项目上下文",
    )

    row1 = st.columns(4, gap="medium")
    with row1[0]:
        _entry_group(
            "项目与总览",
            "从项目状态进入",
            [
                ("overview", "科研驾驶舱", ":material/dashboard:", "查看当前研究状态、证据和专题概览"),
                ("project", "研究总控台", ":material/account_tree:", "管理项目问题、假设与研究记忆"),
            ],
        )
    with row1[1]:
        _entry_group(
            "文献与知识",
            "从证据进入",
            [
                ("literature", "文献中心", ":material/library_books:", "检索、筛选和沉淀KDP文献证据"),
                ("knowledge", "知识图谱", ":material/hub:", "查看来源—机制—结果—文献证据网络"),
                ("topics", "专题调研", ":material/travel_explore:", "围绕具体研究问题形成专题调研"),
                ("compare", "多文献比较", ":material/compare_arrows:", "比较多篇论文的方法、证据与结论"),
            ],
        )
    with row1[2]:
        _entry_group(
            "实验与验证",
            "从现象与变量进入",
            [
                ("diagnosis", "开裂诊断", ":material/crisis_alert:", "排查开裂变量并结合历史实验"),
                ("experiment", "对照实验设计", ":material/fact_check:", "把假设转化为可证伪实验"),
                ("experiment_log", "实验记录与数据积累", ":material/database:", "记录真实实验并为后续机器学习积累数据"),
            ],
        )
    with row1[3]:
        _entry_group(
            "理论与机理",
            "从机制问题进入",
            [
                ("theory", "理论计算规划与分析", ":material/science:", "规划DFT / MD / FEA并回填结果"),
                ("gaps", "研究空白", ":material/lightbulb:", "识别证据薄弱区与待核科学问题"),
            ],
        )

    row2 = st.columns(3, gap="medium")
    with row2[0]:
        _entry_group(
            "方向与决策",
            "从课题选择进入",
            [
                ("direction", "研究方向决策", ":material/explore:", "形成候选课题与阶段路线"),
                ("ai", "AI科研助手", ":material/forum:", "结合项目记忆开展证据整合与科研分析"),
            ],
        )
    with row2[1]:
        _entry_group(
            "成果与复盘",
            "从结果沉淀进入",
            [
                ("reports", "报告中心", ":material/description:", "生成阶段报告与汇报材料"),
                ("audit", "数据审计", ":material/monitor_heart:", "检查证据、分类和项目记录完整性"),
            ],
        )
    with row2[2]:
        st.markdown(
            """
<div class="home-footnote">
  <b>数据与AI边界：</b>
  文献与普通项目记忆可用于智能分析；受保护实验原始数据仍由实验保险库单独控制，
  是否进入外部AI由用户主动决定。
</div>
            """,
            unsafe_allow_html=True,
        )

    section_title(
        "研究闭环",
        "同一科研问题在证据、实验与理论之间反复验证，而不是停留在一次回答",
    )
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
