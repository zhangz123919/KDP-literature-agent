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
        "它本身不替代文献检索、实验或计算；它负责让所有模块围绕同一个KDP科学问题共享上下文、保存关键记录，并知道研究下一步走到哪里。",
        "PROJECT RESEARCH HUB",
    )
    project_context_strip(show_security=True)

    section_title("这个页面到底有什么用？", "把原本彼此独立的页面变成同一个研究项目中的连续步骤")
    st.markdown(
        """
**研究总控台 = 全站共享记忆 + 研究进度中枢。**

- 在**文献中心**找到的重要论文，可以保存成当前项目的“证据”；
- 在**开裂诊断**得到的根因排序，可以保存成“诊断记录”；
- 在**对照实验设计**形成的方案，可以保存成“实验方案”；
- 在**实验记录与数据积累**中的真实实验，可以保存成“实验记录”；
- 在**理论计算规划与分析**中的任务和结果，可以保存成“计算任务/计算结果”；
- **AI科研助手、研究方向决策**以后读取的是这些已经沉淀的项目上下文，而不是每次从零开始。
"""
    )

    flow = pd.DataFrame(
        [
            ["文献中心", "核心论文 / 方法依据", "文献证据", "诊断、计算、AI、方向决策"],
            ["开裂诊断", "风险排序 / 根因假设", "诊断记录", "对照实验、下一步验证"],
            ["对照实验设计", "变量、对照组、判据", "实验方案", "实验研究库"],
            ["实验记录与数据积累", "真实条件 / 现象 / 失败", "受保护实验索引", "历史比较、未来机器学习"],
            ["理论计算规划与分析", "模型、任务、结果", "计算任务 / 结果", "AI综合、机制验证"],
            ["AI科研助手", "综合分析 / 下一步建议", "AI分析", "项目决策与报告"],
        ],
        columns=["模块", "产生什么", "保存到项目中的记忆", "以后由谁调用"],
    )
    st.dataframe(flow, width="stretch", hide_index=True, height=286)

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

        new_name = c2.text_input("新项目名称", placeholder="例如：KDP降温开裂机制")
        new_question = st.text_input(
            "新项目核心问题",
            placeholder="例如：为什么KDP晶体在取晶后30–60 min出现裂纹？",
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
            soft_note("当前项目还没有沉淀记录。建议从“文献中心加入1篇证据 → 建立1条假设 → 生成1个验证实验/计算任务”开始，随后这个页面就会自动汇总整个研究链。")
        return

    if section == "科学假设":
        with st.container(border=True):
            h = st.text_input("新增假设", placeholder="例如：降温过快通过热应力增加裂纹萌生概率")
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
