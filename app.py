
import streamlit as st

from agent import api_status
from ui import apply_theme, sidebar_ai_status, sidebar_brand
from security import safe_page, sidebar_security
from direction_review import direction_review_page
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

pages = {
    "总览": [
        st.Page(
            safe_page(dashboard),
            title="科研驾驶舱",
            icon=":material/dashboard:",
            default=True,
            url_path="overview",
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
            safe_page(theory),
            title="理论计算助手",
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
            title="科研问答",
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

pg.run()
