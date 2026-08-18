
import streamlit as st

from agent import api_status
from ui import apply_theme, sidebar_ai_status, sidebar_brand
from security import safe_page, sidebar_security
from direction_review import direction_review_page
from experiment_lab import experiment_lab_page
from home_page import home_page
from theory_learning import theory_learning_page
from scale_effect import scale_effect_page
from material_properties import material_properties_page
from experiment_vault import sidebar_vault_status
from project_workspace import project_workspace_page
from research_memory import sidebar_project_switcher
from views import (
    ai_agent,
    audit,
    compare,
    crack_diagnosis,
    dashboard,
    experiment_design,
    gaps,
    knowledge_graph,
    literature,
    reports,
    theory,
    topic_review,
)

st.set_page_config(
    page_title="KDP 晶体研究工作台",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
sidebar_brand()
sidebar_project_switcher()

# ------------------------------------------------------------
# IMPORTANT:
# 首页内部跳转统一使用 st.page_link(StreamlitPage)。
# 不再使用 href="/xxx" 直接跳转，避免新建浏览器 Session、
# 丢失 session_state，并减少重复初始化造成的卡顿。
# ------------------------------------------------------------
PAGE = {
    "home": st.Page(
        safe_page(home_page),
        title="首页",
        icon=":material/home:",
        default=True,
        url_path="home",
    ),
    "overview": st.Page(
        safe_page(dashboard),
        title="科研驾驶舱",
        icon=":material/dashboard:",
        url_path="overview",
    ),
    "project": st.Page(
        safe_page(project_workspace_page),
        title="研究总控台",
        icon=":material/account_tree:",
        url_path="project",
    ),
    "learn": st.Page(
        safe_page(theory_learning_page),
        title="KDP理论基础学习",
        icon=":material/menu_book:",
        url_path="theory-learning",
    ),
    "literature": st.Page(
        safe_page(literature),
        title="文献中心",
        icon=":material/library_books:",
        url_path="literature",
    ),
    "knowledge": st.Page(
        safe_page(knowledge_graph),
        title="知识图谱",
        icon=":material/hub:",
        url_path="knowledge",
    ),
    "topics": st.Page(
        safe_page(topic_review),
        title="专题调研",
        icon=":material/travel_explore:",
        url_path="topics",
    ),
    "direction": st.Page(
        safe_page(direction_review_page),
        title="研究方向决策",
        icon=":material/explore:",
        url_path="direction",
    ),
    "compare": st.Page(
        safe_page(compare),
        title="多文献比较",
        icon=":material/compare_arrows:",
        url_path="compare",
    ),
    "scale": st.Page(
        safe_page(scale_effect_page),
        title="大尺寸尺度效应研究",
        icon=":material/straighten:",
        url_path="scale-effect",
    ),
    "diagnosis": st.Page(
        safe_page(crack_diagnosis),
        title="缺陷与开裂诊断",
        icon=":material/crisis_alert:",
        url_path="diagnosis",
    ),
    "experiment": st.Page(
        safe_page(experiment_design),
        title="对照实验设计",
        icon=":material/fact_check:",
        url_path="experiment",
    ),
    "experiment_log": st.Page(
        safe_page(experiment_lab_page),
        title="实验记录与数据积累",
        icon=":material/database:",
        url_path="experiment-log",
    ),
    "properties": st.Page(
        safe_page(material_properties_page),
        title="物性参数与测试",
        icon=":material/biotech:",
        url_path="material-properties",
    ),
    "theory": st.Page(
        safe_page(theory),
        title="理论计算规划与分析",
        icon=":material/science:",
        url_path="theory",
    ),
    "gaps": st.Page(
        safe_page(gaps),
        title="研究空白",
        icon=":material/lightbulb:",
        url_path="gaps",
    ),
    "ai": st.Page(
        safe_page(ai_agent),
        title="AI科研助手",
        icon=":material/forum:",
        url_path="ai",
    ),
    "reports": st.Page(
        safe_page(reports),
        title="报告中心",
        icon=":material/description:",
        url_path="reports",
    ),
    "audit": st.Page(
        safe_page(audit),
        title="数据审计",
        icon=":material/monitor_heart:",
        url_path="audit",
    ),
}

# StreamlitPage 可以由 st.page_link 直接用于站内切换。
# 保存到当前 Session，供首页作为真正的内部导航使用。
st.session_state["_kdp_nav_pages"] = PAGE

pages = {
    "总览": [
        PAGE["home"],
        PAGE["overview"],
        PAGE["project"],
    ],
    "理论基础": [
        PAGE["learn"],
    ],
    "文献与知识": [
        PAGE["literature"],
        PAGE["knowledge"],
        PAGE["topics"],
        PAGE["direction"],
        PAGE["compare"],
    ],
    "实验与计算": [
        PAGE["scale"],
        PAGE["diagnosis"],
        PAGE["experiment"],
        PAGE["experiment_log"],
        PAGE["properties"],
        PAGE["theory"],
        PAGE["gaps"],
    ],
    "分析与输出": [
        PAGE["ai"],
        PAGE["reports"],
        PAGE["audit"],
    ],
}

pg = st.navigation(
    pages,
    position="sidebar",
    expanded=True,
)

ok, model = api_status()
sidebar_ai_status(ok, model)
sidebar_security()
sidebar_vault_status()

pg.run()
