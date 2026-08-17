
import streamlit as st

from agent import api_status
from ui import apply_theme, sidebar_ai_status, sidebar_brand
from security import safe_page, sidebar_security
from direction_review import direction_review_page
from experiment_lab import experiment_lab_page
from home_page import home_page
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

pages = {
    "总览": [
        st.Page(
            safe_page(home_page),
            title="首页",
            icon=":material/home:",
            default=True,
            url_path="home",
        ),
        st.Page(
            safe_page(dashboard),
            title="科研驾驶舱",
            icon=":material/dashboard:",
            url_path="overview",
        ),
        st.Page(
            safe_page(project_workspace_page),
            title="研究总控台",
            icon=":material/account_tree:",
            url_path="project",
        ),
    ],
    "文献与知识": [
        st.Page(
            safe_page(literature),
            title="文献中心",
            icon=":material/library_books:",
            url_path="literature",
        ),
        st.Page(
            safe_page(knowledge_graph),
            title="知识图谱",
            icon=":material/hub:",
            url_path="knowledge",
        ),
        st.Page(
            safe_page(topic_review),
            title="专题调研",
            icon=":material/travel_explore:",
            url_path="topics",
        ),
        st.Page(
            safe_page(direction_review_page),
            title="研究方向决策",
            icon=":material/explore:",
            url_path="direction",
        ),
        st.Page(
            safe_page(compare),
            title="多文献比较",
            icon=":material/compare_arrows:",
            url_path="compare",
        ),
    ],
    "实验与计算": [
        st.Page(
            safe_page(crack_diagnosis),
            title="开裂诊断",
            icon=":material/crisis_alert:",
            url_path="diagnosis",
        ),
        st.Page(
            safe_page(experiment_design),
            title="对照实验设计",
            icon=":material/fact_check:",
            url_path="experiment",
        ),
        st.Page(
            safe_page(experiment_lab_page),
            title="实验记录与数据积累",
            icon=":material/database:",
            url_path="experiment-log",
        ),
        st.Page(
            safe_page(theory),
            title="理论计算规划与分析",
            icon=":material/science:",
            url_path="theory",
        ),
        st.Page(
            safe_page(gaps),
            title="研究空白",
            icon=":material/lightbulb:",
            url_path="gaps",
        ),
    ],
    "分析与输出": [
        st.Page(
            safe_page(ai_agent),
            title="AI科研助手",
            icon=":material/forum:",
            url_path="ai",
        ),
        st.Page(
            safe_page(reports),
            title="报告中心",
            icon=":material/description:",
            url_path="reports",
        ),
        st.Page(
            safe_page(audit),
            title="数据审计",
            icon=":material/monitor_heart:",
            url_path="audit",
        ),
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
