from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from research_memory import add_item
from ui import COLORS, metric_cards, page_header, section_title, soft_note


PARAMS = pd.DataFrame([
    ["热膨胀系数", "α(T)", "热应变与方向差异", "TMA / 膨胀仪", "[001]、[100]；[110]可验证", "1/K"],
    ["热扩散率", "a(T)", "温度扰动传播速度", "LFA 激光闪射", "热流沿[001]、[100]", "mm²/s 或 m²/s"],
    ["热导率", "k(T)", "温度梯度大小", "由 LFA + ρ + Cp 换算或直接法", "[001]、[100]", "W/(m·K)"],
    ["比热", "Cp(T)", "热惯性", "DSC", "通常小块样品；记录晶体状态", "J/(kg·K)"],
    ["密度", "ρ", "热传导与质量归一化", "质量-尺寸 / 合适密度法", "通常不作为方向量", "kg/m³"],
    ["弹性常数", "Cij(T)", "各向异性应力响应", "RUS / 超声反演", "规则定向单晶", "GPa"],
    ["有效弹性模量", "E[uvw]", "给定方向拉压/弯曲刚度", "定向力学 + 应变 / 由Cij计算", "[001]、[100]、[110]", "GPa"],
    ["泊松比", "ν", "横向-纵向变形耦合", "应变片/DIC / 由Cij计算", "需写载荷和横向方向", "—"],
    ["破坏强度", "σf", "宏观失效阈值与Weibull统计", "三点弯曲 / 拉伸 / 压缩", "至少[001]、[100]、[110]", "MPa"],
    ["断裂韧性", "KIC", "已有裂纹失稳扩展能力", "SENB 等", "明确裂纹面与扩展方向", "MPa·m^0.5"],
], columns=["参数", "符号", "为什么要测", "推荐方法", "建议方向/取向", "常用单位"])


def material_properties_page():
    page_header(
        "KDP物性参数与测试",
        "把热—力模型真正需要的参数、晶向、测试方法和样品要求一次规划清楚；实测值与文献值必须可追溯。",
        "MATERIAL PROPERTY & TESTING",
    )

    metric_cards([
        {"label": "温度场", "value": "ρ · Cp · k", "note": "决定温度如何传播", "accent": COLORS["primary"]},
        {"label": "热应变", "value": "α(T)", "note": "决定各方向热收缩", "accent": COLORS["cyan"]},
        {"label": "应力场", "value": "Cij / E / ν", "note": "决定约束下应力响应", "accent": COLORS["violet"]},
        {"label": "失效", "value": "σf / KIC", "note": "强度与裂纹扩展边界", "accent": COLORS["orange"]},
    ])

    mode = st.segmented_control(
        "查看内容",
        ["参数总表", "取样方向", "测试方案生成", "数据记录模板"],
        default="参数总表",
        key="property_mode",
    )

    if mode == "参数总表":
        st.dataframe(PARAMS, width="stretch", hide_index=True, height=470)
        st.latex(r"\rho C_p\frac{\partial T}{\partial t}=\nabla\cdot(\mathbf{k}\nabla T),\qquad \varepsilon^{th}=\alpha\Delta T")
        st.latex(r"\boldsymbol{\sigma}=\mathbf{C}:\left(\boldsymbol{\varepsilon}-\boldsymbol{\varepsilon}^{th}\right),\qquad K_I=Y\sigma\sqrt{\pi a}")
        soft_note("建议最终建立‘参数—晶向—温度—样品批次—方法—不确定度—来源’数据库。一个不带方向和温度的单值，只适合最初级估算。")
        return

    if mode == "取样方向":
        section_title("先定向，再切样", "不要把(200)/(002)晶面和[200]/[002]方向混在一起")
        st.markdown(
            "- **[200] ∥ [100]**，方向通常归一化写作 [100]。\n"
            "- **[002] ∥ [001]**，方向通常归一化写作 [001]。\n"
            "- **(200)** 与 **(002)** 是晶面取向；‘表面为(200)’和‘测试方向沿[100]’要分别写。\n"
            "- 在 (001) 面内的几何对角通常是 **[110]**；力学/断裂建议单独保留该方向。"
        )
        st.dataframe(pd.DataFrame([
            ["热膨胀", "[001]、[100]", "比较轴向与面内热收缩；[110]可作验证"],
            ["热导/热扩散", "热流沿[001]、[100]", "抓住主要热各向异性"],
            ["弹性/超声", "规则定向样块", "优先反演完整Cij"],
            ["弯曲强度", "[001]、[100]、[110]", "检查方向依赖与离散"],
            ["断裂韧性", "明确裂纹面+扩展方向", "不能只写‘110样品’"],
        ], columns=["测试", "建议取向", "说明"]), width="stretch", hide_index=True)
        return

    if mode == "测试方案生成":
        directions = st.multiselect("计划测试方向", ["[001]", "[100]", "[110]"], default=["[001]", "[100]", "[110]"])
        tests = st.multiselect("计划测试项目", PARAMS["参数"].tolist(), default=["热膨胀系数", "热扩散率", "比热", "密度", "弹性常数", "破坏强度", "断裂韧性"])
        temp_range = st.text_input("温度范围", value="室温至实际取晶/冷却涉及温区；按设备能力分段")
        repeats = st.number_input("力学类每个方向探索阶段重复数", min_value=3, max_value=30, value=5)

        rows = []
        for test in tests:
            row = PARAMS[PARAMS["参数"] == test].iloc[0]
            if test in ["比热", "密度"]:
                rows.append({"项目": test, "方向": "总体/按样品状态", "方法": row["推荐方法"], "重复": "≥3或按仪器标准", "温区": temp_range})
            else:
                for d in directions:
                    rows.append({"项目": test, "方向": d, "方法": row["推荐方法"], "重复": repeats if test in ["破坏强度", "断裂韧性"] else "≥2–3", "温区": temp_range})
        plan = pd.DataFrame(rows)
        st.dataframe(plan, width="stretch", hide_index=True, height=480)
        st.download_button("下载测试计划CSV", plan.to_csv(index=False).encode("utf-8-sig"), "KDP_物性测试计划.csv", "text/csv")
        if st.button("保存测试计划到当前项目", type="primary"):
            add_item("experiment_plan", "KDP物性测试计划", f"方向：{', '.join(directions)}；温区：{temp_range}", {"rows": plan.to_dict("records")}, "物性参数与测试", "待执行")
            st.success("已保存到当前研究项目。")
        return

    template = pd.DataFrame([
        {"参数": "热膨胀系数", "方向/取向": "[001]", "温度(℃)": "", "数值": "", "单位": "1/K", "不确定度": "", "测试方法": "TMA", "样品批次": "", "来源": "实测/文献", "DOI或记录ID": "", "备注": ""},
        {"参数": "热导率", "方向/取向": "[100]", "温度(℃)": "", "数值": "", "单位": "W/(m·K)", "不确定度": "", "测试方法": "LFA+ρ+Cp", "样品批次": "", "来源": "实测/文献", "DOI或记录ID": "", "备注": ""},
        {"参数": "断裂韧性", "方向/取向": "裂纹面/扩展方向", "温度(℃)": "", "数值": "", "单位": "MPa·m^0.5", "不确定度": "", "测试方法": "SENB", "样品批次": "", "来源": "实测/文献", "DOI或记录ID": "", "备注": ""},
    ])
    edited = st.data_editor(template, num_rows="dynamic", width="stretch", hide_index=True)
    st.download_button("下载参数记录模板CSV", edited.to_csv(index=False).encode("utf-8-sig"), "KDP_物性参数记录模板.csv", "text/csv")
    st.warning("真实未公开实测数据请仍进入‘实验记录与数据积累’的受保护保险库；本页主要用于测试规划和结构化模板。")
