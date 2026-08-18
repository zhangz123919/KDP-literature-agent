from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from research_memory import add_item
from ui import page_header, soft_note


def _intro_styles():
    st.markdown(
        """
<style>
.scale-hero{border-top:3px solid #1359A6;border-bottom:1px solid #D9E2EA;background:#FBFCFD;padding:18px 20px;margin:2px 0 18px}
.scale-hero-title{font-size:20px;font-weight:850;color:#153A55;margin-bottom:7px}.scale-hero-body{font-size:13px;line-height:1.85;color:#526B7D}
.scale-flow{display:grid;grid-template-columns:repeat(6,1fr);gap:0;border-top:1px solid #D9E2EA;border-bottom:1px solid #D9E2EA;background:#fff;margin:10px 0 24px}
.scale-step{padding:13px 12px;border-right:1px solid #E5EBF0}.scale-step:last-child{border-right:none}.scale-no{font-size:9px;color:#8A9AA7;letter-spacing:.12em}.scale-v{font-size:12px;font-weight:800;color:#183F5C;margin-top:4px}.scale-s{font-size:10px;color:#738797;line-height:1.55;margin-top:3px}
.beginner-card{border-left:3px solid #0E9AA7;background:#F5FAFA;padding:13px 15px;margin:10px 0 16px;line-height:1.8;color:#45677A;font-size:12px}
.question-card{border-top:2px solid #1359A6;background:#fff;padding:15px 16px;border-bottom:1px solid #DDE5EB;min-height:122px}.question-title{font-size:14px;font-weight:850;color:#183B56}.question-body{font-size:11px;line-height:1.7;color:#63798A;margin-top:7px}
@media(max-width:1100px){.scale-flow{grid-template-columns:repeat(3,1fr)}}
</style>
        """,
        unsafe_allow_html=True,
    )


def _flow():
    st.markdown(
        """
<div class="scale-flow">
  <div class="scale-step"><div class="scale-no">01</div><div class="scale-v">晶体长大</div><div class="scale-s">小 → 中 → 大</div></div>
  <div class="scale-step"><div class="scale-no">02</div><div class="scale-v">局部环境改变</div><div class="scale-s">流场 / 传质 / 温度</div></div>
  <div class="scale-step"><div class="scale-no">03</div><div class="scale-v">界面响应</div><div class="scale-s">过饱和度 / 台阶 / 成核</div></div>
  <div class="scale-step"><div class="scale-no">04</div><div class="scale-v">缺陷形成</div><div class="scale-s">白纹 / 串丝 / 包裹体</div></div>
  <div class="scale-step"><div class="scale-no">05</div><div class="scale-v">应力累积</div><div class="scale-s">热应变 / 局部应力</div></div>
  <div class="scale-step"><div class="scale-no">06</div><div class="scale-v">最终结果</div><div class="scale-s">开裂 / 工艺优化</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _overview():
    st.markdown(
        '<div class="scale-hero"><div class="scale-hero-title">这个页面只研究一件事：晶体变大以后，为什么会更难长好？</div>'
        '<div class="scale-hero-body">你现在不需要先懂 Re、Pe、CFD。先抓住一句话：<b>控制器上的温度、转速、降温速率相同，不代表晶体表面真正经历的流动、传质和温度环境相同。</b> 大尺寸研究就是要把“尺寸变大”以后发生的这些变化找出来，再看它们是否对应白纹、串丝、包裹体和开裂。</div></div>',
        unsafe_allow_html=True,
    )
    _flow()

    st.markdown("### 先回答这 4 个问题")
    c1, c2, c3, c4 = st.columns(4, gap="small")
    cards = [
        ("1｜尺寸变大后，哪里变了？", "比较小、中、大晶体周围的流速、涡流、边界层、局部温度和表面过饱和度。"),
        ("2｜缺陷从什么时候开始增加？", "记录白纹、串丝、包裹体首次出现时的晶体尺寸、生长时间和空间位置。"),
        ("3｜缺陷和局部场是否对应？", "把缺陷位置与 CFD/温度场结果叠加，寻找空间共定位，而不是只看平均值。"),
        ("4｜怎样让大晶体也长得好？", "在模型和实验中调整转速、换向、流量、降温程序，验证缺陷是否真正下降。"),
    ]
    for col, (title, body) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f'<div class="question-card"><div class="question-title">{title}</div><div class="question-body">{body}</div></div>', unsafe_allow_html=True)

    st.markdown("### 你现在最先该做什么")
    st.markdown(
        """
1. **把已有晶体按小 / 中 / 大尺寸分组**，先不要急着改变工艺。
2. **统一记录白纹、串丝、包裹体、开裂的位置和严重程度**，不要只记“有/无”。
3. **从最简单的 CFD 尺寸对比开始**：同一个生长槽、同样转速，先看不同晶体尺寸的流场和表面传质有什么差异。
        """
    )
    soft_note("这个页面是研究路线导航，不是直接给出工艺答案。真正的转速、流量和温度程序必须由实际生长槽 CFD 与实验验证共同确定。")


def _experiment_design():
    st.markdown("### 小—中—大尺寸对照实验设计")
    st.caption("这里不用记“A轨/B轨”。你只需要做两轮实验：第一轮保持外部设定不变，第二轮再根据局部环境去优化。")

    t1, t2 = st.tabs(["第一轮｜外部设定保持一致", "第二轮｜让局部环境尽量接近"])
    with t1:
        st.markdown(
            "**目的：**先观察晶体放大本身带来了什么变化。比如同样 20 rpm，小晶体和大晶体表面的流动状态可能已经完全不同。"
        )
        base_size = st.number_input("小晶体参考尺寸（mm）", min_value=1.0, value=50.0, key="scale_exp_s")
        mid_size = st.number_input("中晶体尺寸（mm）", min_value=1.0, value=150.0, key="scale_exp_m")
        large_size = st.number_input("大晶体尺寸（mm）", min_value=1.0, value=300.0, key="scale_exp_l")
        same = st.multiselect(
            "这一轮计划保持不变的外部条件",
            ["体相过饱和度", "温度程序", "转速", "换向程序", "溶液浓度", "籽晶取向", "籽晶固定方式", "循环流量"],
            default=["体相过饱和度", "温度程序", "转速", "换向程序", "籽晶取向"],
        )
        outputs = st.multiselect(
            "每个尺寸阶段都要观察什么",
            ["白纹", "串丝", "普通包裹体", "散射点", "开裂", "生长速率", "晶面形貌"],
            default=["白纹", "串丝", "普通包裹体", "开裂"],
        )
        plan = pd.DataFrame([
            ["小尺寸", base_size, "作为基准", "建立基准缺陷地图"],
            ["中尺寸", mid_size, "保持上述外部条件", "看缺陷/局部场从何时开始偏离"],
            ["大尺寸", large_size, "继续保持上述外部条件", "确认放大后非均匀性和缺陷是否增强"],
        ], columns=["阶段", "特征尺寸(mm)", "工艺策略", "这一阶段要回答的问题"])
        st.dataframe(plan, width="stretch", hide_index=True)
        st.info("第一轮的核心不是把大晶体长到最好，而是建立‘尺寸变化 → 结果变化’的基线。")

    with t2:
        st.markdown(
            "**目的：**如果第一轮发现大晶体缺陷增多，就利用 CFD/传质模型调整工况，让大晶体表面的局部环境尽量接近小晶体，再看缺陷能否下降。"
        )
        st.markdown(
            "重点比较：**速度场、涡流/死区、表面过饱和度分布、温度场**。可调整的控制量包括转速、换向周期、循环流量和温度程序。"
        )
        st.warning("这里不自动给出某个 rpm 作为实验配方。因为真实结果还取决于槽体几何、自由液面、自然对流、晶体形状和溶液物性。")

    if st.button("保存这套尺寸对照思路到当前项目", type="primary", key="save_scale_simple_plan"):
        add_item(
            "experiment_plan",
            "KDP小—中—大尺寸对照实验",
            "第一轮保持外部设定一致建立尺度基线；第二轮利用CFD/传质调整工况，使局部环境尽量接近后再次比较缺陷。",
            {"same_conditions": same if 'same' in locals() else [], "outputs": outputs if 'outputs' in locals() else []},
            "大尺寸尺度效应",
            "待执行",
        )
        st.success("已保存到当前研究项目。")


def _similarity():
    st.markdown("### 尺寸变化为什么会让同样的 rpm 失去可比性？")
    st.markdown(
        "这里做的只是一个**尺度直觉演示**。对旋转晶体，如果用特征速度近似为 `U ~ ωL`，那么一些流动/传质无量纲量会随 `ωL²` 快速增大。它的用途是告诉你：**尺寸放大 6 倍时，保持 rpm 不变绝不是一个小变化。**"
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        l1 = st.number_input("小晶体尺寸 L₁（mm）", 1.0, value=50.0, key="sim_l1")
        n1 = st.number_input("小晶体转速 n₁（rpm）", 0.1, value=20.0, key="sim_n1")
    with c2:
        l2 = st.number_input("中晶体尺寸 L₂（mm）", 1.0, value=150.0, key="sim_l2")
        n2 = st.number_input("中晶体转速 n₂（rpm）", 0.1, value=20.0, key="sim_n2")
    with c3:
        l3 = st.number_input("大晶体尺寸 L₃（mm）", 1.0, value=300.0, key="sim_l3")
        n3 = st.number_input("大晶体转速 n₃（rpm）", 0.1, value=20.0, key="sim_n3")

    base = n1 * l1 * l1
    rows = []
    for name, L, n in [("小", l1, n1), ("中", l2, n2), ("大", l3, n3)]:
        rel = (n * L * L) / base if base else math.nan
        match = n1 * (l1 / L) ** 2
        rows.append([name, L, n, round(rel, 3), round(match, 4)])
    df = pd.DataFrame(rows, columns=["阶段", "尺寸(mm)", "当前转速(rpm)", "ωL²相对指数", "仅按Re尺度匹配的rpm(演示)"])
    st.dataframe(df, width="stretch", hide_index=True)

    rel_large = (n3 * l3 * l3) / base if base else math.nan
    st.markdown(
        f"**按这个非常简化的尺度指标：**大晶体当前工况相对小晶体约为 **{rel_large:.1f} 倍**。这并不表示实际 Re 或 Pe 就精确增加 {rel_large:.1f} 倍，而是提醒你必须进入真实 CFD。"
    )
    soft_note("右侧‘匹配 rpm’只能用于理解量级，不能直接拿去设定真实生长转速。真实 KDP 生长还需要考虑自然对流、周期换向、槽体边界、自由液面、晶体形状、溶液黏度与扩散系数。")


def _defect_map():
    st.markdown("### 缺陷空间记录：以后不要只写‘有白纹’")
    st.caption("真正有研究价值的是：缺陷出现在哪里、何时出现、朝什么方向、当时晶体有多大。")

    with st.expander("白纹怎么记录", expanded=True):
        st.markdown(
            """
- **严重程度**：无 / 少量 / 中等 / 大量，后续再升级为密度或面积占比。
- **空间位置**：锥区还是柱区；靠中心还是边缘；靠哪个晶面/生长扇区。
- **方向**：白纹与 [001]、生长界面或晶面之间的夹角。
- **几何量**：宽度、长度、间距，有无明显周期。
- **时间信息**：这部分晶体大约在第几天、晶体多大时长出来。
- **照片**：同一光照、同一角度、带比例尺。
            """
        )
    with st.expander("串丝怎么记录", expanded=False):
        st.markdown(
            """
- 数量/密度、单条长度、链状结构密集程度。
- 与 c 轴、晶面、生长方向的夹角。
- 距籽晶和晶体边缘的距离。
- 是否与白纹、包裹体密集区或裂纹邻近。
- 有条件时补充显微/散射图，区分真正的 hair inclusion 与普通条纹。
            """
        )
    with st.expander("开裂怎么记录", expanded=False):
        st.markdown(
            """
- 裂纹首次出现时间：生长中 / 取晶时 / 出炉冷却后多长时间。
- 起裂位置和晶体尺寸。
- 裂纹走向、可能晶面、是否贯穿。
- 起裂附近是否存在白纹、串丝、包裹体或明显应力异常。
- 同步保存当时温度程序、环境温度和固定/支撑方式。
            """
        )

    st.markdown("#### 最小记录模板")
    template = pd.DataFrame([
        {"样品/批次": "", "生长阶段": "", "晶体尺寸(mm)": "", "缺陷类型": "白纹", "位置": "", "方向": "", "严重程度/数量": "", "首次出现时间": "", "照片编号": "", "备注": ""},
        {"样品/批次": "", "生长阶段": "", "晶体尺寸(mm)": "", "缺陷类型": "串丝", "位置": "", "方向": "", "严重程度/数量": "", "首次出现时间": "", "照片编号": "", "备注": ""},
    ])
    edited = st.data_editor(template, num_rows="dynamic", width="stretch", hide_index=True, key="scale_defect_editor")
    st.download_button("下载缺陷空间记录模板 CSV", edited.to_csv(index=False).encode("utf-8-sig"), "KDP_缺陷空间记录模板.csv", "text/csv")


def _checklist():
    st.markdown("### 一次实验到底要留下哪些数据？")
    st.caption("下面是最小清单。先把这些数据留下来，后面才有可能做统计、CFD共定位和机器学习。")
    groups = {
        "晶体本体": ["三个方向尺寸/质量", "当前生长阶段", "籽晶取向与固定方式"],
        "生长条件": ["温度与降温程序", "浓度/体相过饱和度", "转速与换向程序", "循环流量/溶液状态"],
        "缺陷结果": ["白纹空间地图", "串丝空间地图", "包裹体/散射点", "裂纹起点/时间/方向"],
        "模型与验证": ["CFD速度场/涡流", "表面过饱和度分布", "温度场", "应力场", "物性参数来源"],
    }
    for title, items in groups.items():
        st.markdown(f"**{title}**")
        cols = st.columns(2)
        for i, item in enumerate(items):
            cols[i % 2].checkbox(item, key=f"check_{title}_{i}")


def scale_effect_page():
    _intro_styles()
    page_header(
        "大尺寸 KDP：从小晶体到大晶体",
        "用最直观的方式研究‘为什么名义条件一样，晶体长大以后却可能出现更多白纹、串丝、包裹体和开裂’。",
        "LARGE-SCALE KDP",
    )

    tabs = st.tabs(["先看懂这件事", "设计尺寸对照实验", "尺寸相似性演示", "记录白纹/串丝/开裂", "实验数据清单"])
    with tabs[0]:
        _overview()
    with tabs[1]:
        _experiment_design()
    with tabs[2]:
        _similarity()
    with tabs[3]:
        _defect_map()
    with tabs[4]:
        _checklist()
