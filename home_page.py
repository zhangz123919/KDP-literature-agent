
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


def _group(title: str, kicker: str, items):
    st.markdown(
        f"""
<div class="research-entry-head">
  <div class="research-entry-kicker">{kicker}</div>
  <div class="research-entry-title">{title}</div>
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
   HOME — scientific dossier / instrument editorial style
   ============================================================ */
.kdp-cover{
    position:relative;
    min-height:520px;
    overflow:hidden;
    border-radius:24px;
    border:1px solid rgba(22,70,112,.14);
    background:
      linear-gradient(90deg, rgba(248,248,244,.99) 0%, rgba(248,248,244,.98) 47%, rgba(236,244,247,.96) 100%);
    box-shadow:0 22px 55px rgba(26,57,88,.075);
}
.kdp-cover:before{
    content:"";position:absolute;inset:0;
    background-image:
      linear-gradient(rgba(26,72,111,.032) 1px,transparent 1px),
      linear-gradient(90deg,rgba(26,72,111,.032) 1px,transparent 1px);
    background-size:32px 32px;
    pointer-events:none;
}
.cover-left{
    position:relative;z-index:3;
    width:58%;padding:54px 58px 44px 62px;
}
.cover-meta{
    display:flex;align-items:center;gap:13px;
    font-size:10px;letter-spacing:.16em;font-weight:900;color:#55718A;
}
.cover-meta:before{
    content:"";width:31px;height:2px;background:#1359A6;display:inline-block
}
.cover-title{
    margin:25px 0 16px;
    max-width:760px;
    color:#102F4C;
    font-size:55px;line-height:1.07;
    font-weight:880;letter-spacing:-.035em
}
.cover-deck{
    max-width:770px;color:#546E85;font-size:17px;line-height:1.86
}
.cover-axis{
    margin-top:30px;
    display:grid;grid-template-columns:repeat(4,1fr);
    border-top:1px solid rgba(20,70,110,.14);
    border-bottom:1px solid rgba(20,70,110,.14);
}
.cover-axis-cell{padding:13px 14px 13px 0}
.cover-axis-no{font-size:9px;font-weight:900;letter-spacing:.14em;color:#9AA9B5}
.cover-axis-name{margin-top:5px;font-size:12px;font-weight:800;color:#314E67}
.cover-note{
    margin-top:22px;font-size:11px;color:#8191A0;line-height:1.7
}

/* ============================================================
   Animated KDP crystal-structure motif
   Note: a structural motif, not a literal discrete KDP molecule.
   ============================================================ */
.crystal-panel{
    position:absolute;right:0;top:0;width:45%;height:100%;
    display:flex;align-items:center;justify-content:center;
    perspective:1000px;
}
.crystal-panel:before{
    content:"";position:absolute;inset:8% 7% 8% 0;
    background:
      radial-gradient(circle at 52% 48%,rgba(36,151,174,.18),transparent 24%),
      radial-gradient(circle at 52% 48%,rgba(19,89,166,.10),transparent 50%);
    filter:blur(1px);
}
.crystal-caption{
    position:absolute;right:30px;top:28px;text-align:right;
    font-size:9px;line-height:1.65;letter-spacing:.16em;font-weight:850;color:#71899C
}
.crystal-scene{
    position:relative;width:390px;height:390px;
    transform-style:preserve-3d;
}
.crystal-spin{
    position:absolute;left:50%;top:50%;
    width:250px;height:250px;
    transform-style:preserve-3d;
    animation: crystalRotate 18s linear infinite;
}
@keyframes crystalRotate{
    0%{transform:translate(-50%,-50%) rotateX(62deg) rotateZ(0deg)}
    50%{transform:translate(-50%,-50%) rotateX(68deg) rotateZ(180deg)}
    100%{transform:translate(-50%,-50%) rotateX(62deg) rotateZ(360deg)}
}
.crystal-scene:hover .crystal-spin{animation-play-state:paused}
.atom{
    position:absolute;left:50%;top:50%;
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:10px;font-weight:900;
    box-shadow:0 8px 22px rgba(20,60,95,.18);
    transform-style:preserve-3d;
}
.atom-p{
    width:52px;height:52px;background:linear-gradient(145deg,#1359A6,#0E8FA0);
    color:#fff;transform:translate3d(-26px,-26px,38px);
}
.atom-o{
    width:35px;height:35px;background:linear-gradient(145deg,#E8EDF2,#C4D2DE);
    color:#27445F;border:1px solid rgba(255,255,255,.9)
}
.atom-k{
    width:39px;height:39px;background:linear-gradient(145deg,#E6A251,#D77F2C);
    color:white;border:1px solid rgba(255,255,255,.75)
}
.atom-h{
    width:20px;height:20px;background:#F8FBFD;color:#6B7F91;
    border:1px solid rgba(41,102,151,.24);font-size:8px
}
.o1{transform:translate3d(78px,-18px,70px)}
.o2{transform:translate3d(-104px,18px,48px)}
.o3{transform:translate3d(-40px,92px,-44px)}
.o4{transform:translate3d(20px,-108px,-57px)}
.k1{transform:translate3d(-140px,-80px,82px)}
.k2{transform:translate3d(125px,82px,-72px)}
.h1{transform:translate3d(-78px,-38px,24px)}
.h2{transform:translate3d(78px,40px,-14px)}
.bond{
    position:absolute;left:50%;top:50%;height:2px;
    transform-origin:0 50%;
    background:linear-gradient(90deg,rgba(19,89,166,.75),rgba(14,154,167,.24));
    border-radius:999px
}
.b1{width:94px;transform:translate(0,0) rotate(-13deg)}
.b2{width:110px;transform:translate(0,0) rotate(165deg)}
.b3{width:104px;transform:translate(0,0) rotate(103deg)}
.b4{width:112px;transform:translate(0,0) rotate(-79deg)}
.hbond{
    position:absolute;left:50%;top:50%;height:1px;
    border-top:1px dashed rgba(42,118,160,.34);
    transform-origin:0 50%
}
.hb1{width:130px;transform:translate(-65px,-20px) rotate(-16deg)}
.hb2{width:132px;transform:translate(-64px,29px) rotate(18deg)}
.crystal-ring{
    position:absolute;left:50%;top:50%;
    border:1px solid rgba(34,104,154,.12);border-radius:50%;
    transform:translate(-50%,-50%) rotateX(68deg);
}
.cr1{width:230px;height:230px}
.cr2{width:310px;height:310px;transform:translate(-50%,-50%) rotateX(68deg) rotateZ(31deg)}
.cr3{width:365px;height:365px;transform:translate(-50%,-50%) rotateX(72deg) rotateZ(-24deg)}
.crystal-label{
    position:absolute;font-size:9px;font-weight:850;letter-spacing:.13em;color:#7A90A1
}
.cl1{left:14px;top:62px}.cl2{right:2px;top:92px}.cl3{left:20px;bottom:52px}

/* ============================================================
   Project strip
   ============================================================ */
.project-strip{
    margin-top:18px;
    display:grid;grid-template-columns:2fr repeat(4,1fr);
    border:1px solid rgba(23,74,115,.11);
    border-radius:16px;overflow:hidden;background:#fff
}
.project-cell{padding:16px 20px;border-right:1px solid rgba(23,74,115,.08)}
.project-cell:last-child{border-right:none}
.project-k{font-size:9px;letter-spacing:.14em;font-weight:900;color:#91A1AE}
.project-v{margin-top:4px;font-size:19px;font-weight:850;color:#163650}
.project-n{margin-top:2px;font-size:11px;color:#8191A0}

/* ============================================================
   Research navigation
   ============================================================ */
.research-entry-head{
    margin:2px 0 10px;padding-bottom:10px;border-bottom:1px solid rgba(23,74,115,.10)
}
.research-entry-kicker{font-size:9px;font-weight:900;letter-spacing:.15em;color:#0E8996}
.research-entry-title{margin-top:5px;font-size:16px;font-weight:850;color:#1C3A54}
div[data-testid="stPageLink"] a{
    min-height:44px;border-radius:9px!important;
    border:1px solid rgba(23,74,115,.10)!important;
    background:rgba(255,255,255,.82)!important;color:#29475F!important;
    box-shadow:none!important;transition:all .15s ease
}
div[data-testid="stPageLink"] a:hover{
    transform:translateX(2px);
    border-color:rgba(19,89,166,.26)!important;
    background:rgba(244,249,252,.98)!important
}
.research-loop{
    display:grid;grid-template-columns:repeat(6,1fr);
    border:1px solid rgba(23,74,115,.10);border-radius:16px;overflow:hidden;background:#fff
}
.loop-cell{padding:18px 15px;min-height:110px;border-right:1px solid rgba(23,74,115,.08)}
.loop-cell:last-child{border-right:none}
.loop-no{font-size:9px;letter-spacing:.12em;font-weight:900;color:#A0ADBA}
.loop-title{margin-top:11px;font-size:14px;font-weight:850;color:#1E3D56}
.loop-note{margin-top:5px;font-size:10px;line-height:1.55;color:#7B8D9D}
.analysis-layer{
    margin:20px 0 8px;padding:22px 25px;border-left:3px solid #0E8996;
    background:linear-gradient(90deg,rgba(14,137,150,.055),rgba(19,89,166,.018));
    color:#315169
}
.analysis-layer-title{font-size:15px;font-weight:850;color:#1E455F}
.analysis-layer-note{margin-top:5px;font-size:12px;line-height:1.7;color:#6D8193}
@media(max-width:1250px){
    .cover-title{font-size:45px}.cover-left{width:64%}.crystal-panel{width:42%;opacity:.72}
    .research-loop{grid-template-columns:repeat(3,1fr)}
    .project-strip{grid-template-columns:repeat(2,1fr)}
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="kdp-cover">
  <div class="cover-left">
    <div class="cover-meta">KDP RESEARCH DOSSIER · DEFECTS / CRACKING / VALIDATION</div>
    <div class="cover-title">KDP晶体缺陷与开裂<br>研究工作台</div>
    <div class="cover-deck">
      围绕KDP晶体生长、缺陷形成与裂纹萌生问题，统一组织文献证据、研究假设、
      实验记录与理论验证，使研究过程能够持续积累、回查与迭代。
    </div>
    <div class="cover-axis">
      <div class="cover-axis-cell"><div class="cover-axis-no">01</div><div class="cover-axis-name">文献证据</div></div>
      <div class="cover-axis-cell"><div class="cover-axis-no">02</div><div class="cover-axis-name">实验验证</div></div>
      <div class="cover-axis-cell"><div class="cover-axis-no">03</div><div class="cover-axis-name">理论计算</div></div>
      <div class="cover-axis-cell"><div class="cover-axis-no">04</div><div class="cover-axis-name">研究决策</div></div>
    </div>
    <div class="cover-note">
      智能分析作为贯穿式辅助层，用于证据整合、问题拆解、结果解释与下一步规划。
    </div>
  </div>

  <div class="crystal-panel">
    <div class="crystal-caption">KDP STRUCTURAL MOTIF<br>PO₄ TETRAHEDRON · H-BOND NETWORK<br>HOVER TO PAUSE</div>
    <div class="crystal-scene">
      <div class="crystal-ring cr1"></div><div class="crystal-ring cr2"></div><div class="crystal-ring cr3"></div>
      <div class="crystal-label cl1">PO₄ TETRAHEDRON</div>
      <div class="crystal-label cl2">K⁺ ENVIRONMENT</div>
      <div class="crystal-label cl3">H-BOND NETWORK</div>
      <div class="crystal-spin">
        <div class="bond b1"></div><div class="bond b2"></div><div class="bond b3"></div><div class="bond b4"></div>
        <div class="hbond hb1"></div><div class="hbond hb2"></div>
        <div class="atom atom-p">P</div>
        <div class="atom atom-o o1">O</div><div class="atom atom-o o2">O</div>
        <div class="atom atom-o o3">O</div><div class="atom atom-o o4">O</div>
        <div class="atom atom-k k1">K</div><div class="atom atom-k k2">K</div>
        <div class="atom atom-h h1">H</div><div class="atom atom-h h2">H</div>
      </div>
    </div>
  </div>
</div>

<div class="project-strip">
  <div class="project-cell"><div class="project-k">ACTIVE PROJECT</div><div class="project-v">{project_name}</div><div class="project-n">状态：{project_status}</div></div>
  <div class="project-cell"><div class="project-k">EVIDENCE</div><div class="project-v">{counts["evidence"]}</div><div class="project-n">项目证据</div></div>
  <div class="project-cell"><div class="project-k">HYPOTHESES</div><div class="project-v">{counts["hypothesis"]}</div><div class="project-n">科学假设</div></div>
  <div class="project-cell"><div class="project-k">EXPERIMENTS</div><div class="project-v">{counts["experiment"]}</div><div class="project-n">受保护实验索引</div></div>
  <div class="project-cell"><div class="project-k">COMPUTATION</div><div class="project-v">{counts["calculation"]}</div><div class="project-n">计算任务 / 结果</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    section_title(
        "研究入口",
        "按科研任务进入对应模块；站内切换保留当前项目上下文和实验保险库状态",
    )

    row1 = st.columns(4, gap="medium")
    with row1[0]:
        _group(
            "总览与项目",
            "OVERVIEW",
            [
                ("overview", "科研驾驶舱", ":material/dashboard:", "查看项目证据、研究状态与核心概览"),
                ("project", "研究总控台", ":material/account_tree:", "管理项目记忆、假设与研究进度"),
            ],
        )
    with row1[1]:
        _group(
            "文献与知识",
            "EVIDENCE",
            [
                ("literature", "文献中心", ":material/library_books:", "检索、筛选和沉淀项目证据"),
                ("knowledge", "知识图谱", ":material/hub:", "查看缺陷—机制—结果关系"),
                ("topics", "专题调研", ":material/travel_explore:", "按研究主题形成专题证据"),
                ("compare", "多文献比较", ":material/compare_arrows:", "比较多篇论文的方法与结论"),
            ],
        )
    with row1[2]:
        _group(
            "研究问题与决策",
            "DECISION",
            [
                ("direction", "研究方向决策", ":material/explore:", "形成候选课题与研究路线"),
                ("gaps", "研究空白", ":material/lightbulb:", "识别潜在研究空白与待核问题"),
                ("ai", "AI科研助手", ":material/forum:", "结合项目上下文进行科研分析"),
            ],
        )
    with row1[3]:
        _group(
            "实验与验证",
            "EXPERIMENT",
            [
                ("diagnosis", "开裂诊断", ":material/crisis_alert:", "结合证据和历史实验形成排查路径"),
                ("experiment", "对照实验设计", ":material/fact_check:", "形成可证伪的实验方案"),
                ("experiment_log", "实验记录与数据积累", ":material/database:", "进入受保护实验数据空间"),
            ],
        )

    row2 = st.columns([1, 1, 2], gap="medium")
    with row2[0]:
        _group(
            "理论与计算",
            "COMPUTATION",
            [
                ("theory", "理论计算规划与分析", ":material/science:", "组织DFT/MD/FEA计算流程与结果回填"),
            ],
        )
    with row2[1]:
        _group(
            "成果与审计",
            "OUTPUT",
            [
                ("reports", "报告中心", ":material/description:", "整理阶段结果和输出材料"),
                ("audit", "数据审计", ":material/monitor_heart:", "检查数据、证据与项目记录状态"),
            ],
        )
    with row2[2]:
        st.markdown(
            """
<div class="analysis-layer">
  <div class="analysis-layer-title">智能分析层</div>
  <div class="analysis-layer-note">
    负责文献证据整合、跨模块上下文调用、问题拆解、结果解释与下一步规划。
    受保护实验原始数据仍由实验保险库单独控制，不默认进入外部模型。
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    section_title(
        "研究闭环",
        "文献、实验和理论验证共同服务于同一个科学问题，结论再回到下一轮实验与计算",
    )
    st.markdown(
        """
<div class="research-loop">
  <div class="loop-cell"><div class="loop-no">01 · EVIDENCE</div><div class="loop-title">证据建立</div><div class="loop-note">核心论文、方法依据、共识与争议</div></div>
  <div class="loop-cell"><div class="loop-no">02 · QUESTION</div><div class="loop-title">问题与假设</div><div class="loop-note">把现象转化为可验证、可否证的问题</div></div>
  <div class="loop-cell"><div class="loop-no">03 · EXPERIMENT</div><div class="loop-title">实验检验</div><div class="loop-note">条件、现象、失败与对照结果连续积累</div></div>
  <div class="loop-cell"><div class="loop-no">04 · COMPUTATION</div><div class="loop-title">理论验证</div><div class="loop-note">DFT / MD / FEA解释局部机制和应力过程</div></div>
  <div class="loop-cell"><div class="loop-no">05 · SYNTHESIS</div><div class="loop-title">综合判断</div><div class="loop-note">比较文献、实验和计算是否相互支持</div></div>
  <div class="loop-cell"><div class="loop-no">06 · ITERATION</div><div class="loop-title">下一轮迭代</div><div class="loop-note">更新研究假设，规划下一组实验或计算</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )
