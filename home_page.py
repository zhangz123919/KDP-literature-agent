
from __future__ import annotations

import html

import streamlit as st

from research_memory import get_active_project, list_items
from ui import COLORS, page_header, section_title


def _count(kind: str) -> int:
    try:
        return len(list_items(kind))
    except Exception:
        return 0


def _safe(s) -> str:
    return html.escape(str(s or ""))


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

    # Lightweight self-contained styling; does not load the literature Excel.
    st.markdown(
        """
<style>
.kdp-home-hero{
    position:relative;
    overflow:hidden;
    min-height:470px;
    border:1px solid rgba(19,89,166,.16);
    border-radius:28px;
    padding:58px 64px 46px 64px;
    background:
        radial-gradient(circle at 82% 28%, rgba(14,154,167,.13), transparent 28%),
        radial-gradient(circle at 68% 72%, rgba(47,115,201,.11), transparent 31%),
        linear-gradient(135deg, rgba(255,255,252,.98), rgba(242,247,251,.98));
    box-shadow:0 18px 50px rgba(32,67,103,.08);
}
.kdp-home-hero:before{
    content:"";
    position:absolute;inset:0;
    background-image:
      linear-gradient(rgba(19,89,166,.032) 1px, transparent 1px),
      linear-gradient(90deg, rgba(19,89,166,.032) 1px, transparent 1px);
    background-size:38px 38px;
    mask-image:linear-gradient(to right, rgba(0,0,0,.45), rgba(0,0,0,.08));
    pointer-events:none;
}
.home-kicker{
    position:relative;z-index:3;
    display:inline-flex;align-items:center;gap:9px;
    padding:7px 12px;border-radius:999px;
    border:1px solid rgba(19,89,166,.18);
    background:rgba(255,255,255,.68);
    font-size:11px;font-weight:800;letter-spacing:.14em;color:#1359A6;
}
.home-title{
    position:relative;z-index:3;
    margin:24px 0 12px;
    max-width:820px;
    font-size:56px;line-height:1.08;font-weight:840;
    letter-spacing:-.035em;color:#102D49;
}
.home-sub{
    position:relative;z-index:3;
    max-width:830px;
    color:#5A7088;font-size:18px;line-height:1.8;
}
.home-logic{
    position:relative;z-index:3;
    margin-top:28px;
    display:flex;flex-wrap:wrap;gap:9px;
}
.home-chip{
    padding:8px 12px;border-radius:10px;
    background:rgba(255,255,255,.78);
    border:1px solid rgba(19,89,166,.12);
    color:#36526E;font-size:12px;font-weight:700;
}
.home-orbit{
    position:absolute;right:34px;top:34px;
    width:410px;height:410px;opacity:.95;
    pointer-events:none;
}
.home-orbit .ring{
    position:absolute;left:50%;top:50%;
    border:1px solid rgba(19,89,166,.16);
    border-radius:50%;
    transform:translate(-50%,-50%) rotateX(68deg);
}
.home-orbit .r1{width:170px;height:170px}
.home-orbit .r2{width:260px;height:260px;transform:translate(-50%,-50%) rotateX(66deg) rotateZ(32deg)}
.home-orbit .r3{width:350px;height:350px;transform:translate(-50%,-50%) rotateX(70deg) rotateZ(-27deg)}
.home-orbit .core{
    position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
    width:108px;height:108px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    background:linear-gradient(145deg,#1359A6,#0E9AA7);
    color:white;font-size:31px;font-weight:850;letter-spacing:.05em;
    box-shadow:0 15px 34px rgba(19,89,166,.24);
}
.home-orbit .dot{position:absolute;width:13px;height:13px;border-radius:50%;box-shadow:0 5px 18px rgba(19,89,166,.22)}
.home-orbit .d1{left:87px;top:92px;background:#D9852F}
.home-orbit .d2{right:71px;top:129px;background:#0E9AA7}
.home-orbit .d3{left:60px;bottom:109px;background:#6B63B5}
.home-orbit .d4{right:102px;bottom:55px;background:#1359A6}
.home-orbit .label{
    position:absolute;color:#6E8194;font-size:10px;font-weight:800;letter-spacing:.12em
}
.home-orbit .l1{left:25px;top:67px}.home-orbit .l2{right:12px;top:105px}
.home-orbit .l3{left:8px;bottom:79px}.home-orbit .l4{right:48px;bottom:29px}
.home-project-bar{
    margin-top:18px;
    display:grid;grid-template-columns:2fr repeat(4,1fr);
    border:1px solid rgba(19,89,166,.12);
    border-radius:18px;overflow:hidden;background:rgba(255,255,255,.72)
}
.home-project-cell{padding:17px 20px;border-right:1px solid rgba(19,89,166,.09)}
.home-project-cell:last-child{border-right:none}
.home-project-label{font-size:10px;letter-spacing:.12em;font-weight:800;color:#7B8EA2}
.home-project-value{margin-top:5px;font-size:20px;font-weight:820;color:#173650}
.home-project-note{margin-top:3px;font-size:11px;color:#8090A0}
.home-flow{
    display:grid;grid-template-columns:repeat(6,1fr);gap:0;margin:12px 0 28px;
    border:1px solid rgba(19,89,166,.12);border-radius:20px;overflow:hidden;background:white
}
.home-flow-step{position:relative;padding:22px 17px;min-height:118px;border-right:1px solid rgba(19,89,166,.09)}
.home-flow-step:last-child{border-right:none}
.home-flow-num{font-size:10px;font-weight:900;letter-spacing:.1em;color:#99A9B8}
.home-flow-title{margin-top:13px;font-size:15px;font-weight:850;color:#173650}
.home-flow-note{margin-top:6px;font-size:11px;line-height:1.55;color:#75879A}
.home-route-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.home-route{
    padding:24px 22px;border-radius:18px;background:#FFF;
    border:1px solid rgba(19,89,166,.11);
    box-shadow:0 8px 24px rgba(31,68,103,.045)
}
.home-route-id{font-size:10px;font-weight:850;letter-spacing:.14em;color:#1359A6}
.home-route-title{margin-top:11px;font-size:18px;font-weight:850;color:#173650}
.home-route-note{margin-top:7px;font-size:12px;line-height:1.65;color:#708397}
.home-engine{
    margin:18px 0 8px;padding:28px 30px;border-radius:20px;
    background:linear-gradient(135deg,#102F4E,#1359A6 58%,#0E8795);
    color:white;display:flex;align-items:center;justify-content:space-between;gap:24px
}
.home-engine-title{font-size:22px;font-weight:850}
.home-engine-note{margin-top:7px;color:rgba(255,255,255,.74);font-size:13px;line-height:1.7;max-width:900px}
.home-engine-mark{font-size:42px;font-weight:900;letter-spacing:.06em;opacity:.18}
@media (max-width:1200px){
    .home-title{font-size:45px;max-width:700px}
    .home-orbit{right:-55px;opacity:.5}
    .home-route-grid{grid-template-columns:repeat(2,1fr)}
    .home-flow{grid-template-columns:repeat(3,1fr)}
    .home-project-bar{grid-template-columns:repeat(2,1fr)}
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
  <div class="home-logic">
    <span class="home-chip">Evidence 文献证据</span>
    <span class="home-chip">Hypothesis 科学假设</span>
    <span class="home-chip">Experiment 实验验证</span>
    <span class="home-chip">Computation 理论计算</span>
    <span class="home-chip">Decision 研究决策</span>
  </div>
  <div class="home-orbit">
    <div class="ring r1"></div><div class="ring r2"></div><div class="ring r3"></div>
    <div class="core">KDP</div>
    <div class="dot d1"></div><div class="dot d2"></div><div class="dot d3"></div><div class="dot d4"></div>
    <div class="label l1">DEFECT</div><div class="label l2">MECHANISM</div>
    <div class="label l3">EXPERIMENT</div><div class="label l4">COMPUTATION</div>
  </div>
</div>
<div class="home-project-bar">
  <div class="home-project-cell">
    <div class="home-project-label">ACTIVE PROJECT</div>
    <div class="home-project-value">{project_name}</div>
    <div class="home-project-note">状态：{project_status}</div>
  </div>
  <div class="home-project-cell">
    <div class="home-project-label">EVIDENCE</div>
    <div class="home-project-value">{counts["evidence"]}</div>
    <div class="home-project-note">项目证据</div>
  </div>
  <div class="home-project-cell">
    <div class="home-project-label">HYPOTHESES</div>
    <div class="home-project-value">{counts["hypothesis"]}</div>
    <div class="home-project-note">科学假设</div>
  </div>
  <div class="home-project-cell">
    <div class="home-project-label">EXPERIMENTS</div>
    <div class="home-project-value">{counts["experiment"]}</div>
    <div class="home-project-note">受保护实验索引</div>
  </div>
  <div class="home-project-cell">
    <div class="home-project-label">COMPUTATION</div>
    <div class="home-project-value">{counts["calculation"]}</div>
    <div class="home-project-note">计算任务 / 结果</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title(
        "研究闭环",
        "平台的价值不在于模块数量，而在于同一科研问题能够从证据走向验证，再回到下一轮决策",
    )
    st.markdown(
        """
<div class="home-flow">
  <div class="home-flow-step"><div class="home-flow-num">01 · EVIDENCE</div><div class="home-flow-title">文献证据</div><div class="home-flow-note">核心论文、方法依据、共识与争议</div></div>
  <div class="home-flow-step"><div class="home-flow-num">02 · HYPOTHESIS</div><div class="home-flow-title">科学假设</div><div class="home-flow-note">形成可验证、可否证的机制问题</div></div>
  <div class="home-flow-step"><div class="home-flow-num">03 · EXPERIMENT</div><div class="home-flow-title">实验验证</div><div class="home-flow-note">记录条件、现象、失败与对照结果</div></div>
  <div class="home-flow-step"><div class="home-flow-num">04 · COMPUTATION</div><div class="home-flow-title">理论验证</div><div class="home-flow-note">DFT / MD / FEA与专业求解器衔接</div></div>
  <div class="home-flow-step"><div class="home-flow-num">05 · AI SYNTHESIS</div><div class="home-flow-title">AI综合分析</div><div class="home-flow-note">调用项目记忆，整合证据与研究状态</div></div>
  <div class="home-flow-step"><div class="home-flow-num">06 · DECISION</div><div class="home-flow-title">下一步决策</div><div class="home-flow-note">课题、实验、表征和计算继续迭代</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title(
        "四条研究路径",
        "从不同科研任务进入，最终都沉淀到同一个项目研究记忆",
    )
    st.markdown(
        """
<div class="home-route-grid">
  <div class="home-route"><div class="home-route-id">PATH 01</div><div class="home-route-title">领域与选题</div><div class="home-route-note">文献中心 → 专题调研 → 潜在研究空白 → 研究方向决策</div></div>
  <div class="home-route"><div class="home-route-id">PATH 02</div><div class="home-route-title">开裂与实验</div><div class="home-route-note">实验现象 → 开裂诊断 → 历史实验 → 对照实验设计 → 结果回填</div></div>
  <div class="home-route"><div class="home-route-id">PATH 03</div><div class="home-route-title">机理与计算</div><div class="home-route-note">科学假设 → 方法文献 → DFT / MD / FEA规划 → 外部求解 → 结果验证</div></div>
  <div class="home-route"><div class="home-route-id">PATH 04</div><div class="home-route-title">数据驱动</div><div class="home-route-note">真实实验积累 → 数据质量 → 统计规律 → 机器学习 → 条件优化</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="home-engine">
  <div>
    <div class="home-engine-title">AI 是平台的智能引擎，而不是独立聊天窗口</div>
    <div class="home-engine-note">
      AI科研助手围绕当前研究项目调用文献证据、项目假设、允许访问的研究记忆与分析结果，
      用于解释、比较、归纳和规划下一步；受保护实验原始数据仍按实验保险库权限控制。
    </div>
  </div>
  <div class="home-engine-mark">AI × KDP</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "从左侧导航进入科研驾驶舱、研究总控台、文献中心、实验记录、理论计算或AI科研助手。"
    )
