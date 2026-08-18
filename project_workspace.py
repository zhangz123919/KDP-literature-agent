from __future__ import annotations

import json
from collections import Counter

import pandas as pd
import streamlit as st

from research_memory import (
    add_item,
    create_project,
    ensure_default_project,
    get_active_project,
    item_counts,
    list_items,
    list_projects,
    private_mode_enabled,
    project_context_strip,
    set_active_project,
    storage_mode_label,
    storage_security_note,
    update_project,
)
from ui import COLORS, metric_cards, page_header, section_title, soft_note


TYPE_LABEL = {
    "hypothesis": "科学假设",
    "evidence": "文献证据",
    "experiment": "实验记录",
    "experiment_plan": "实验方案",
    "diagnosis": "诊断记录",
    "theory_task": "计算任务",
    "theory_result": "计算结果",
    "direction_decision": "方向决策",
    "ai_note": "AI分析",
    "report": "报告",
    "note": "科研备注",
}


def _summary_table(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "时间": x.get("created_at", "")[:19].replace("T", " "),
                "类型": TYPE_LABEL.get(x.get("item_type"), x.get("item_type")),
                "标题": x.get("title", ""),
                "摘要": x.get("summary", ""),
                "来源": x.get("source_module", ""),
                "状态": x.get("status", ""),
            }
            for x in rows
        ]
    )


def project_workspace_page():
    project = ensure_default_project()
    page_header(
        "研究总控台",
        "以大尺寸KDP晶体生长尺度效应为当前主线，统一组织理论基础、文献证据、科学假设、实验记录、缺陷诊断、物性测试、数值计算与阶段决策。",
        "PROJECT RESEARCH HUB",
    )
    project_context_strip(show_security=True)

    section_title(
        "项目协同与研究记忆",
        "各模块围绕同一研究项目读写统一上下文，使文献、假设、实验、计算和决策形成连续研究链",
    )
    st.markdown(
        """
当前平台不再把“开裂”作为孤立终点，而把研究链统一为：  
**晶体尺寸/生长阶段 → 流场与传质 → 表面过饱和度/界面 → 白纹、串丝、包裹体等缺陷 → 热—力响应 → 开裂与工艺优化。**  
文献、实验、物性、CFD/FEA 和 AI 分析都围绕这条链共享项目上下文。
"""
    )

    flow = pd.DataFrame(
        [
            ["KDP理论基础学习", "晶体学 / 生长 / 缺陷 / 热力基础", "学习知识骨架", "理解实验与计算语言"],
            ["大尺寸尺度效应研究", "小—中—大双轨对照 / 相似性", "实验方案", "CFD、缺陷地图、工艺优化"],
            ["文献中心", "核心论文 / 方法依据", "文献证据", "诊断、计算、AI、方向决策"],
            ["缺陷与开裂诊断", "白纹/串丝/开裂变量排查", "诊断记录", "对照实验、下一步验证"],
            ["对照实验设计", "变量、对照组、判据", "实验方案", "实验研究库"],
            ["实验记录与数据积累", "尺寸阶段 / 工艺 / 白纹 / 串丝 / 开裂", "受保护实验索引", "历史比较、未来机器学习"],
            ["物性参数与测试", "热学 / 弹性 / 强度 / 断裂参数", "测试方案", "热—力模型参数库"],
            ["理论计算规划与分析", "CFD / FEA / DFT / MD", "计算任务 / 结果", "机制验证与实验回填"],
            ["AI科研助手", "综合分析 / 下一步建议", "AI分析", "项目决策与报告"],
        ],
        columns=["研究模块", "核心产出", "项目记忆类型", "后续协同环节"],
    )
    st.dataframe(flow, width="stretch", hide_index=True, height=410)

    with st.expander("项目管理", expanded=False):
        projects = list_projects()
        mapping = {p["name"]: p["id"] for p in projects}
        c1, c2 = st.columns([1.2, 1])
        chosen = c1.selectbox(
            "切换项目",
            list(mapping),
            index=max(0, list(mapping.values()).index(project["id"])) if project["id"] in mapping.values() else 0,
        )
        if mapping.get(chosen) != project["id"]:
            set_active_project(mapping[chosen])
            st.rerun()

        new_name = c2.text_input("新项目名称", placeholder="例如：大尺寸KDP尺度效应与缺陷演化")
        new_question = st.text_input(
            "新项目核心问题",
            placeholder="例如：为什么同样名义工艺下，大尺寸KDP更容易出现白纹、串丝或开裂？",
        )
        if st.button("创建新研究项目"):
            if not new_name.strip():
                st.warning("请填写项目名称。")
            else:
                create_project(new_name, new_question)
                st.rerun()

    project = get_active_project()
    counts = item_counts(project["id"])

    metric_cards(
        [
            {"label": "科学假设", "value": counts.get("hypothesis", 0), "note": "可验证/可否证", "accent": COLORS["primary"]},
            {"label": "文献证据", "value": counts.get("evidence", 0), "note": "从文献中心沉淀", "accent": COLORS["teal"]},
            {"label": "受保护实验", "value": counts.get("experiment", 0), "note": "详细数据需二次解锁", "accent": COLORS["orange"]},
            {"label": "诊断与方案", "value": counts.get("diagnosis", 0) + counts.get("experiment_plan", 0), "note": "从问题到验证", "accent": COLORS["cyan"]},
            {"label": "理论计算", "value": counts.get("theory_task", 0) + counts.get("theory_result", 0), "note": "任务与结果闭环", "accent": COLORS["violet"]},
            {"label": "方向决策", "value": counts.get("direction_decision", 0), "note": "保留关键选择", "accent": COLORS["green"]},
        ]
    )

    with st.container(border=True):
        section_title("当前项目定义", "先把研究问题定义清楚，其他模块都从这里读取上下文")
        c1, c2 = st.columns(2)
        name = c1.text_input("项目名称", value=project.get("name", ""), key="project_name_edit")
        status = c2.selectbox(
            "项目状态",
            ["构思中", "进行中", "验证中", "阶段完成", "暂停"],
            index=["构思中", "进行中", "验证中", "阶段完成", "暂停"].index(project.get("status", "进行中")) if project.get("status") in ["构思中", "进行中", "验证中", "阶段完成", "暂停"] else 1,
        )
        question = st.text_area("核心科学问题", value=project.get("question", ""), height=90)
        goal = st.text_area("阶段目标 / 成败判据", value=project.get("goal", ""), height=90)
        if st.button("保存项目定义", type="primary"):
            update_project(project["id"], name=name, status=status, question=question, goal=goal)
            st.success("项目定义已更新，后续模块会读取新的研究上下文。")

    section = st.segmented_control(
        "项目工作区",
        ["研究总览", "科学假设", "证据", "实验", "理论计算", "决策与下一步"],
        default="研究总览",
        selection_mode="single",
        label_visibility="collapsed",
        key="project_workspace_section",
    )

    rows = list_items()

    if section == "研究总览":
        section_title("项目研究链", "记录不是目的，关键是让每一步能够指向下一步")
        st.markdown(
            "**研究问题 → 文献证据 → 科学假设 → 对照实验/理论计算 → 结果回填 → 假设更新 → 研究决策**"
        )
        latest = _summary_table(rows[:20])
        if len(latest):
            st.dataframe(latest, width="stretch", hide_index=True, height=520)
        else:
            soft_note("当前项目还没有沉淀记录。建议先在‘KDP理论基础学习’建立概念骨架，再从‘大尺寸尺度效应研究’建立双轨方案，随后加入文献证据、实验记录和CFD/FEA任务。")
        return

    if section == "科学假设":
        with st.container(border=True):
            h = st.text_input("新增假设", placeholder="例如：晶体尺寸增大通过改变局部传质与表面过饱和度，提高白纹/串丝出现概率")
            rationale = st.text_area("当前依据 / 为什么值得验证", height=90)
            c1, c2 = st.columns(2)
            priority = c1.selectbox("优先级", ["高", "中", "低"])
            hstatus = c2.selectbox("状态", ["待验证", "验证中", "部分支持", "暂不支持", "已否证"])
            falsify = st.text_area("怎样的结果会推翻这个假设？", height=80)
            if st.button("保存科学假设", type="primary"):
                if not h.strip():
                    st.warning("请填写假设。")
                else:
                    add_item(
                        "hypothesis",
                        h,
                        rationale,
                        {
                            "priority": priority,
                            "hypothesis_status": hstatus,
                            "falsification": falsify,
                        },
                        "研究项目工作区",
                        hstatus,
                    )
                    st.success("已保存。开裂诊断、实验设计和AI分析都可以读取这条假设。")
                    st.rerun()
        hrows = _summary_table(list_items("hypothesis"))
        if len(hrows):
            st.dataframe(hrows, width="stretch", hide_index=True, height=500)
        return

    if section == "证据":
        section_title("项目证据", "这里不复制整个文献库，只保存与当前科学问题真正相关的证据")
        ev = _summary_table(list_items("evidence"))
        if len(ev):
            st.dataframe(ev, width="stretch", hide_index=True, height=520)
        else:
            soft_note("尚未保存项目证据。去“文献中心”检索后可一键加入当前项目。")
        return

    if section == "实验":
        exp = list_items("experiment")
        plans = list_items("experiment_plan")
        diags = list_items("diagnosis")
        section_title("实验链", "这里只显示受保护实验索引、诊断和实验方案；真实配方、工艺参数、现象结果需到“实验记录与数据积累”二次解锁后查看")
        table = _summary_table(exp + plans + diags)
        if len(table):
            st.dataframe(table.sort_values("时间", ascending=False), width="stretch", hide_index=True, height=560)
        else:
            soft_note("尚无实验记录。可进入“实验记录与数据积累”创建受密码保护的实验保险库并开始真实数据积累。")
        return

    if section == "理论计算":
        calc = list_items("theory_task") + list_items("theory_result")
        section_title("计算任务与结果", "网站管理研究问题和计算流程，VASP/QE/LAMMPS/COMSOL等外部软件负责真正求解")
        table = _summary_table(calc)
        if len(table):
            st.dataframe(table.sort_values("时间", ascending=False), width="stretch", hide_index=True, height=560)
        else:
            soft_note("尚未保存理论计算任务。可在“理论计算工作流”里生成并保存任务卡。")
        return

    if section == "决策与下一步":
        with st.container(border=True):
            d = st.text_input("记录一个关键决策 / 下一步", placeholder="例如：下一阶段优先验证降温速率×固定方式")
            reason = st.text_area("依据、限制和判据", height=100)
            if st.button("保存研究决策", type="primary"):
                if d.strip():
                    add_item("direction_decision", d, reason, source_module="研究项目工作区")
                    st.success("已保存为项目决策。")
                    st.rerun()
        decision_rows = _summary_table(list_items("direction_decision") + list_items("note"))
        if len(decision_rows):
            st.dataframe(decision_rows, width="stretch", hide_index=True, height=520)
