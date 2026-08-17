
from __future__ import annotations

import json
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from experiment_vault import (
    add_attachment,
    attachment_bytes,
    audit_log,
    create_vault,
    current_vault,
    duplicate_record,
    export_blob,
    get_record,
    has_session_vault,
    import_vault,
    list_attachments,
    list_records,
    lock_vault,
    lockout_seconds,
    password_policy_ok,
    project_matches,
    remove_attachment,
    restore_record,
    rotate_password,
    sanitized_summary,
    save_record,
    trash_record,
    unlock_session_vault,
    update_record,
    vault_stats,
    vault_unlocked,
)
from research_memory import (
    add_item,
    get_active_project,
    list_items,
    new_experiment_id,
    update_item,
)
from ui import COLORS, metric_cards, page_header, plotly, section_title, soft_note


INPUT_FIELDS = [
    "supersaturation_pct",
    "growth_temp_start",
    "growth_temp_end",
    "cooling_rate",
    "growth_hours",
    "ph",
    "seed_type",
    "seed_orientation",
    "seed_quality",
    "fixation",
    "temperature_stability",
    "rotation",
]

TARGET_FIELDS = [
    "cracked",
    "crack_latency_min",
    "crack_count",
    "final_mass_g",
    "final_length_mm",
    "final_width_mm",
    "final_height_mm",
    "inclusion",
    "scattering",
]


def _optional_float(v):
    try:
        s = str(v or "").strip()
        return None if not s else float(s)
    except Exception:
        return None


def _safe_float(v):
    try:
        if v is None or v == "":
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def _display_value(v):
    if v is None:
        return ""
    return str(v)


def _ensure_project_index(rec, status="受保护"):
    """
    只把“实验ID + 受保护状态”写入普通项目记忆。
    配方、温度、速率、附件、真实结果等敏感字段只留在实验保险库。
    """
    ref = rec.get("id", "")
    existing = [
        x for x in list_items("experiment")
        if (x.get("payload", {}) or {}).get("vault_ref") == ref
    ]

    payload = {
        "vault_ref": ref,
        "protected": True,
        "experiment_id": rec.get("experiment_id", ""),
    }
    title = f"{rec.get('experiment_id','实验记录')} · 受保护"
    summary = "详细实验参数、配方、现象、结果和附件保存在独立实验数据保险库中。"

    if existing:
        update_item(
            existing[0]["id"],
            title=title,
            summary=summary,
            payload=payload,
            status=status,
        )
        return existing[0]

    return add_item(
        "experiment",
        title,
        summary,
        payload,
        "实验数据保险库",
        status,
    )


def _sync_indexes():
    for rec in list_records(include_trash=True):
        _ensure_project_index(
            rec,
            status="回收站" if rec.get("status") == "trash" else "受保护",
        )


def _flatten(rec):
    p = rec.get("payload", {}) or {}
    return {
        "保险库记录ID": rec.get("id", ""),
        "实验ID": rec.get("experiment_id", ""),
        "日期": p.get("date", ""),
        "研究目的": p.get("objective", ""),
        "原料/溶液批次": p.get("raw_batch", ""),
        "纯度/纯化": p.get("purity", ""),
        "浓度/配比": p.get("concentration", ""),
        "pH": p.get("ph"),
        "过饱和度(%)": p.get("supersaturation_pct"),
        "生长起始温度(℃)": p.get("growth_temp_start"),
        "生长终止温度(℃)": p.get("growth_temp_end"),
        "降温速率(℃/h)": p.get("cooling_rate"),
        "生长时间(h)": p.get("growth_hours"),
        "旋转/流动": p.get("rotation", ""),
        "温度稳定性": p.get("temperature_stability", ""),
        "籽晶类型": p.get("seed_type", ""),
        "籽晶取向": p.get("seed_orientation", ""),
        "籽晶质量": p.get("seed_quality", ""),
        "籽晶尺寸": p.get("seed_size", ""),
        "固定方式": p.get("fixation", ""),
        "取晶温度(℃)": p.get("takeout_temp"),
        "环境温度(℃)": p.get("ambient_temp"),
        "冷却方式": p.get("post_cooling", ""),
        "过程异常": p.get("process_anomaly", ""),
        "开裂": p.get("cracked", ""),
        "裂纹延迟(min)": p.get("crack_latency_min"),
        "裂纹数量": p.get("crack_count"),
        "裂纹位置": p.get("crack_location", ""),
        "裂纹方向/形貌": p.get("crack_direction", ""),
        "包裹体": p.get("inclusion", ""),
        "散射点": p.get("scattering", ""),
        "最终质量(g)": p.get("final_mass_g"),
        "最终长度(mm)": p.get("final_length_mm"),
        "最终宽度(mm)": p.get("final_width_mm"),
        "最终高度(mm)": p.get("final_height_mm"),
        "显微摘要": p.get("microscopy_summary", ""),
        "XRD摘要": p.get("xrd_summary", ""),
        "Raman摘要": p.get("raman_summary", ""),
        "FTIR摘要": p.get("ftir_summary", ""),
        "当前假设": p.get("current_hypothesis", ""),
        "下一步": p.get("next_step", ""),
        "结果摘要": rec.get("summary", ""),
        "修订版本": rec.get("revision", 1),
        "更新时间": rec.get("updated_at", ""),
    }


def _vault_entry(project):
    page_header(
        "实验记录与数据积累",
        "这里允许记录真实实验数据，但它在全站采用最高权限：独立二次密码、会话隔离、自动锁定、加密备份，且不会自动发送给外部AI。",
        "PROTECTED EXPERIMENT DATA",
    )

    section_title("为什么这个模块值得保留？", "它不是为了现在炫机器学习，而是从第一批实验开始积累未来真正可学习的实验经验")
    st.markdown(
        """
**现在：** 记录真实实验 → 成功/失败对比 → 找历史相似实验 → 复盘变量变化。  
**以后：** 数据清洗 → 基线机器学习 → 不确定性 → 主动学习/贝叶斯优化 → 推荐下一组实验。  

这里与普通AI最大的区别是：**AI没有你自己的连续实验历史，而这个模块会逐步形成你自己的KDP实验经验库。**
"""
    )

    st.info(
        "当前仍然没有独立后端数据库：真实数据只存在当前浏览会话的受保护保险库中。"
        "为了跨会话长期积累，请每次结束前下载 `.kdpvault` 加密备份；下次重新导入即可继续。"
        "明天导师若要求改为内网/后端，只需替换存储层，不需要推翻数据结构和页面。"
    )

    if vault_unlocked():
        return True

    wait = lockout_seconds()
    if wait > 0:
        st.error(f"连续密码错误次数过多，请约 {wait} 秒后再试。")
        return False

    tabs = st.tabs(["创建新的实验保险库", "打开已有加密保险库", "重新解锁当前会话"])

    with tabs[0]:
        st.caption("每个使用者可以设置自己的实验保险库密码；密码不会写入GitHub或普通项目记忆。")
        p1 = st.text_input("设置实验保险库密码", type="password", key="vault_create_pwd")
        p2 = st.text_input("再次输入密码", type="password", key="vault_create_pwd2")
        ok, msg = password_policy_ok(p1) if p1 else (False, "")
        if p1:
            st.caption("密码规则：至少10位，建议字母 + 数字 + 符号。" + ("" if ok else f" 当前：{msg}"))
        if st.button("创建并解锁实验保险库", type="primary", key="vault_create_btn"):
            if p1 != p2:
                st.error("两次密码不一致。")
            else:
                try:
                    create_vault(p1, project.get("id", ""), project.get("name", ""))
                    st.success("已创建。真实实验数据现在可以在当前会话中录入。")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with tabs[1]:
        up = st.file_uploader(
            "选择 `.kdpvault` 加密备份",
            type=["kdpvault"],
            key="vault_import_file",
        )
        pwd = st.text_input("保险库密码", type="password", key="vault_import_pwd")
        if st.button("解密并导入", type="primary", key="vault_import_btn"):
            if not up:
                st.warning("请先选择保险库文件。")
            else:
                try:
                    import_vault(
                        up.getvalue(),
                        pwd,
                        bind_project_id=project.get("id", ""),
                        bind_project_name=project.get("name", ""),
                    )
                    _sync_indexes()
                    st.success("导入成功，已绑定到当前研究项目。")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with tabs[2]:
        if not has_session_vault():
            st.caption("当前会话没有已锁定的保险库。")
        else:
            pwd = st.text_input("输入密码重新解锁", type="password", key="vault_unlock_pwd")
            if st.button("重新解锁", type="primary", key="vault_unlock_btn"):
                try:
                    unlock_session_vault(pwd)
                    _sync_indexes()
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    return False


def _security_header(project):
    v = current_vault() or {}
    stats = vault_stats()
    same = str(v.get("project_id", "")) == str(project.get("id", ""))

    c1, c2, c3, c4 = st.columns([1.25, 1, 1, 1])
    c1.success("实验保险库：已解锁")
    c2.metric("受保护实验", stats["records"])
    c3.metric("附件", stats["attachments"])
    c4.metric("项目绑定", "正常" if same else "需检查")

    left, right = st.columns([1, 1])
    with left:
        st.caption(
            "全量实验数据不会自动进入AI上下文；普通项目工作区只保存一个“受保护实验索引”。"
        )
    with right:
        if st.button("立即锁定实验数据", key="vault_lock_top"):
            lock_vault("页面手动锁定")
            st.rerun()

    if not same:
        st.warning(
            f"当前保险库原绑定项目：{v.get('project_name','')}。"
            "建议重新导入并绑定到当前项目，避免不同项目实验混用。"
        )


def _new_record_form(project):
    exp_id = new_experiment_id()

    with st.form("secure_new_experiment", clear_on_submit=False):
        section_title("1｜基本信息", "一批实验一个Experiment ID；后续附件、表征、修订记录都挂在这里")
        a1, a2, a3 = st.columns(3)
        experiment_id = a1.text_input("实验ID", value=exp_id)
        exp_date = a2.date_input("实验日期", value=date.today())
        operator = a3.text_input("实验人员/代号")
        objective = st.text_area("本次实验目的 / 要验证的假设", height=80)

        section_title("2｜原料与溶液", "这些是未来机器学习的重要输入特征 X")
        b1, b2, b3, b4 = st.columns(4)
        raw_batch = b1.text_input("原料/溶液批次")
        purity = b2.text_input("纯度/纯化/过滤信息")
        concentration = b3.text_input("浓度/配比（保留原始单位）")
        ph_text = b4.text_input("pH")

        c1, c2, c3, c4 = st.columns(4)
        supersaturation_text = c1.text_input("过饱和度(%)")
        t_start_text = c2.text_input("生长起始温度(℃)")
        t_end_text = c3.text_input("生长终止温度(℃)")
        cooling_text = c4.text_input("降温速率(℃/h)")

        d1, d2, d3 = st.columns(3)
        growth_hours_text = d1.text_input("生长时间(h)")
        rotation = d2.text_input("旋转/流动条件")
        temp_stability = d3.text_input("温度稳定性", placeholder="例如 ±0.02 ℃")

        section_title("3｜籽晶与机械约束", "以后可以与开裂诊断、有限元和历史实验自动关联")
        e1, e2, e3, e4 = st.columns(4)
        seed_type = e1.text_input("籽晶类型")
        seed_orientation = e2.text_input("籽晶取向")
        seed_quality = e3.selectbox("籽晶质量", ["未知", "较好", "一般", "存在可见缺陷"])
        fixation = e4.text_input("固定方式/约束")
        seed_size = st.text_input("籽晶尺寸")

        section_title("4｜取晶、冷却与异常事件", "把实验过程本身也记录下来，避免只留下最终结果")
        f1, f2, f3 = st.columns(3)
        takeout_temp_text = f1.text_input("取晶温度(℃)")
        ambient_temp_text = f2.text_input("环境温度(℃)")
        post_cooling = f3.text_input("出炉/取晶后冷却方式")
        process_anomaly = st.text_area(
            "过程异常 / 设备波动 / 临时操作",
            height=70,
            placeholder="例如温度波动、断电、设备报警、人工干预等；没有可留空",
        )

        section_title("5｜结果与现象", "成功和失败实验都要保存；失败实验对未来建模非常有价值")
        g1, g2, g3 = st.columns(3)
        cracked = g1.selectbox("是否开裂", ["未知", "否", "是"])
        inclusion = g2.selectbox("包裹体/夹杂", ["未知", "无明显", "少量", "明显"])
        scattering = g3.selectbox("散射点", ["未知", "无明显", "少量", "明显"])

        h1, h2, h3 = st.columns(3)
        crack_latency_text = h1.text_input("裂纹延迟时间(min)")
        crack_count_text = h2.text_input("裂纹数量")
        crack_time = h3.text_input("裂纹首次出现阶段", placeholder="例如：取晶后35 min")

        i1, i2 = st.columns(2)
        crack_location = i1.text_input("裂纹起始位置")
        crack_direction = i2.text_input("裂纹方向/形貌")

        section_title("6｜机器学习友好的连续结果 Y", "文字描述保留给人看，数值字段才能真正用于回归、分类和优化")
        j1, j2, j3, j4 = st.columns(4)
        final_mass_text = j1.text_input("最终晶体质量(g)")
        final_length_text = j2.text_input("最终长度(mm)")
        final_width_text = j3.text_input("最终宽度(mm)")
        final_height_text = j4.text_input("最终高度(mm)")
        crystal_size = st.text_input("最终尺寸原始描述（可选）")

        section_title("7｜表征结果", "以后可继续扩展为结构化XRD/Raman特征；当前先保存摘要与附件")
        k1, k2 = st.columns(2)
        microscopy_summary = k1.text_area("显微/裂纹图像摘要", height=80)
        xrd_summary = k2.text_area("XRD 摘要", height=80)
        l1, l2 = st.columns(2)
        raman_summary = l1.text_area("Raman 摘要", height=80)
        ftir_summary = l2.text_area("FTIR 摘要", height=80)
        other_char = st.text_area("其他表征", height=70)

        section_title("8｜科研判断与下一步", "记录当时的判断，而不是以后只记得“最后结论”")
        result_summary = st.text_area("本次现象 / 结果摘要", height=90)
        current_hypothesis = st.text_area("当前工作假设", height=70)
        next_step = st.text_area("下一步实验 / 表征 / 计算", height=70)

        section_title("9｜自定义变量", "新的工艺变量也可直接加入数据字典，并标记未来是输入X还是结果Y")
        custom = st.data_editor(
            pd.DataFrame(
                [
                    {"参数": "", "值": "", "单位": "", "角色": "输入特征 X", "备注": ""},
                    {"参数": "", "值": "", "单位": "", "角色": "输入特征 X", "备注": ""},
                ]
            ),
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="secure_custom_params",
        )

        uploads = st.file_uploader(
            "原始附件（会随 `.kdpvault` 一起加密）",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "csv", "xlsx", "txt", "pdf", "dat", "out"],
            help="当前版本不把附件写到GitHub或普通项目记忆。单文件/总量受保险库限制。",
        )

        submitted = st.form_submit_button("保存到受保护实验保险库", type="primary")

    if not submitted:
        return

    custom_rows = []
    for _, row in custom.iterrows():
        if str(row.get("参数", "")).strip():
            custom_rows.append({k: str(row.get(k, "")) for k in custom.columns})

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
        "temperature_stability": temp_stability,
        "seed_type": seed_type,
        "seed_orientation": seed_orientation,
        "seed_quality": seed_quality,
        "fixation": fixation,
        "seed_size": seed_size,
        "takeout_temp": _optional_float(takeout_temp_text),
        "ambient_temp": _optional_float(ambient_temp_text),
        "post_cooling": post_cooling,
        "process_anomaly": process_anomaly,
        "cracked": cracked,
        "inclusion": inclusion,
        "scattering": scattering,
        "crack_latency_min": _optional_float(crack_latency_text),
        "crack_count": _optional_float(crack_count_text),
        "crack_time": crack_time,
        "crack_location": crack_location,
        "crack_direction": crack_direction,
        "final_mass_g": _optional_float(final_mass_text),
        "final_length_mm": _optional_float(final_length_text),
        "final_width_mm": _optional_float(final_width_text),
        "final_height_mm": _optional_float(final_height_text),
        "crystal_size": crystal_size,
        "microscopy_summary": microscopy_summary,
        "xrd_summary": xrd_summary,
        "raman_summary": raman_summary,
        "ftir_summary": ftir_summary,
        "other_characterization": other_char,
        "result_summary": result_summary,
        "current_hypothesis": current_hypothesis,
        "next_step": next_step,
        "custom_parameters": custom_rows,
    }

    try:
        rec = save_record(payload, summary=result_summary or objective)
        _ensure_project_index(rec)

        saved = 0
        for up in uploads or []:
            add_attachment(up, rec["id"])
            saved += 1

        st.success(f"已安全保存实验记录 {experiment_id}。附件 {saved} 个。")
        st.warning("当前没有后端数据库。请在离开页面前到“备份与安全”下载最新加密保险库。")
    except Exception as exc:
        st.error(f"保存失败：{exc}")


def _records_table(records):
    if not records:
        return pd.DataFrame()
    return pd.DataFrame([_flatten(x) for x in records])


def _history():
    records = list_records()
    if not records:
        soft_note("当前保险库还没有实验记录。")
        return

    flat = _records_table(records)
    section_title("我的实验", "详细参数只有保险库解锁后才能查看；失败实验不会被过滤")
    show_cols = [
        "实验ID", "日期", "研究目的", "开裂", "裂纹延迟(min)",
        "包裹体", "散射点", "最终质量(g)", "最终长度(mm)",
        "修订版本", "更新时间",
    ]
    st.dataframe(
        flat[[c for c in show_cols if c in flat.columns]],
        width="stretch",
        hide_index=True,
        height=430,
    )

    mapping = {
        f"{r.get('experiment_id','')}｜{(r.get('payload',{}) or {}).get('date','')}｜rev{r.get('revision',1)}": r["id"]
        for r in records
    }
    chosen = st.selectbox("打开一条实验记录", list(mapping))
    rec = get_record(mapping[chosen])
    p = rec.get("payload", {})

    tabs = st.tabs(["完整记录", "补充/修订结果", "复制为下一组实验", "附件", "版本历史"])

    with tabs[0]:
        detail = pd.DataFrame(
            [{"字段": k, "值": json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else _display_value(v)}
             for k, v in p.items()]
        )
        st.dataframe(detail, width="stretch", hide_index=True, height=560)
        st.caption("完整记录只在实验保险库解锁后显示，不进入普通项目记忆。")

    with tabs[1]:
        st.caption("每次修订都会保留上一版本快照，便于追溯实验记录是何时补充或修改的。")
        with st.form("update_secure_record"):
            a1, a2, a3 = st.columns(3)
            cracked = a1.selectbox(
                "是否开裂",
                ["未知", "否", "是"],
                index=["未知", "否", "是"].index(p.get("cracked", "未知")) if p.get("cracked", "未知") in ["未知", "否", "是"] else 0,
            )
            latency = a2.text_input("裂纹延迟(min)", value=_display_value(p.get("crack_latency_min")))
            count = a3.text_input("裂纹数量", value=_display_value(p.get("crack_count")))

            b1, b2 = st.columns(2)
            location = b1.text_input("裂纹位置", value=_display_value(p.get("crack_location")))
            direction = b2.text_input("裂纹方向/形貌", value=_display_value(p.get("crack_direction")))

            c1, c2 = st.columns(2)
            inclusion = c1.selectbox(
                "包裹体",
                ["未知", "无明显", "少量", "明显"],
                index=["未知", "无明显", "少量", "明显"].index(p.get("inclusion", "未知")) if p.get("inclusion", "未知") in ["未知", "无明显", "少量", "明显"] else 0,
            )
            scattering = c2.selectbox(
                "散射点",
                ["未知", "无明显", "少量", "明显"],
                index=["未知", "无明显", "少量", "明显"].index(p.get("scattering", "未知")) if p.get("scattering", "未知") in ["未知", "无明显", "少量", "明显"] else 0,
            )

            d1, d2, d3, d4 = st.columns(4)
            mass = d1.text_input("最终质量(g)", value=_display_value(p.get("final_mass_g")))
            length = d2.text_input("最终长度(mm)", value=_display_value(p.get("final_length_mm")))
            width = d3.text_input("最终宽度(mm)", value=_display_value(p.get("final_width_mm")))
            height = d4.text_input("最终高度(mm)", value=_display_value(p.get("final_height_mm")))

            result_summary = st.text_area("结果摘要", value=rec.get("summary", ""), height=90)
            hypothesis = st.text_area("当前假设", value=p.get("current_hypothesis", ""), height=70)
            next_step = st.text_area("下一步", value=p.get("next_step", ""), height=70)

            submitted = st.form_submit_button("保存新版本", type="primary")

        if submitted:
            updates = {
                "cracked": cracked,
                "crack_latency_min": _optional_float(latency),
                "crack_count": _optional_float(count),
                "crack_location": location,
                "crack_direction": direction,
                "inclusion": inclusion,
                "scattering": scattering,
                "final_mass_g": _optional_float(mass),
                "final_length_mm": _optional_float(length),
                "final_width_mm": _optional_float(width),
                "final_height_mm": _optional_float(height),
                "current_hypothesis": hypothesis,
                "next_step": next_step,
            }
            update_record(rec["id"], updates, summary=result_summary)
            _ensure_project_index(get_record(rec["id"]))
            st.success("已保存新版本，上一版本已进入历史记录。")
            st.rerun()

    with tabs[2]:
        new_id = st.text_input(
            "新实验ID",
            value=new_experiment_id(),
            key="copy_new_experiment_id",
        )
        st.caption("会继承原料、生长条件、籽晶和固定方式，并自动清空结果字段。这样最适合连续单变量实验。")
        if st.button("复制为新实验基线", type="primary", key="copy_record_btn"):
            new_rec = duplicate_record(rec["id"], new_id, clear_results=True)
            _ensure_project_index(new_rec)
            st.success(f"已创建 {new_rec['experiment_id']}。")
            st.rerun()

    with tabs[3]:
        uploads = st.file_uploader(
            "补充附件",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "csv", "xlsx", "txt", "pdf", "dat", "out"],
            key=f"att_{rec['id']}",
        )
        if st.button("保存附件", key=f"save_att_{rec['id']}"):
            try:
                for up in uploads or []:
                    add_attachment(up, rec["id"])
                st.success("附件已写入受保护保险库。")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        atts = list_attachments(rec["id"])
        if atts:
            for att in atts:
                c1, c2, c3 = st.columns([2.2, 1, 1])
                c1.write(att["name"])
                c2.caption(f"{att['size_bytes']/1024:.1f} KB")
                c3.download_button(
                    "下载",
                    attachment_bytes(att["id"]),
                    file_name=att["name"],
                    key=f"dl_{att['id']}",
                )
                if st.button("从保险库删除附件", key=f"rm_{att['id']}"):
                    remove_attachment(att["id"])
                    st.rerun()
        else:
            st.caption("暂无附件。")

    with tabs[4]:
        versions = rec.get("versions", [])
        if versions:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "版本": x.get("revision"),
                            "时间": x.get("time"),
                            "当时摘要": x.get("summary", ""),
                        }
                        for x in reversed(versions)
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("当前还没有历史修订版本。")

    c1, c2 = st.columns([1, 5])
    if c1.button("移入回收站", key=f"trash_{rec['id']}"):
        trash_record(rec["id"])
        _ensure_project_index(get_record(rec["id"]), status="回收站")
        st.rerun()


def _compare():
    records = list_records()
    if len(records) < 2:
        soft_note("至少需要2条有效实验记录。")
        return

    flat = _records_table(records)
    mapping = {
        f"{r['实验ID']}｜{r['日期']}｜开裂={r['开裂']}": i
        for i, r in flat.iterrows()
    }
    selected = st.multiselect(
        "选择2–8组实验",
        list(mapping),
        max_selections=8,
    )
    if len(selected) < 2:
        return

    comp = flat.loc[[mapping[x] for x in selected]].copy()
    st.dataframe(comp, width="stretch", hide_index=True, height=430)

    compare_fields = [
        "过饱和度(%)", "生长起始温度(℃)", "生长终止温度(℃)",
        "降温速率(℃/h)", "生长时间(h)", "pH",
        "籽晶类型", "籽晶取向", "籽晶质量", "固定方式",
        "取晶温度(℃)", "环境温度(℃)", "冷却方式",
    ]

    diffs = []
    same = []
    for col in compare_fields:
        values = ["" if pd.isna(v) else str(v) for v in comp[col].tolist()]
        unique = list(dict.fromkeys(values))
        if len(unique) > 1:
            diffs.append({"变量": col, "各实验值": " ｜ ".join(values)})
        elif unique and unique[0] != "":
            same.append(col)

    section_title("真正发生变化的变量", "对连续对照实验尤其重要：系统直接告诉你这几组实验之间到底改了什么")
    if diffs:
        st.dataframe(pd.DataFrame(diffs), width="stretch", hide_index=True)
    else:
        st.info("所选实验在当前结构化字段里没有检测到输入变量差异。")
    if same:
        st.caption("保持一致的已记录变量：" + "、".join(same))

    numeric_cols = [
        "过饱和度(%)", "生长起始温度(℃)", "生长终止温度(℃)",
        "降温速率(℃/h)", "生长时间(h)", "pH",
        "裂纹延迟(min)", "最终质量(g)", "最终长度(mm)",
    ]
    rows = []
    for _, r in comp.iterrows():
        for col in numeric_cols:
            val = _safe_float(r.get(col))
            if not np.isnan(val):
                rows.append({"实验ID": r["实验ID"], "变量": col, "值": val})
    if rows:
        long = pd.DataFrame(rows)
        fig = go.Figure()
        for var, d in long.groupby("变量"):
            fig.add_trace(
                go.Scatter(
                    x=d["实验ID"],
                    y=d["值"],
                    mode="lines+markers",
                    name=var,
                )
            )
        fig.update_layout(
            xaxis_title="实验ID",
            yaxis_title="原始数值（不同单位，仅用于查看变化趋势）",
        )
        plotly(fig, height=470, key="secure_experiment_compare")


def _data_quality():
    records = list_records()
    if not records:
        soft_note("当前没有实验记录。")
        return

    flat = _records_table(records)
    section_title("数据质量", "机器学习之前，先检查记录是否完整、一致、可追溯")

    important = [
        "过饱和度(%)", "生长起始温度(℃)", "生长终止温度(℃)",
        "降温速率(℃/h)", "生长时间(h)", "pH",
        "籽晶取向", "固定方式", "开裂",
    ]
    missing = []
    for col in important:
        s = flat[col]
        valid = s.notna() & s.astype(str).str.strip().ne("") & s.astype(str).ne("未知")
        missing.append(
            {
                "字段": col,
                "完整率": round(float(valid.mean() * 100), 1),
                "缺失/未知": int((~valid).sum()),
            }
        )

    labelled = int(flat["开裂"].isin(["是", "否"]).sum())
    cracked = int((flat["开裂"] == "是").sum())

    metric_cards(
        [
            {"label": "有效实验", "value": len(flat), "note": "不含回收站", "accent": COLORS["primary"]},
            {"label": "开裂标签完整", "value": f"{labelled}/{len(flat)}", "note": "分类模型Y", "accent": COLORS["teal"]},
            {"label": "开裂记录", "value": cracked, "note": "失败经验也保留", "accent": COLORS["orange"]},
            {"label": "版本可追溯", "value": "已启用", "note": "修改保留历史快照", "accent": COLORS["cyan"]},
        ]
    )

    st.dataframe(pd.DataFrame(missing), width="stretch", hide_index=True)

    completeness = []
    for _, r in flat.iterrows():
        vals = []
        for col in important:
            v = r.get(col)
            vals.append(
                v is not None
                and str(v).strip() not in {"", "未知", "nan", "None"}
            )
        completeness.append(
            {
                "实验ID": r["实验ID"],
                "完整度": round(sum(vals) / len(vals) * 100, 1),
                "开裂": r["开裂"],
            }
        )
    st.dataframe(
        pd.DataFrame(completeness).sort_values("完整度"),
        width="stretch",
        hide_index=True,
        height=360,
    )


def _ml_ready():
    records = list_records()
    if not records:
        soft_note("当前没有实验记录。")
        return

    flat = _records_table(records)

    section_title("机器学习准备", "现在不强行训练模型；先让数据真正达到可学习、可解释、可验证的状态")

    target_map = {
        "是否开裂（分类）": "开裂",
        "裂纹延迟时间（回归）": "裂纹延迟(min)",
        "最终质量（回归）": "最终质量(g)",
        "最终长度（回归）": "最终长度(mm)",
        "包裹体等级（分类）": "包裹体",
        "散射等级（分类）": "散射点",
    }
    target_name = st.selectbox("未来准备预测的目标 Y", list(target_map))
    target = target_map[target_name]

    valid_y = flat[target].notna() & flat[target].astype(str).str.strip().ne("") & flat[target].astype(str).ne("未知")
    n_valid = int(valid_y.sum())

    input_cols = [
        "过饱和度(%)", "生长起始温度(℃)", "生长终止温度(℃)",
        "降温速率(℃/h)", "生长时间(h)", "pH",
        "籽晶类型", "籽晶取向", "籽晶质量", "固定方式",
        "取晶温度(℃)", "环境温度(℃)", "冷却方式",
    ]
    core_complete = float(
        flat[input_cols[:6]].notna().mean().mean() * 100
    ) if len(flat) else 0.0

    readiness = (
        min(100, len(flat) * 2.0) * 0.35
        + (n_valid / max(1, len(flat)) * 100) * 0.35
        + core_complete * 0.30
    )

    metric_cards(
        [
            {"label": "实验记录", "value": len(flat), "note": "当前项目", "accent": COLORS["primary"]},
            {"label": "目标Y有效样本", "value": n_valid, "note": target_name, "accent": COLORS["teal"]},
            {"label": "核心数值参数完整", "value": f"{core_complete:.0f}%", "note": "输入X质量", "accent": COLORS["cyan"]},
            {"label": "数据准备度", "value": f"{readiness:.0f}/100", "note": "数据管理指标，不是模型准确率", "accent": COLORS["orange"]},
        ]
    )

    if len(flat) < 20:
        st.info("当前优先做实验比较、缺失率检查和变量规范化。样本较少时，机器学习预测不能当科研结论。")
    elif len(flat) < 50:
        st.info("可以开始探索简单基线模型和交叉验证，但重点仍是识别批次效应、标签偏差和不确定性。")
    else:
        st.info("数据规模开始具备正式基线建模的条件；仍需划分独立验证集，并防止同批次数据泄漏到训练集和测试集。")

    if target in {"开裂", "包裹体", "散射点"} and n_valid:
        dist = flat.loc[valid_y, target].value_counts().rename_axis("类别").reset_index(name="样本数")
        st.dataframe(dist, width="stretch", hide_index=True)

    section_title("未来模型的数据表", "X和Y已经从实验记录自动整理；以后接机器学习时无需重新人工录表")
    export_cols = ["实验ID", "日期"] + input_cols + [
        "开裂", "裂纹延迟(min)", "裂纹数量",
        "包裹体", "散射点", "最终质量(g)",
        "最终长度(mm)", "最终宽度(mm)", "最终高度(mm)",
    ]
    export_cols = [c for c in export_cols if c in flat.columns]
    ml_df = flat[export_cols].copy()
    st.dataframe(ml_df, width="stretch", hide_index=True, height=380)

    st.download_button(
        "导出机器学习数据集 CSV",
        ml_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="KDP_实验机器学习数据集.csv",
        mime="text/csv",
    )

    section_title("让AI安全参与", "AI继续服务这个平台，但默认看不到真实实验配方和参数")
    st.caption(
        "可以生成一段“脱敏统计摘要”加入普通项目记忆。AI科研助手以后可以读取这段摘要，"
        "但不会获得单次实验的具体配比、温度、速率、附件或精确结果。"
    )
    summary = sanitized_summary()
    st.code(summary, language=None)
    if st.button("将脱敏摘要加入当前项目记忆", key="save_sanitized_note"):
        add_item(
            "note",
            "实验数据脱敏统计摘要",
            summary,
            {"protected_source": True, "contains_raw_experiment_data": False},
            "实验记录与数据积累",
            "可供AI参考",
        )
        st.success("已加入普通项目记忆。AI可读取这段脱敏摘要，不会读取保险库全量数据。")


def _backup_security(project):
    stats = vault_stats()
    section_title("加密备份", "当前没有后端数据库，所以这是跨会话长期积累真实实验数据的关键")

    filename = (
        f"KDP_{project.get('name','研究项目')}_实验保险库_"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.kdpvault"
    )
    safe_name = re.sub(r'[\\\\/:*?"<>|]+', "_", filename)

    st.download_button(
        "下载最新加密实验保险库",
        export_blob(),
        file_name=safe_name,
        mime="application/octet-stream",
        type="primary",
    )
    st.warning(
        "请把 `.kdpvault` 文件保存在你自己的受控位置。"
        "当前Streamlit没有后端持久数据库，如果浏览器会话结束、应用重启或重新部署，"
        "未下载备份的数据可能丢失。"
    )

    section_title("更换保险库密码", "更换后请立即重新下载一份新备份；旧备份仍需要旧密码")
    n1 = st.text_input("新密码", type="password", key="rotate_vault_pwd1")
    n2 = st.text_input("再次输入新密码", type="password", key="rotate_vault_pwd2")
    if st.button("更换密码", key="rotate_vault_btn"):
        if n1 != n2:
            st.error("两次密码不一致。")
        else:
            try:
                rotate_password(n1)
                st.success("密码已更换。请立即下载新的保险库备份。")
            except Exception as exc:
                st.error(str(exc))

    section_title("安全状态", "这是当前无后端版本能做到的最高保护层；明天导师决定部署方式后，再决定是否迁移到内网/后端")
    security_rows = pd.DataFrame(
        [
            ["二次密码", "启用", "与网页普通访问码独立"],
            ["会话隔离", "启用", "不同访客的Streamlit Session互不共享保险库明文"],
            ["自动锁定", "启用", "默认20分钟无操作自动锁定，可用Secrets调整"],
            ["密码错误保护", "启用", "连续错误会短时锁定"],
            ["普通项目记忆", "只保存索引", "不保存真实配方/工艺/附件"],
            ["外部AI", "默认隔离", "全量实验数据不会自动发送给DeepSeek/OpenAI"],
            ["跨会话持久化", "加密备份文件", "当前无后端数据库，需下载/重新导入 .kdpvault"],
            ["附件", "随保险库加密", f"{stats['attachments']} 个，当前约 {stats['attachment_bytes']/1024/1024:.1f} MB"],
        ],
        columns=["保护项", "当前状态", "说明"],
    )
    st.dataframe(security_rows, width="stretch", hide_index=True, height=360)

    section_title("审计日志", "记录创建、修改、导入、锁定、附件操作等事件；不记录真实参数值")
    logs = audit_log()
    if logs:
        st.dataframe(pd.DataFrame(logs[:100]), width="stretch", hide_index=True, height=360)

    section_title("回收站", "删除先进入回收站，避免实验记录被直接抹掉")
    trash = [x for x in list_records(include_trash=True) if x.get("status") == "trash"]
    if trash:
        for rec in trash:
            c1, c2 = st.columns([4, 1])
            c1.write(f"{rec.get('experiment_id','')} · {rec.get('updated_at','')}")
            if c2.button("恢复", key=f"restore_{rec['id']}"):
                restore_record(rec["id"])
                _ensure_project_index(get_record(rec["id"]), status="受保护")
                st.rerun()
    else:
        st.caption("回收站为空。")


def experiment_lab_page():
    project = get_active_project()
    if not project:
        st.error("没有活动研究项目。")
        return

    if not _vault_entry(project):
        return

    _sync_indexes()
    _security_header(project)

    sections = [
        "记录新实验",
        "我的实验",
        "实验对比",
        "数据质量",
        "机器学习准备",
        "备份与安全",
    ]
    section = st.segmented_control(
        "实验数据功能",
        sections,
        default="记录新实验",
        selection_mode="single",
        label_visibility="collapsed",
        key="secure_experiment_section",
    )

    if section == "记录新实验":
        _new_record_form(project)
    elif section == "我的实验":
        _history()
    elif section == "实验对比":
        _compare()
    elif section == "数据质量":
        _data_quality()
    elif section == "机器学习准备":
        _ml_ready()
    else:
        _backup_security(project)
