from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from research_memory import (
    add_item,
    allow_private_external_ai,
    get_active_project,
    list_items,
    new_experiment_id,
    private_mode_enabled,
    project_context_strip,
    save_attachment,
    storage_security_note,
)
from ui import COLORS, metric_cards, page_header, plotly, section_title, soft_note


def _flatten_experiment(item):
    p = item.get("payload", {}) or {}
    return {
        "实验ID": p.get("experiment_id", item.get("title", "")),
        "日期": p.get("date", ""),
        "研究目的": p.get("objective", ""),
        "过饱和度(%)": p.get("supersaturation_pct"),
        "生长起始温度(℃)": p.get("growth_temp_start"),
        "生长终止温度(℃)": p.get("growth_temp_end"),
        "降温速率(℃/h)": p.get("cooling_rate"),
        "生长时间(h)": p.get("growth_hours"),
        "pH": p.get("ph"),
        "籽晶取向": p.get("seed_orientation", ""),
        "籽晶质量": p.get("seed_quality", ""),
        "固定方式": p.get("fixation", ""),
        "开裂": p.get("cracked", ""),
        "裂纹出现时间": p.get("crack_time", ""),
        "裂纹位置": p.get("crack_location", ""),
        "包裹体": p.get("inclusion", ""),
        "散射点": p.get("scattering", ""),
        "结果摘要": item.get("summary", ""),
    }


def _safe_float(v):
    try:
        if v is None or v == "":
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def _optional_float(v):
    try:
        s = str(v or "").strip()
        return None if not s else float(s)
    except Exception:
        return None


def experiment_lab_page():
    project = get_active_project()
    page_header(
        "实验研究库",
        "把每一批KDP实验的条件、现象、失败和结果结构化沉淀。现在先服务于记录、比较和复盘，数据积累后再升级机器学习与实验条件优化。",
        "EXPERIMENT RESEARCH LOG",
    )
    project_context_strip(show_security=True)

    if not private_mode_enabled():
        st.warning(
            "当前公开/演示部署只启用会话临时记忆，不会持久保存。"
            "**不要录入真实机密配方、参数、原始数据或实验图片。**"
            "真实实验库应在本地电脑或实验室内网启用私密持久化。"
        )
        demo_ok = st.checkbox("我确认这里只录入非机密测试/演示数据", value=False)
    else:
        demo_ok = True
        st.success(
            "本地私密持久化已启用。原始附件只保存到本地指定目录；"
            + ("当前允许发送私密项目上下文到外部AI。" if allow_private_external_ai() else "私密项目上下文默认不会发送给外部AI。")
        )

    section = st.segmented_control(
        "实验研究库",
        ["记录新实验", "历史实验", "实验对比", "数据积累 / 机器学习准备"],
        default="历史实验" if not demo_ok else "记录新实验",
        selection_mode="single",
        label_visibility="collapsed",
        key="experiment_lab_section",
    )

    experiments = list_items("experiment")

    if section == "记录新实验":
        if not demo_ok:
            soft_note("请先确认当前只录入非机密测试数据；真实数据请迁移到本地私密模式。")
            return

        exp_id = new_experiment_id()
        with st.form("new_experiment_form", clear_on_submit=False):
            section_title("基本信息", "一批实验一个Experiment ID，后续图片、表征和计算都挂到同一记录")
            c1, c2, c3 = st.columns([1, 1, 1])
            experiment_id = c1.text_input("实验ID", value=exp_id)
            exp_date = c2.date_input("实验日期", value=date.today())
            operator = c3.text_input("实验人员/代号", placeholder="可填代号")
            objective = st.text_area("本次实验目的 / 要验证的假设", height=80)

            section_title("溶液与生长条件", "尽量填写结构化数值；未来机器学习最依赖这些一致字段")
            a1, a2, a3, a4 = st.columns(4)
            raw_batch = a1.text_input("原料/溶液批次")
            purity = a2.text_input("纯度/纯化信息")
            concentration = a3.text_input("浓度/配比", placeholder="保留原始单位")
            ph_text = a4.text_input("pH", placeholder="不确定可留空")

            b1, b2, b3, b4 = st.columns(4)
            supersaturation_text = b1.text_input("过饱和度(%)", placeholder="不确定可留空")
            t_start_text = b2.text_input("生长起始温度(℃)", placeholder="不确定可留空")
            t_end_text = b3.text_input("生长终止温度(℃)", placeholder="不确定可留空")
            cooling_text = b4.text_input("降温速率(℃/h)", placeholder="例如 0.08")

            c1, c2, c3 = st.columns(3)
            growth_hours_text = c1.text_input("生长时间(h)", placeholder="不确定可留空")
            rotation = c2.text_input("旋转/流动条件")
            temperature_stability = c3.text_input("温度稳定性", placeholder="例如 ±0.02 ℃")

            section_title("籽晶与固定", "这些变量以后可以直接与开裂诊断联动")
            d1, d2, d3, d4 = st.columns(4)
            seed_type = d1.text_input("籽晶类型")
            seed_orientation = d2.text_input("籽晶取向")
            seed_quality = d3.selectbox("籽晶质量", ["未知", "较好", "一般", "存在可见缺陷"])
            fixation = d4.text_input("固定方式/约束")
            seed_size = st.text_input("籽晶尺寸")

            section_title("结果与现象", "失败实验也必须记录；对未来机器学习同样重要")
            e1, e2, e3 = st.columns(3)
            cracked = e1.selectbox("是否开裂", ["未知", "否", "是"])
            inclusion = e2.selectbox("包裹体/夹杂", ["未知", "无明显", "少量", "明显"])
            scattering = e3.selectbox("散射点", ["未知", "无明显", "少量", "明显"])
            crack_time = st.text_input("裂纹首次出现时间/阶段", placeholder="例如：取晶后35 min")
            f1, f2 = st.columns(2)
            crack_location = f1.text_input("裂纹起始位置")
            crack_direction = f2.text_input("裂纹方向/形貌")
            crystal_size = st.text_input("最终晶体尺寸")
            result_summary = st.text_area("现象、结果和本次判断", height=110)

            section_title("自定义参数", "如果有特殊变量可追加，不需要破坏主字段结构")
            custom = st.data_editor(
                pd.DataFrame(
                    [
                        {"参数": "", "值": "", "单位": "", "备注": ""},
                        {"参数": "", "值": "", "单位": "", "备注": ""},
                    ]
                ),
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key="experiment_custom_params",
            )

            if private_mode_enabled():
                uploads = st.file_uploader(
                    "原始附件（仅保存到本地私密目录）",
                    accept_multiple_files=True,
                    type=["png", "jpg", "jpeg", "csv", "xlsx", "txt", "pdf", "dat", "out"],
                )
            else:
                uploads = []
                st.caption("公开/演示模式不提供原始附件上传入口，避免误上传机密文件。")

            submitted = st.form_submit_button("保存实验记录", type="primary")

        if submitted:
            custom_rows = []
            for _, r in custom.iterrows():
                if str(r.get("参数", "")).strip():
                    custom_rows.append({k: str(r.get(k, "")) for k in custom.columns})

            payload = {
                "experiment_id": experiment_id,
                "date": str(exp_date),
                "operator": operator,
                "objective": objective,
                "raw_batch": raw_batch,
                "purity": purity,
                "concentration": concentration,
                "ph": _optional_float(ph_text),
                "supersaturation_pct": _optional_float(supersaturation_text),
                "growth_temp_start": _optional_float(t_start_text),
                "growth_temp_end": _optional_float(t_end_text),
                "cooling_rate": _optional_float(cooling_text),
                "growth_hours": _optional_float(growth_hours_text),
                "rotation": rotation,
                "temperature_stability": temperature_stability,
                "seed_type": seed_type,
                "seed_orientation": seed_orientation,
                "seed_quality": seed_quality,
                "fixation": fixation,
                "seed_size": seed_size,
                "cracked": cracked,
                "inclusion": inclusion,
                "scattering": scattering,
                "crack_time": crack_time,
                "crack_location": crack_location,
                "crack_direction": crack_direction,
                "crystal_size": crystal_size,
                "custom_parameters": custom_rows,
            }
            item = add_item(
                "experiment",
                experiment_id,
                result_summary or objective,
                payload,
                "实验研究库",
                "已完成" if cracked != "未知" else "记录中",
            )

            attachment_msgs = []
            for up in uploads or []:
                res = save_attachment(up, item["id"])
                attachment_msgs.append(res.get("message", ""))

            st.success("实验记录已加入当前研究项目。")
            if attachment_msgs:
                if private_mode_enabled():
                    st.caption(f"附件处理：{len(attachment_msgs)} 个文件已进入本地私密目录。")
                else:
                    st.warning("当前不是私密模式，附件没有落盘保存。")
        return

    flat = pd.DataFrame([_flatten_experiment(x) for x in experiments]) if experiments else pd.DataFrame()

    if section == "历史实验":
        section_title("历史实验", "所有实验都挂在当前项目下；失败实验不会被过滤")
        if len(flat):
            st.dataframe(flat, width="stretch", hide_index=True, height=600)
        else:
            soft_note("当前项目还没有实验记录。")
        return

    if section == "实验对比":
        if len(flat) < 2:
            soft_note("至少需要2条实验记录才能比较。")
            return
        mapping = {f"{r['实验ID']}｜{r['日期']}｜开裂={r['开裂']}": i for i, r in flat.iterrows()}
        selected = st.multiselect("选择2–8组实验", list(mapping), max_selections=8)
        if len(selected) >= 2:
            comp = flat.loc[[mapping[x] for x in selected]].copy()
            st.dataframe(comp, width="stretch", hide_index=True)

            numeric_cols = ["过饱和度(%)", "生长起始温度(℃)", "生长终止温度(℃)", "降温速率(℃/h)", "生长时间(h)", "pH"]
            long_rows = []
            for _, r in comp.iterrows():
                for col in numeric_cols:
                    val = _safe_float(r.get(col))
                    if not np.isnan(val):
                        long_rows.append({"实验ID": r["实验ID"], "变量": col, "值": val})
            if long_rows:
                long = pd.DataFrame(long_rows)
                fig = go.Figure()
                for var, d in long.groupby("变量"):
                    fig.add_trace(go.Scatter(x=d["实验ID"], y=d["值"], mode="lines+markers", name=var))
                fig.update_layout(xaxis_title="实验ID", yaxis_title="原始数值（不同单位，仅看相对变化）")
                plotly(fig, height=470, key="experiment_compare_numeric")
        return

    # ML readiness
    n = len(flat)
    if n == 0:
        metric_cards([
            {"label": "实验记录", "value": 0, "note": "先从规范记录开始", "accent": COLORS["primary"]},
            {"label": "机器学习", "value": "暂不启动", "note": "没有数据不训练模型", "accent": COLORS["orange"]},
        ])
        soft_note("机器学习不是现在强行增加的功能。先把实验字段和结果标签记录一致，数据自然会成为后续模型的训练基础。")
        return

    label_rate = float(flat["开裂"].isin(["是", "否"]).mean() * 100)
    core_cols = ["过饱和度(%)", "生长起始温度(℃)", "降温速率(℃/h)", "生长时间(h)"]
    complete_rate = float(flat[core_cols].notna().mean().mean() * 100) if len(flat) else 0.0

    # purely a data-management readiness indicator, not a ML accuracy estimate
    readiness = min(100.0, n * 2.0) * 0.35 + label_rate * 0.35 + complete_rate * 0.30

    metric_cards(
        [
            {"label": "实验记录", "value": n, "note": "当前项目", "accent": COLORS["primary"]},
            {"label": "结果标签完整", "value": f"{label_rate:.0f}%", "note": "开裂=是/否", "accent": COLORS["teal"]},
            {"label": "核心参数完整", "value": f"{complete_rate:.0f}%", "note": "关键数值字段", "accent": COLORS["cyan"]},
            {"label": "数据准备度", "value": f"{readiness:.0f}/100", "note": "数据管理指标，不是模型准确率", "accent": COLORS["orange"]},
        ]
    )

    section_title("未来机器学习路线", "先统计、再预测、最后才做主动学习/贝叶斯优化")
    if n < 20:
        st.info("当前更适合做描述统计、实验对比和字段规范化。暂不建议把机器学习预测作为科研结论。")
    elif n < 50:
        st.info("可以开始探索简单模型和交叉验证，但应以识别数据问题、变量趋势和不确定性为主。")
    else:
        st.info("数据规模开始具备建立基线模型的条件，但仍需检查批次效应、变量共线性、标签偏差和独立验证集。")

    st.markdown(
        "**推荐演化顺序：** 历史统计 → 相似实验检索 → 基线模型 → 不确定性评估 → 主动学习 / 贝叶斯优化 → 下一组实验建议。"
    )
    soft_note(
        "未来模型输出必须区分“统计关联、模型预测、文献机制支持、对照实验因果验证”。"
        "模型发现相关性不等于已经证明因果关系。"
    )
