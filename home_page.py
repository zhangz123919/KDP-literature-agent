
from __future__ import annotations

import html

import streamlit as st

from research_memory import get_active_project, list_items
from ui import COLORS, section_title


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
    st.page_link(
        page,
        label=label,
        icon=icon,
        help=help_text,
        width="stretch",
    )


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
.kdp-home-hero{
    position:relative;overflow:hidden;min-height:455px;
    border:1px solid rgba(19,89,166,.16);border-radius:28px;
    padding:56px 62px 46px;
    background:
        radial-gradient(circle at 84% 27%,rgba(14,154,167,.13),transparent 28%),
        radial-gradient(circle at 70% 76%,rgba(47,115,201,.10),transparent 31%),
        linear-gradient(135deg,rgba(255,255,252,.99),rgba(242,247,251,.98));
    box-shadow:0 18px 50px rgba(32,67,103,.08);
}
.kdp-home-hero:before{
    content:"";position:absolute;inset:0;
    background-image:
      linear-gradient(rgba(19,89,166,.03) 1px,transparent 1px),
      linear-gradient(90deg,rgba(19,89,166,.03) 1px,transparent 1px);
    background-size:38px 38px;
    mask-image:linear-gradient(to right,rgba(0,0,0,.45),rgba(0,0,0,.08));
    pointer-events:none
}
.home-kicker{
    position:relative;z-index:2;display:inline-flex;padding:7px 12px;border-radius:999px;
    border:1px solid rgba(19,89,166,.18);background:rgba(255,255,255,.72);
    font-size:11px;font-weight:850;letter-spacing:.14em;color:#1359A6
}
.home-title{
    position:relative;z-index:2;margin:24px 0 12px;max-width:820px;
    font-size:55px;line-height:1.08;font-weight:860;letter-spacing:-.035em;color:#102D49
}
.home-sub{
    position:relative;z-index:2;max-width:835px;color:#5A7088;font-size:18px;line-height:1.8
}
.home-tags{position:relative;z-index:2;margin-top:27px;display:flex;flex-wrap:wrap;gap:9px}
.home-tag{
    padding:8px 12px;border-radius:10px;background:rgba(255,255,255,.78);
    border:1px solid rgba(19,89,166,.12);color:#36526E;font-size:12px;font-weight:720
}
.home-orbit{position:absolute;right:38px;top:32px;width:410px;height:410px;pointer-events:none}
.home-orbit .ring{
    position:absolute;left:50%;top:50%;border:1px solid rgba(19,89,166,.16);
    border-radius:50%;transform:translate(-50%,-50%) rotateX(68deg)
}
.home-orbit .r1{width:170px;height:170px}
.home-orbit .r2{width:260px;height:260px;transform:translate(-50%,-50%) rotateX(66deg) rotateZ(32deg)}
.home-orbit .r3{width:350px;height:350px;transform:translate(-50%,-50%) rotateX(70deg) rotateZ(-27deg)}
.home-orbit .core{
    position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
    width:108px;height:108px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(145deg,#1359A6,#0E9AA7);color:white;font-size:31px;font-weight:880;
    box-shadow:0 15px 34px rgba(19,89,166,.24)
}
.home-orbit .dot{position:absolute;width:13px;height:13px;border-radius:50%;box-shadow:0 5px 18px rgba(19,89,166,.22)}
.home-orbit .d1{left:87px;top:92px;background:#D9852F}
.home-orbit .d2{right:71px;top:129px;background:#0E9AA7}
.home-orbit .d3{left:60px;bottom:109px;background:#6B63B5}
.home-orbit .d4{right:102px;bottom:55px;background:#1359A6}
.home-orbit .label{position:absolute;color:#6E8194;font-size:10px;font-weight:800;letter-spacing:.12em}
.home-orbit .l1{left:25px;top:67px}.home-orbit .l2{right:12px;top:105px}
.home-orbit .l3{left:8px;bottom:79px}.home-orbit .l4{right:48px;bottom:29px}
.home-metrics{
    margin-top:18px;display:grid;grid-template-columns:2fr repeat(4,1fr);
    border:1px solid rgba(19,89,166,.12);border-radius:18px;overflow:hidden;background:rgba(255,255,255,.76)
}
.home-metric{padding:17px 20px;border-right:1px solid rgba(19,89,166,.09)}
.home-metric:last-child{border-right:none}
.home-metric-label{font-size:10px;letter-spacing:.12em;font-weight:820;color:#7B8EA2}
.home-metric-value{margin-top:5px;font-size:20px;font-weight:840;color:#173650}
.home-metric-note{margin-top:3px;font-size:11px;color:#8090A0}
.home-loop{
    display:grid;grid-template-columns:repeat(6,1fr);gap:0;margin:12px 0 20px;
    border:1px solid rgba(19,89,166,.12);border-radius:20px;overflow:hidden;background:#fff
}
.home-loop-cell{padding:20px 16px;min-height:112px;border-right:1px solid rgba(19,89,166,.09)}
.home-loop-cell:last-child{border-right:none}
.home-loop-id{font-size:10px;font-weight:900;letter-spacing:.1em;color:#99A9B8}
.home-loop-title{margin-top:12px;font-size:15px;font-weight:850;color:#173650}
.home-loop-note{margin-top:6px;font-size:11px;line-height:1.55;color:#75879A}
.nav-panel{
    margin-top:8px;padding:20px 22px 10px;border-radius:20px;
    border:1px solid rgba(19,89,166,.11);
    background:linear-gradient(135deg,rgba(255,255,255,.98),rgba(244,248,251,.96))
}
.nav-kicker{font-size:10px;font-weight:900;letter-spacing:.14em;color:#0E9AA7}
.nav-title{font-size:22px;font-weight:870;color:#173650;margin-top:6px}
.nav-note{font-size:12px;color:#718499;line-height:1.65;margin:5px 0 13px}
.ai-strip{
    margin:22px 0 6px;padding:26px 29px;border-radius:20px;
    background:linear-gradient(135deg,#102F4E,#1359A6 58%,#0E8795);color:#fff;
    display:flex;justify-content:space-between;gap:24px;align-items:center
}
.ai-strip-title{font-size:21px;font-weight:850}
.ai-strip-note{margin-top:6px;color:rgba(255,255,255,.74);font-size:13px;line-height:1.68}
.ai-strip-mark{font-size:39px;font-weight:900;letter-spacing:.06em;opacity:.17}
div[data-testid="stPageLink"] a{
    min-height:48px;border-radius:12px!important;
    border:1px solid rgba(19,89,166,.12)!important;
    background:#fff!important;color:#274662!important;
    box-shadow:0 5px 15px rgba(31,68,103,.035);
    transition:all .16s ease
}
div[data-testid="stPageLink"] a:hover{
    transform:translateY(-2px);border-color:rgba(19,89,166,.27)!important;
    box-shadow:0 10px 24px rgba(31,68,103,.08)
}
@media(max-width:1200px){
    .home-title{font-size:45px;max-width:700px}.home-orbit{right:-60px;opacity:.48}
    .home-loop{grid-template-columns:repeat(3,1fr)}
    .home-metrics{grid-template-columns:repeat(2,1fr)}
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="kdp-home-hero">
  <div class="home-kicker">KDP · RESEARCH WORKSPACE</div>
  <div class="home-title">KDP晶体缺陷与开裂<br>研究工作台</div>
  <div class="home-sub">
    面向KDP晶体生长、缺陷形成与开裂机制研究，将文献证据、科学假设、实验记录、
    理论计算与AI分析组织为连续、可追溯的研究流程。
  </div>
  <div class="home-tags">
    <span class="home-tag">Evidence · 文献证据</span>
    <span class="home-tag">Hypothesis · 科学假设</span>
    <span class="home-tag">Experiment · 实验验证</span>
    <span class="home-tag">Computation · 理论计算</span>
    <span class="home-tag">Decision · 研究决策</span>
  </div>
  <div class="home-orbit">
    <div class="ring r1"></div><div class="ring r2"></div><div class="ring r3"></div>
    <div class="core">KDP</div>
    <div class="dot d1"></div><div class="dot d2"></div><div class="dot d3"></div><div class="dot d4"></div>
    <div class="label l1">DEFECT</div><div class="label l2">MECHANISM</div>
    <div class="label l3">EXPERIMENT</div><div class="label l4">COMPUTATION</div>
  </div>
</div>
<div class="home-metrics">
  <div class="home-metric"><div class="home-metric-label">ACTIVE PROJECT</div><div class="home-metric-value">{project_name}</div><div class="home-metric-note">状态：{project_status}</div></div>
  <div class="home-metric"><div class="home-metric-label">EVIDENCE</div><div class="home-metric-value">{counts["evidence"]}</div><div class="home-metric-note">项目证据</div></div>
  <div class="home-metric"><div class="home-metric-label">HYPOTHESES</div><div class="home-metric-value">{counts["hypothesis"]}</div><div class="home-metric-note">科学假设</div></div>
  <div class="home-metric"><div class="home-metric-label">EXPERIMENTS</div><div class="home-metric-value">{counts["experiment"]}</div><div class="home-metric-note">受保护实验索引</div></div>
  <div class="home-metric"><div class="home-metric-label">COMPUTATION</div><div class="home-metric-value">{counts["calculation"]}</div><div class="home-metric-note">计算任务 / 结果</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title(
        "快速进入",
        "以下入口使用Streamlit站内导航，不创建新的浏览器会话，项目记忆和实验保险库状态会继续保留",
    )
    st.markdown('<div class="nav-panel"><div class="nav-kicker">CORE ENTRY</div><div class="nav-title">从科研任务直接进入</div><div class="nav-note">首页负责导航，数据分析在对应模块按需加载。</div></div>', unsafe_allow_html=True)

    r1 = st.columns(3, gap="medium")
    with r1[0]:
        _page_link("overview", "科研驾驶舱", ":material/dashboard:", "查看核心文献、专题活跃度与研究状态")
    with r1[1]:
        _page_link("project", "研究总控台", ":material/account_tree:", "管理项目记忆、假设与研究进度")
    with r1[2]:
        _page_link("ai", "AI科研助手", ":material/forum:", "结合当前项目上下文开展科研分析")

    r2 = st.columns(3, gap="medium")
    with r2[0]:
        _page_link("literature", "文献中心", ":material/library_books:", "检索、筛选并沉淀项目证据")
    with r2[1]:
        _page_link("experiment_log", "实验记录与数据积累", ":material/database:", "进入受保护实验数据空间")
    with r2[2]:
        _page_link("theory", "理论计算规划与分析", ":material/science:", "组织DFT/MD/FEA计算研究流程")

    section_title(
        "研究闭环",
        "同一科研问题从证据、假设和验证继续迭代，而不是停留在一次AI回答",
    )
    st.markdown(
        """
<div class="home-loop">
  <div class="home-loop-cell"><div class="home-loop-id">01 · EVIDENCE</div><div class="home-loop-title">文献证据</div><div class="home-loop-note">核心论文、方法依据、共识与争议</div></div>
  <div class="home-loop-cell"><div class="home-loop-id">02 · HYPOTHESIS</div><div class="home-loop-title">科学假设</div><div class="home-loop-note">形成可验证、可否证的机制问题</div></div>
  <div class="home-loop-cell"><div class="home-loop-id">03 · EXPERIMENT</div><div class="home-loop-title">实验验证</div><div class="home-loop-note">条件、现象、失败与对照结果</div></div>
  <div class="home-loop-cell"><div class="home-loop-id">04 · COMPUTATION</div><div class="home-loop-title">理论验证</div><div class="home-loop-note">DFT / MD / FEA与外部求解器衔接</div></div>
  <div class="home-loop-cell"><div class="home-loop-id">05 · AI SYNTHESIS</div><div class="home-loop-title">AI综合分析</div><div class="home-loop-note">读取允许访问的项目研究上下文</div></div>
  <div class="home-loop-cell"><div class="home-loop-id">06 · DECISION</div><div class="home-loop-title">下一步决策</div><div class="home-loop-note">课题、实验、表征与计算继续迭代</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    pcols = st.columns(4, gap="medium")
    with pcols[0]:
        st.markdown("**领域与选题**  \n文献 → 专题 → 潜在空白 → 方向决策")
        _page_link("direction", "进入研究方向决策 →")
    with pcols[1]:
        st.markdown("**开裂与实验**  \n现象 → 诊断 → 历史实验 → 对照验证")
        _page_link("diagnosis", "进入开裂诊断 →")
    with pcols[2]:
        st.markdown("**机理与计算**  \n假设 → 方法文献 → DFT/MD/FEA → 验证")
        _page_link("theory", "进入理论计算 →")
    with pcols[3]:
        st.markdown("**数据驱动**  \n实验积累 → 数据质量 → ML → 条件优化")
        _page_link("experiment_log", "进入实验数据空间 →")

    st.markdown(
        """
<div class="ai-strip">
  <div>
    <div class="ai-strip-title">AI 是平台的智能引擎，而不是独立聊天窗口</div>
    <div class="ai-strip-note">
      AI科研助手围绕当前研究项目调用文献证据、科学假设和允许访问的研究记忆，
      用于解释、比较、归纳与规划下一步；受保护实验原始数据仍由实验保险库权限控制。
    </div>
  </div>
  <div class="ai-strip-mark">AI × KDP</div>
</div>
        """,
        unsafe_allow_html=True,
    )
