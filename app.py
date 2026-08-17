
import streamlit as st

from agent import api_status
from ui import apply_theme, sidebar_ai_status, sidebar_brand
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
    page_title="KDP/DKDP Research OS",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
sidebar_brand()

pages = {
    "总览": [
        st.Page(
            dashboard,
            title="科研驾驶舱",
            icon=":material/dashboard:",
            default=True,
            url_path="overview",
        ),
    ],
    "文献与知识": [
        st.Page(
            literature,
            title="文献中心",
            icon=":material/library_books:",
            url_path="literature",
        ),
        st.Page(
            knowledge_graph,
            title="知识图谱",
            icon=":material/hub:",
            url_path="knowledge",
        ),
        st.Page(
            topic_review,
            title="专题调研",
            icon=":material/travel_explore:",
            url_path="topics",
        ),
        st.Page(
            compare,
            title="多文献比较",
            icon=":material/compare_arrows:",
            url_path="compare",
        ),
    ],
    "实验与计算": [
        st.Page(
            crack_diagnosis,
            title="开裂诊断",
            icon=":material/crisis_alert:",
            url_path="diagnosis",
        ),
        st.Page(
            experiment_design,
            title="对照实验设计",
            icon=":material/fact_check:",
            url_path="experiment",
        ),
        st.Page(
            theory,
            title="理论计算助手",
            icon=":material/science:",
            url_path="theory",
        ),
        st.Page(
            gaps,
            title="研究空白",
            icon=":material/lightbulb:",
            url_path="gaps",
        ),
    ],
    "智能与输出": [
        st.Page(
            ai_agent,
            title="AI 科研智能体",
            icon=":material/smart_toy:",
            url_path="ai",
        ),
        st.Page(
            reports,
            title="报告中心",
            icon=":material/description:",
            url_path="reports",
        ),
        st.Page(
            audit,
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

pg.run()
