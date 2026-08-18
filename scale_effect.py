from __future__ import annotations

import math
from io import BytesIO

import pandas as pd
import streamlit as st

from research_memory import add_item, get_active_project
from ui import COLORS, metric_cards, page_header, section_title, soft_note


def _float(v, default):
    try:
        return float(v)
    except Exception:
        return float(default)


def scale_effect_page():
    page_header(
        "大尺寸尺度效应研究",
        "围绕‘同样名义工艺，小晶体与大晶体为什么长得不一样’建立双轨对照：尺寸 → 流场/传质/表面过饱和度 → 白纹/串丝/包裹体 → 应力/开裂。",
        "LARGE-SCALE KDP RESEARCH",
    )

    with st.container(border=True):
        st.markdown("### 当前核心科学问题")
        st.markdown(
            "**当 KDP 从小尺寸逐步长到大尺寸时，外部设定值可以相同，但局部流动、传质、温度和生长界面是否已经发生系统变化？这些变化是否对应白纹、串丝、包裹体和开裂的尺寸依赖？**"
        )
        st.caption("这里把它作为待验证的研究主线，而不是预设结论。")

    metric_cards([
        {"label": "H1", "value": "尺度→局部场", "note": "名义条件相同 ≠ 表面环境相同", "accent": COLORS["primary"]},
        {"label": "H2", "value": "局部场→缺陷", "note": "白纹 / 串丝 / 包裹体", "accent": COLORS["cyan"]},
        {"label": "H3", "value": "缺陷+热力→开裂", "note": "需做空间共定位验证", "accent": COLORS["orange"]},
        {"label": "目标", "value": "大尺寸低缺陷", "note": "从解释机制走向工艺优化", "accent": COLORS["teal"]},
    ])

    mode = st.segmented_control(
        "研究工具",
        ["双轨实验设计", "尺寸相似性估算", "缺陷空间地图规范", "数据清单"],
        default="双轨实验设计",
        key="scale_mode",
    )

    if mode == "双轨实验设计":
        section_title("A轨｜名义工艺相同", "故意不随尺寸修正工艺，用来观察纯放大后果")
        st.dataframe(pd.DataFrame([
            ["小尺寸", "基准", "相同", "相同", "相同", "记录白纹/串丝/包裹体/开裂"],
            ["中尺寸", "增大", "保持基准", "保持基准", "保持基准", "比较局部场和缺陷是否开始偏离"],
            ["大尺寸", "进一步增大", "保持基准", "保持基准", "保持基准", "量化尺度放大后的非均匀与失效"],
        ], columns=["阶段", "晶体尺寸", "体相过饱和度", "转速/换向", "温度程序", "关键输出"]), width="stretch", hide_index=True)

        section_title("B轨｜局部环境尽量相似", "通过CFD/传质模型修正转速、流量或温度，使不同尺寸的表面环境更可比")
        st.dataframe(pd.DataFrame([
            ["小尺寸", "建立基准", "表面过饱和度分布", "作为目标场"],
            ["中尺寸", "调整工况", "Re/Pe、速度场、边界层、表面过饱和度", "尽量匹配基准的局部环境"],
            ["大尺寸", "再次调整", "同上 + 涡流/死区", "检验缺陷是否随局部环境改善而下降"],
        ], columns=["阶段", "工况策略", "比较量", "研究目的"]), width="stretch", hide_index=True)

        st.markdown("#### 两条轨道组合后能回答什么")
        st.markdown(
            "- 如果 A 轨随尺寸增大缺陷显著增加，而 B 轨在局部场被改善后缺陷下降，就支持‘**尺寸通过局部场改变缺陷**’这条机制链。\n"
            "- 如果 B 轨仍然无法改善，则要继续考虑位错、杂质、机械约束、温度场或材料统计尺寸效应。"
        )
        if st.button("保存尺度效应双轨方案到当前项目", type="primary"):
            add_item(
                "experiment_plan",
                "大尺寸KDP尺度效应双轨实验",
                "A轨保持名义工艺相同；B轨利用CFD/传质尽量匹配局部生长环境。",
                {"strategy": "scale_dual_track", "outputs": ["白纹", "串丝", "包裹体", "开裂", "表面过饱和度", "温度/应力"]},
                "尺度效应研究",
                "待执行",
            )
            st.success("已进入当前研究项目。")
        return

    if mode == "尺寸相似性估算":
        st.caption("这里只做无量纲趋势估算，用于理解尺度效应；不能直接替代真实 KDP 生长槽 CFD。")
        c1, c2, c3 = st.columns(3)
        with c1:
            l1 = st.number_input("小晶体特征尺寸 L₁ (mm)", min_value=1.0, value=50.0)
            n1 = st.number_input("小晶体转速 n₁ (rpm)", min_value=0.1, value=20.0)
        with c2:
            l2 = st.number_input("中晶体特征尺寸 L₂ (mm)", min_value=1.0, value=150.0)
            n2 = st.number_input("中晶体转速 n₂ (rpm)", min_value=0.1, value=20.0)
        with c3:
            l3 = st.number_input("大晶体特征尺寸 L₃ (mm)", min_value=1.0, value=300.0)
            n3 = st.number_input("大晶体转速 n₃ (rpm)", min_value=0.1, value=20.0)

        base = n1 * l1 * l1
        rows = []
        for name, L, n in [("小", l1, n1), ("中", l2, n2), ("大", l3, n3)]:
            rel = (n * L * L) / base if base else math.nan
            n_match = n1 * (l1 / L) ** 2
            rows.append({"尺寸阶段": name, "L(mm)": L, "当前rpm": n, "ωL²相对指数": rel, "若只匹配Re尺度的rpm估算": n_match})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.latex(r"U\sim \omega L\quad\Rightarrow\quad Re,Pe\propto \omega L^2")
        soft_note("‘匹配 Re 的 rpm’只用于尺度直觉。实际 KDP 生长还存在晶体几何、自然对流、周期换向、自由表面、溶液物性和传质边界条件，最终工艺必须靠真实 CFD + 实验。")
        return

    if mode == "缺陷空间地图规范":
        section_title("白纹", "不要只记有/无，要保留尺度、方向和生长历史")
        st.dataframe(pd.DataFrame([
            ["密度", "条/厘米、面积占比或等级", "小/大晶体比较必须统一定义"],
            ["宽度/长度", "mm", "区分细线与宽带"],
            ["间距/周期", "mm", "判断是否有周期性生长波动"],
            ["方向", "与 [001]/晶面/生长界面的夹角", "寻找晶体学关联"],
            ["位置", "距籽晶、中心/边缘、锥区/柱区", "与流场和扇区对应"],
            ["首次出现阶段", "晶体尺寸 + 生长时间", "寻找尺度阈值"],
        ], columns=["字段", "建议记录", "为什么"]), width="stretch", hide_index=True)

        section_title("串丝 / hair inclusion", "把链状包裹体从‘看见了’升级为可统计缺陷")
        st.dataframe(pd.DataFrame([
            ["数量/密度", "条数、单位体积/观察面积/路径长度", "跨尺寸比较"],
            ["长度", "mm / cm", "表征链尺度"],
            ["链密度", "单个包裹体个数或 mm⁻¹", "与文献指标对接"],
            ["方向", "与 c 轴、{101} 面夹角", "验证位错/生长方向关联"],
            ["空间位置", "晶面/扇区/距籽晶", "与CFD局部场共定位"],
            ["显微组成", "球状/条状/液态包裹体", "区分串丝与普通条纹"],
        ], columns=["字段", "建议记录", "为什么"]), width="stretch", hide_index=True)
        return

    rows = [
        ["输入X", "晶体三维尺寸/质量/生长阶段", "每个关键阶段", "尺度主变量"],
        ["输入X", "体相过饱和度、浓度、温度", "连续/批次", "生长驱动力"],
        ["输入X", "转速、换向周期、循环流量", "连续/程序", "流场边界"],
        ["输入X", "籽晶方向、质量、固定方式", "每批", "晶体学/机械约束"],
        ["过程场", "CFD速度场、涡流、表面过饱和度", "小/中/大", "机制中间变量"],
        ["结果Y", "白纹密度/方向/位置", "空间地图", "尺度敏感缺陷"],
        ["结果Y", "串丝数量/长度/角度", "空间地图", "链状包裹体"],
        ["结果Y", "包裹体/散射点", "空间地图", "体缺陷"],
        ["结果Y", "裂纹时间/起点/方向", "时序+空间", "宏观失效"],
        ["验证", "温度场、应力场、物性参数", "取晶/冷却", "热—力机制"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["类别", "数据", "记录方式", "用途"]), width="stretch", hide_index=True)
