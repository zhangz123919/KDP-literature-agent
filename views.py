
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agent import api_status, run_agent, stream_agent
from diagnosis import VARIABLES, diagnose, experiment_matrix
from engine import CORE_TOPICS, TOPICS, load_data, material_scope, offline_summary, search_papers, topic_search, topic_stats
from reports import docx_bytes, excel_bytes
from security import safe_error
from usage_monitor import render_deepseek_usage
from experiment_vault import list_records as vault_list_records, vault_unlocked
from research_memory import (
    add_item,
    build_project_context,
    get_active_project,
    list_items,
    private_mode_enabled,
    project_context_strip,
)
from ui import (
    COLORS,
    evidence_table,
    insight_strip,
    metric_cards,
    mini_cards,
    page_header,
    plotly,
    research_chain,
    section_title,
    soft_note,
    sources_block,
)


def _df():
    df = load_data()
    if df.empty:
        st.error("缺少 data/KDP_全自动详细文献调研.xlsx")
        st.stop()
    return df


def _tier_counts(df):
    return {
        "S": int((df["V5推荐等级"] == "S 核心 50").sum()),
        "A": int((df["V5推荐等级"] == "A 重点 150").sum()),
        "B": int((df["V5推荐等级"] == "B 扩展 800").sum()),
    }


def dashboard():
    df = _df()
    page_header(
        "科研驾驶舱",
        "汇总KDP主研究证据、专题活跃度、核心文献与当前研究状态，为进一步调研和决策提供快速入口。",
        "RESEARCH COMMAND CENTER",
    )

    project_context_strip()

    related = material_scope(df, "KDP主线")
    rel = len(related)
    tiers = _tier_counts(related)
    max_year = int(related["年份"].max()) if len(related) else 0
    recent_n = int((related["年份"] >= max_year - 4).sum()) if max_year else 0

    metric_cards(
        [
            {"label": "全库去重文献", "value": f"{len(df):,}", "note": "完整数据库", "accent": COLORS["primary"]},
            {"label": "KDP 主研究池", "value": f"{rel:,}", "note": "默认研究证据范围", "accent": COLORS["cyan"]},
            {"label": "S 核心", "value": tiers["S"], "note": "最高优先级", "accent": COLORS["violet"]},
            {"label": "A 重点", "value": tiers["A"], "note": "重点精读层", "accent": COLORS["orange"]},
            {"label": "B 扩展", "value": tiers["B"], "note": "主题扩展层", "accent": COLORS["teal"]},
            {"label": "近五年相关文献", "value": f"{recent_n:,}", "note": f"{max_year-4}–{max_year}" if max_year else "—", "accent": COLORS["green"]},
        ]
    )

    stats_raw = topic_stats(df).copy()
    stats_valid = stats_raw[stats_raw["总文献"] > 0].copy()
    stats_valid["近五年占比"] = (
        stats_valid["近5年"] / stats_valid["总文献"].replace(0, np.nan) * 100
    ).fillna(0)
    stats_valid["核心密度"] = (
        stats_valid["S/A"] / stats_valid["总文献"].replace(0, np.nan) * 100
    ).fillna(0)

    hot = stats_valid.sort_values(["近5年", "总文献"], ascending=False).iloc[0] if len(stats_valid) else None
    dense = stats_valid.sort_values(["核心密度", "S/A"], ascending=False).iloc[0] if len(stats_valid) else None
    dft = stats_valid.sort_values(["DFT", "总文献"], ascending=False).iloc[0] if len(stats_valid) else None

    insight_strip(
        [
            {
                "kicker": "RECENT ACTIVITY",
                "title": hot["专题"] if hot is not None else "—",
                "note": f"近五年 {int(hot['近5年'])} 篇 · 当前库近期文献量最高" if hot is not None else "暂无数据",
                "accent": COLORS["primary"],
            },
            {
                "kicker": "CORE EVIDENCE",
                "title": dense["专题"] if dense is not None else "—",
                "note": f"S/A {int(dense['S/A'])} 篇 · 核心证据密度 {dense['核心密度']:.1f}%" if dense is not None else "暂无数据",
                "accent": COLORS["orange"],
            },
            {
                "kicker": "THEORY COVERAGE",
                "title": dft["专题"] if dft is not None else "—",
                "note": f"DFT相关 {int(dft['DFT'])} 篇 · 用于观察理论覆盖结构" if dft is not None else "暂无数据",
                "accent": COLORS["cyan"],
            },
        ]
    )

    section_title("研究主线", "以“缺陷来源—局部机制—宏观后果—验证控制”统一组织研究问题")
    research_chain()

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        section_title("专题证据规模", "快速判断哪些问题已有较厚证据，哪些仍需补充")
        stats = stats_raw.sort_values("总文献", ascending=True)

        fig = go.Figure()

        # 总证据规模：低饱和背景条
        fig.add_trace(
            go.Bar(
                x=stats["总文献"],
                y=stats["专题"],
                orientation="h",
                name="全部相关文献",
                marker=dict(
                    color="#DCE5EE",
                    line=dict(width=0),
                ),
                hovertemplate="<b>%{y}</b><br>全部相关文献 %{x} 篇<extra></extra>",
            )
        )

        # 近五年：高亮覆盖
        fig.add_trace(
            go.Bar(
                x=stats["近5年"],
                y=stats["专题"],
                orientation="h",
                name="近五年",
                marker=dict(
                    color=COLORS["primary"],
                    line=dict(width=0),
                ),
                text=stats["近5年"].where(stats["近5年"] > 0, ""),
                textposition="outside",
                textfont=dict(size=10, color="#52677F"),
                hovertemplate="<b>%{y}</b><br>近五年 %{x} 篇<extra></extra>",
            )
        )

        fig.update_layout(
            barmode="overlay",
            xaxis_title="文献数",
            yaxis_title="",
            bargap=.28,
            legend=dict(
                orientation="h",
                x=0,
                y=1.08,
            ),
        )
        plotly(fig, height=560, key="dashboard_topics")

    with right:
        section_title("研究活跃度", "观察相关文献的长期增长与近期加速")
        trend = (
            related[related["年份"] > 0]
            .groupby("年份")
            .size()
            .reset_index(name="文献数")
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=trend["年份"],
                y=trend["文献数"],
                mode="lines",
                line=dict(color=COLORS["primary"], width=3),
                fill="tozeroy",
                fillcolor="rgba(91,91,214,.08)",
                hovertemplate="%{x}<br>%{y} 篇<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trend["年份"].tail(8),
                y=trend["文献数"].tail(8),
                mode="markers",
                marker=dict(size=7, color=COLORS["cyan"], line=dict(color="white", width=1.5)),
                showlegend=False,
                hovertemplate="%{x}<br>%{y} 篇<extra></extra>",
            )
        )
        if max_year:
            fig.add_vrect(
                x0=max_year - 4.5,
                x1=max_year + .5,
                fillcolor="rgba(19,89,166,.045)",
                line_width=0,
                layer="below",
            )
            fig.add_annotation(
                x=max_year - 2,
                y=1,
                yref="paper",
                text="近五年",
                showarrow=False,
                yshift=10,
                font=dict(size=10, color="#1359A6"),
            )
        fig.update_layout(
            xaxis_title="年份",
            yaxis_title="发文量",
            showlegend=False,
        )
        plotly(fig, height=520, key="dashboard_trend")

    section_title(
        "核心证据库",
        "S层已加入“证据完整度 ≥ 70”硬门槛；高被引/高分但方法、机制或结果没有解析清楚的文献不会直接进入核心证据层",
    )

    top = (
        related[related["V5推荐等级"] == "S 核心 50"]
        .sort_values(["V5核心排序分", "证据完整度分"], ascending=False)
    )

    s1_n = int((top["核心证据层级"] == "S1 直接核心").sum()) if len(top) else 0
    s2_n = int((top["核心证据层级"] == "S2 基础支撑").sum()) if len(top) else 0
    complete_n = int(top["证据完整度状态"].isin(["完整", "较完整"]).sum()) if len(top) else 0
    median_complete = int(top["证据完整度分"].median()) if len(top) else 0

    metric_cards(
        [
            {"label": "当前S核心", "value": len(top), "note": "通过完整度硬门槛", "accent": COLORS["primary"]},
            {"label": "S1直接核心", "value": s1_n, "note": "直接回答缺陷/开裂问题", "accent": COLORS["teal"]},
            {"label": "S2基础支撑", "value": s2_n, "note": "参数、结构与机理支撑", "accent": COLORS["orange"]},
            {"label": "完整度中位数", "value": f"{median_complete}/100", "note": f"{complete_n} 篇较完整/完整", "accent": COLORS["cyan"]},
        ]
    )

    show_cols = [
        "题名", "年份", "期刊", "核心证据层级", "证据完整度状态", "证据完整度分",
        "研究对象确认", "缺陷/应力来源", "作用机制", "宏观结果",
        "_方法标签", "V5核心排序分", "DOI",
    ]
    show_cols = [c for c in show_cols if c in top.columns]

    st.dataframe(
        top[show_cols],
        width="stretch",
        height=520,
        hide_index=True,
        column_config={
            "证据完整度分": st.column_config.ProgressColumn(
                "证据完整度", min_value=0, max_value=100, format="%d"
            ),
            "V5核心排序分": st.column_config.ProgressColumn(
                "核心排序分", min_value=0, max_value=100, format="%.1f"
            ),
        },
    )

    pending = (
        related[
            related["V5推荐等级"].eq("A 重点 150")
            & related["核心证据层级"].eq("需核验")
        ]
        .sort_values(["V5科研优先分", "被引次数"], ascending=False)
        .head(15)
    )

    if len(pending):
        with st.expander(
            f"高价值但证据不足的候选文献 · {len(pending)} 篇示例",
            expanded=False,
        ):
            st.caption(
                "这些文献可能很重要，但当前摘要/自动字段不足以确认方法、机制或结果。"
                "系统已主动降到待核层，不参与强结论。"
            )
            pending_cols = [
                "题名", "年份", "期刊", "证据完整度状态", "证据完整度分",
                "作用机制", "宏观结果", "_方法标签", "V5科研优先分", "DOI",
            ]
            pending_cols = [c for c in pending_cols if c in pending.columns]
            st.dataframe(
                pending[pending_cols],
                width="stretch",
                hide_index=True,
            )


def literature():
    df = _df()
    page_header(
        "文献中心",
        "从 6,000+ 条记录中快速定位真正相关的证据，并保留 DOI、分类、方法和证据层级。",
        "LITERATURE INTELLIGENCE",
    )

    project_context_strip()

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1.15])
        scope = c1.selectbox("证据范围", ["KDP主线", "S+A", "相关扩展", "全库"], index=0)
        limit = c2.selectbox("显示上限", [50, 100, 200, 500, 1000], index=2)
        tiers = c3.multiselect(
            "推荐等级",
            ["S 核心 50", "A 重点 150", "B 扩展 800", "C 扩展/背景", "D 非核心/待核"],
        )
        q = st.text_input(
            "科研检索",
            placeholder="例如：氢空位 额外吸收｜包裹体 开裂｜subsurface damage｜DFT",
        )

    work = df[df["V5推荐等级"].isin(tiers)] if tiers else df
    result = search_papers(work, q, limit, scope)

    direct = int(
        result["_证据层级"].isin(["强直接证据", "直接主题证据"]).sum()
    ) if "_证据层级" in result.columns else 0

    metric_cards(
        [
            {"label": "当前结果", "value": f"{len(result):,}", "note": "符合当前筛选", "accent": COLORS["primary"]},
            {"label": "直接证据", "value": direct, "note": "强直接 + 直接主题", "accent": COLORS["teal"]},
            {"label": "当前范围", "value": scope, "note": "可随时切换证据层", "accent": COLORS["cyan"]},
        ]
    )

    cols = [
        "题名", "作者", "年份", "期刊", "_证据层级", "V5推荐等级",
        "核心证据层级", "证据使用等级", "证据完整度状态", "证据完整度分", "V5科研优先分",
        "缺陷/应力来源", "作用机制", "宏观结果", "_方法标签", "被引次数", "DOI",
    ]
    cols = [c for c in cols if c in result.columns]

    section_title("检索结果", "表格支持滚动浏览；科研优先分只用于排序，不替代全文判断")
    st.dataframe(
        result[cols],
        width="stretch",
        height=620,
        hide_index=True,
        column_config={
            "V5科研优先分": st.column_config.ProgressColumn(
                "科研优先分", min_value=0, max_value=100, format="%.1f"
            ),
            "证据完整度分": st.column_config.ProgressColumn(
                "证据完整度", min_value=0, max_value=100, format="%d"
            ),
        },
    )
    st.download_button(
        "导出当前结果为 Excel",
        excel_bytes(result[cols], "文献检索"),
        "KDP_文献检索.xlsx",
    )


    if len(result):
        with st.expander("项目协同：把文献加入当前研究项目", expanded=False):
            top_for_project = result.head(120)
            mapping = {
                f"{r['题名']}｜{r.get('年份','')}｜{r.get('证据使用等级','')}": i
                for i, r in top_for_project.iterrows()
            }
            selected_papers = st.multiselect(
                "选择要沉淀的项目证据",
                list(mapping),
                max_selections=12,
                key="literature_project_evidence",
            )
            role = st.selectbox(
                "在当前项目中的作用",
                ["直接支持", "间接支持", "基础支撑", "反对/冲突证据", "待核验"],
            )
            if st.button("加入当前项目证据"):
                for label in selected_papers:
                    r = result.loc[mapping[label]]
                    add_item(
                        "evidence",
                        str(r.get("题名", "")),
                        str(r.get("自动主要结论", ""))[:1000],
                        {
                            "doi": str(r.get("DOI", "")),
                            "year": str(r.get("年份", "")),
                            "journal": str(r.get("期刊", "")),
                            "evidence_role": role,
                            "evidence_grade": str(r.get("证据使用等级", "")),
                            "mechanism": str(r.get("作用机制", "")),
                            "outcome": str(r.get("宏观结果", "")),
                        },
                        "文献中心",
                        role,
                    )
                if selected_papers:
                    st.success(f"已将 {len(selected_papers)} 篇文献加入当前项目记忆。")


# ---- Knowledge graph -------------------------------------------------------

KG_UNCERTAIN = {
    "基础物性/其他",
    "待核验（摘要未明确）",
    "摘要证据不足",
    "未讨论机制/基础性质",
    "基础物性（非失效）",
    "未命中",
    "",
}
KG_CORE_RAW_KEYWORDS = [
    "缺陷", "空位", "杂质", "掺杂", "包裹体", "散射", "位错", "生长", "过饱和",
    "加工", "表面", "亚表面", "激光损伤", "损伤", "LIDT", "裂纹", "开裂", "应力",
    "吸收", "光热", "氢键", "质子", "籽晶", "固定", "DFT", "第一性原理", "分子动力学", "有限元",
]


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _top_chain(chain: pd.DataFrame, top_n: int) -> pd.DataFrame:
    return chain.sort_values("文献数", ascending=False).head(top_n).copy()


def _relationship_matrix(chain: pd.DataFrame, top_n=28):
    """
    双路径关系矩阵：
    左：缺陷/应力来源 × 局部机制
    右：局部机制 × 宏观后果

    使用浅色“论文图版”风格，和全站国科蓝主题一致。
    """
    chain = _top_chain(chain, top_n)

    sm = (
        chain.groupby(
            ["缺陷/应力来源", "作用机制"],
            as_index=False,
        )["文献数"]
        .sum()
    )

    mo = (
        chain.groupby(
            ["作用机制", "宏观结果"],
            as_index=False,
        )["文献数"]
        .sum()
    )

    sources = list(
        sm.groupby("缺陷/应力来源")["文献数"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    mechs = list(
        chain.groupby("作用机制")["文献数"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    outcomes = list(
        mo.groupby("宏观结果")["文献数"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    sm_pivot = (
        sm.pivot(
            index="缺陷/应力来源",
            columns="作用机制",
            values="文献数",
        )
        .fillna(0)
        .reindex(index=sources, columns=mechs)
    )

    mo_pivot = (
        mo.pivot(
            index="作用机制",
            columns="宏观结果",
            values="文献数",
        )
        .fillna(0)
        .reindex(index=mechs, columns=outcomes)
    )

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=.17,
        subplot_titles=(
            "缺陷 / 应力来源  →  局部机制",
            "局部机制  →  宏观后果",
        ),
    )

    # 浅色科研蓝：零值近纸白，证据越强越接近国科蓝/青蓝。
    colorscale = [
        [0.00, "#F5F7F8"],
        [0.08, "#EDF2F6"],
        [0.28, "#D5E3F0"],
        [0.52, "#A7C4DE"],
        [0.74, "#5F92C2"],
        [0.90, "#2E6CA8"],
        [1.00, "#168B94"],
    ]

    common = dict(
        colorscale=colorscale,
        zmin=0,
        hoverongaps=False,
        xgap=5,
        ygap=5,
    )

    fig.add_trace(
        go.Heatmap(
            z=sm_pivot.values,
            x=sm_pivot.columns,
            y=sm_pivot.index,
            showscale=False,
            text=np.where(
                sm_pivot.values > 0,
                sm_pivot.values.astype(int).astype(str),
                "",
            ),
            texttemplate="%{text}",
            textfont=dict(size=12, color="#17324E"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "→ %{x}<br>"
                "关联文献 %{z:.0f} 篇"
                "<extra></extra>"
            ),
            **common,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Heatmap(
            z=mo_pivot.values,
            x=mo_pivot.columns,
            y=mo_pivot.index,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="文献数",
                    font=dict(color="#52677F", size=11),
                ),
                thickness=9,
                len=.68,
                x=1.025,
                outlinewidth=0,
                tickfont=dict(color="#607287", size=10),
            ),
            text=np.where(
                mo_pivot.values > 0,
                mo_pivot.values.astype(int).astype(str),
                "",
            ),
            texttemplate="%{text}",
            textfont=dict(size=12, color="#17324E"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "→ %{x}<br>"
                "关联文献 %{z:.0f} 篇"
                "<extra></extra>"
            ),
            **common,
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        paper_bgcolor="rgba(255,255,252,0)",
        plot_bgcolor="rgba(255,255,252,0)",
        height=590,
        # 左侧增加空间，避免“本征点缺陷”等标签被裁掉。
        margin=dict(l=118, r=82, t=78, b=38),
        font=dict(
            family='Inter, "Microsoft YaHei", Arial',
            color="#314B67",
            size=12,
        ),
    )

    fig.update_annotations(
        font=dict(
            color="#17324E",
            size=14,
            family='Inter, "Microsoft YaHei", Arial',
        )
    )

    fig.update_xaxes(
        side="top",
        tickangle=-20,
        tickfont=dict(color="#52677F", size=10.5),
        showgrid=False,
        zeroline=False,
        ticks="",
    )

    fig.update_yaxes(
        tickfont=dict(color="#52677F", size=10.5),
        showgrid=False,
        zeroline=False,
        ticks="",
        autorange="reversed",
        automargin=True,
    )

    return fig

def _sphere_points(n, radius, phase):
    if n <= 0:
        return []
    points = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - 2.0 * (i + .5) / n
        rr = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden * i + phase
        points.append((radius * math.cos(theta) * rr, radius * y, radius * math.sin(theta) * rr))
    return points


def _orbit_trace(radius, plane="xy", color="rgba(121,145,178,.16)"):
    t = np.linspace(0, 2 * np.pi, 180)
    if plane == "xy":
        x, y, z = radius*np.cos(t), radius*np.sin(t), np.zeros_like(t)
    elif plane == "xz":
        x, y, z = radius*np.cos(t), np.zeros_like(t), radius*np.sin(t)
    else:
        x, y, z = np.zeros_like(t), radius*np.cos(t), radius*np.sin(t)
    return go.Scatter3d(
        x=x, y=y, z=z,
        mode="lines",
        line=dict(color=color, width=1.5),
        hoverinfo="skip",
        showlegend=False,
    )



def _curve_points(p0, p1, lift=.55, inward=.38, n=22):
    """Quadratic Bézier curve for a smoother research-network edge."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    mid = (p0 + p1) / 2
    control = mid * inward
    direction = p1 - p0
    dist = float(np.linalg.norm(direction))
    control[2] += lift + dist * .08

    t = np.linspace(0, 1, n)
    pts = (
        ((1 - t) ** 2)[:, None] * p0
        + (2 * (1 - t) * t)[:, None] * control
        + (t ** 2)[:, None] * p1
    )
    return pts


def _constellation_positions(names, radius, z_base=0.0, phase=0.0, y_scale=.82, z_wave=.42):
    """Deterministic orbital positions with a mild 3D wave."""
    out = {}
    n = max(1, len(names))
    for i, name in enumerate(names):
        a = phase + 2 * math.pi * i / n
        x = radius * math.cos(a)
        y = radius * y_scale * math.sin(a)
        z = z_base + z_wave * math.sin(2 * a + phase / 2)
        out[name] = (x, y, z)
    return out



def _fibonacci_shell_positions(names, radius, phase=0.0):
    """Evenly distribute nodes on a spherical shell."""
    names = list(names)
    n = max(1, len(names))
    out = {}
    golden = math.pi * (3.0 - math.sqrt(5.0))

    for i, name in enumerate(names):
        y = 1 - (2 * (i + .5) / n)
        r_xy = math.sqrt(max(0.0, 1 - y * y))
        theta = golden * i + phase
        x = radius * r_xy * math.cos(theta)
        z = radius * r_xy * math.sin(theta)
        out[name] = (x, radius * y, z)

    return out


def _sphere_wireframe(radius, color="rgba(110,160,205,.10)", width=1.0):
    """One lightweight trace containing latitude/longitude wireframe lines."""
    xs, ys, zs = [], [], []

    # latitudes
    for lat in [-50, -25, 0, 25, 50]:
        phi = math.radians(lat)
        rr = radius * math.cos(phi)
        yy = radius * math.sin(phi)
        a = np.linspace(0, 2 * math.pi, 110)
        xs.extend((rr * np.cos(a)).tolist() + [None])
        ys.extend(([yy] * len(a)) + [None])
        zs.extend((rr * np.sin(a)).tolist() + [None])

    # longitudes
    for lon in [0, 45, 90, 135]:
        lam = math.radians(lon)
        a = np.linspace(-math.pi / 2, math.pi / 2, 100)
        x = radius * np.cos(a) * math.cos(lam)
        y = radius * np.sin(a)
        z = radius * np.cos(a) * math.sin(lam)
        xs.extend(x.tolist() + [None])
        ys.extend(y.tolist() + [None])
        zs.extend(z.tolist() + [None])

    return go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="lines",
        line=dict(color=color, width=width),
        hoverinfo="skip",
        showlegend=False,
    )


def _sphere_label(radius, text, color):
    return go.Scatter3d(
        x=[0], y=[radius + .28], z=[0],
        mode="text",
        text=[text],
        textfont=dict(color=color, size=9),
        hoverinfo="skip",
        showlegend=False,
    )


def _orbit_ellipse(radius, z=0.0, phase=0.0, y_scale=.82, color="rgba(120,160,210,.16)"):
    a = np.linspace(0, 2 * math.pi, 180)
    x = radius * np.cos(a)
    y = radius * y_scale * np.sin(a)
    zz = z + .05 * np.sin(2 * a + phase)
    return go.Scatter3d(
        x=x, y=y, z=zz,
        mode="lines",
        line=dict(color=color, width=1.4),
        hoverinfo="skip",
        showlegend=False,
    )


def _edge_buckets(df, source_col, target_col, positions, source_prefix, target_prefix, max_w, focus=None):
    """
    Merge many curved edges into a few traces by strength bucket.
    This looks richer than straight lines while staying far lighter than
    one Plotly trace per relation.
    """
    palette = {
        "weak": ("rgba(101,139,196,.18)", 1.2),
        "medium": ("rgba(82,137,213,.32)", 2.2),
        "strong": ("rgba(40,181,190,.58)", 3.6),
        "focus": ("rgba(245,177,79,.95)", 5.2),
    }
    groups = {k: {"x": [], "y": [], "z": []} for k in palette}

    for _, r in df.iterrows():
        w = float(r["文献数"])
        s = str(r[source_col])
        t = str(r[target_col])
        connected = focus is None or focus in {s, t}

        if focus is not None and connected:
            bucket = "focus"
        else:
            ratio = w / max(max_w, 1.0)
            bucket = "strong" if ratio >= .5 else "medium" if ratio >= .22 else "weak"

        p0 = positions[source_prefix + "|" + s]
        p1 = positions[target_prefix + "|" + t]
        pts = _curve_points(
            p0, p1,
            lift=.45 if bucket == "weak" else .62 if bucket == "medium" else .78,
            inward=.44 if source_prefix == "S" else .56,
            n=20,
        )
        groups[bucket]["x"].extend(pts[:, 0].tolist() + [None])
        groups[bucket]["y"].extend(pts[:, 1].tolist() + [None])
        groups[bucket]["z"].extend(pts[:, 2].tolist() + [None])

    traces = []
    for bucket, xyz in groups.items():
        if not xyz["x"]:
            continue
        color, width = palette[bucket]
        if focus is not None and bucket != "focus":
            color = color.replace(")", ",") if False else color
            # dim non-focus lines
            if bucket == "weak":
                color = "rgba(82,112,154,.07)"
            elif bucket == "medium":
                color = "rgba(82,112,154,.10)"
            elif bucket == "strong":
                color = "rgba(82,112,154,.14)"
        traces.append(
            go.Scatter3d(
                x=xyz["x"], y=xyz["y"], z=xyz["z"],
                mode="lines",
                line=dict(color=color, width=width),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    return traces


def _orbital_graph(
    chain: pd.DataFrame,
    top_n=34,
    min_evidence=1,
    focus_layer="全局",
    focus_node=None,
    camera_name="透视",
):
    """
    KDP Mechanism Constellation 2.0
    - three orbital layers
    - curved evidence paths
    - evidence-weighted node size
    - focus mode
    - hover relationship summaries
    - dark scientific-instrument presentation
    """
    work = chain[chain["文献数"] >= int(min_evidence)].copy()
    if work.empty:
        return go.Figure()

    work = _top_chain(work, top_n)

    sc = work.groupby("缺陷/应力来源")["文献数"].sum().sort_values(ascending=False)
    mc = work.groupby("作用机制")["文献数"].sum().sort_values(ascending=False)
    oc = work.groupby("宏观结果")["文献数"].sum().sort_values(ascending=False)

    # Three concentric spherical research shells:
    # inner = source, middle = mechanism, outer = outcome.
    source_pos = _fibonacci_shell_positions(list(sc.index), 2.05, phase=.18)
    mech_pos = _fibonacci_shell_positions(list(mc.index), 3.35, phase=.86)
    out_pos = _fibonacci_shell_positions(list(oc.index), 4.65, phase=1.42)

    positions = {"CENTER": (0., 0., 0.)}
    positions.update({"S|" + k: v for k, v in source_pos.items()})
    positions.update({"M|" + k: v for k, v in mech_pos.items()})
    positions.update({"O|" + k: v for k, v in out_pos.items()})

    focus = focus_node if focus_layer != "全局" and focus_node else None
    max_w = max(float(work["文献数"].max()), 1.0)

    # Build connection summaries for hover.
    sm = (
        work.groupby(["缺陷/应力来源", "作用机制"], as_index=False)["文献数"]
        .sum()
        .sort_values("文献数", ascending=False)
    )
    mo = (
        work.groupby(["作用机制", "宏观结果"], as_index=False)["文献数"]
        .sum()
        .sort_values("文献数", ascending=False)
    )

    fig = go.Figure()

    # Deep-space particles: one trace, deterministic and lightweight.
    rng = np.random.default_rng(20260818)
    stars = rng.normal(0, 1, size=(85, 3))
    norms = np.linalg.norm(stars, axis=1, keepdims=True)
    stars = stars / np.where(norms == 0, 1, norms)
    radii = rng.uniform(4.9, 6.3, size=(85, 1))
    stars = stars * radii
    fig.add_trace(
        go.Scatter3d(
            x=stars[:, 0], y=stars[:, 1], z=stars[:, 2],
            mode="markers",
            marker=dict(size=rng.uniform(1.0, 2.2, 85), color="rgba(180,211,238,.25)"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Spherical-shell architecture: subtle scientific wireframes.
    fig.add_trace(_sphere_wireframe(2.05, "rgba(232,145,63,.14)", 1.0))
    fig.add_trace(_sphere_wireframe(3.35, "rgba(118,131,226,.13)", 1.0))
    fig.add_trace(_sphere_wireframe(4.65, "rgba(40,181,184,.12)", 1.0))

    fig.add_trace(_sphere_label(2.05, "SHELL 01 · DEFECT / STRESS", "rgba(235,166,99,.62)"))
    fig.add_trace(_sphere_label(3.35, "SHELL 02 · MECHANISM", "rgba(157,166,240,.62)"))
    fig.add_trace(_sphere_label(4.65, "SHELL 03 · OUTCOME", "rgba(95,215,215,.58)"))

    # Center-to-source spokes, bucketed into a single trace.
    cx, cy, cz = [], [], []
    for n, w in sc.items():
        p1 = positions["S|" + n]
        pts = _curve_points((0, 0, 0), p1, lift=.20, inward=.65, n=18)
        cx.extend(pts[:, 0].tolist() + [None])
        cy.extend(pts[:, 1].tolist() + [None])
        cz.extend(pts[:, 2].tolist() + [None])
    fig.add_trace(
        go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color="rgba(229,139,73,.14)", width=1.4),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Curved evidence paths.
    for tr in _edge_buckets(
        sm, "缺陷/应力来源", "作用机制",
        positions, "S", "M", max_w, focus=focus
    ):
        fig.add_trace(tr)

    for tr in _edge_buckets(
        mo, "作用机制", "宏观结果",
        positions, "M", "O", max_w, focus=focus
    ):
        fig.add_trace(tr)

    # Determine related nodes for focus mode.
    related_sources = set(sc.index)
    related_mechs = set(mc.index)
    related_outcomes = set(oc.index)

    if focus:
        if focus_layer == "缺陷/应力来源":
            related_sources = {focus}
            related_mechs = set(work.loc[work["缺陷/应力来源"] == focus, "作用机制"])
            related_outcomes = set(
                work.loc[work["作用机制"].isin(related_mechs), "宏观结果"]
            )
        elif focus_layer == "作用机制":
            related_mechs = {focus}
            related_sources = set(work.loc[work["作用机制"] == focus, "缺陷/应力来源"])
            related_outcomes = set(work.loc[work["作用机制"] == focus, "宏观结果"])
        elif focus_layer == "宏观结果":
            related_outcomes = {focus}
            related_mechs = set(work.loc[work["宏观结果"] == focus, "作用机制"])
            related_sources = set(
                work.loc[work["作用机制"].isin(related_mechs), "缺陷/应力来源"]
            )

    def add_layer_nodes(names, counts, prefix, base_color, layer_name, related_set, top_labels=4):
        names = list(names)
        max_count = max(float(counts.max()), 1.0)

        xs, ys, zs, sizes, colors, opacities, hover, labels = [], [], [], [], [], [], [], []
        top_names = set(counts.head(top_labels).index)

        for n in names:
            x, y, z = positions[prefix + "|" + n]
            c = float(counts[n])
            is_related = n in related_set
            node_opacity = .98 if is_related else .16
            node_color = base_color if is_related else "#526071"
            size = 12 + 18 * math.sqrt(c / max_count)

            # top connected relation snippets
            if prefix == "S":
                rel = sm[sm["缺陷/应力来源"] == n].head(3)
                snippets = [
                    f"{r['作用机制']} · {int(r['文献数'])}篇"
                    for _, r in rel.iterrows()
                ]
            elif prefix == "M":
                a = sm[sm["作用机制"] == n].head(2)
                b = mo[mo["作用机制"] == n].head(2)
                snippets = [
                    f"← {r['缺陷/应力来源']} · {int(r['文献数'])}篇"
                    for _, r in a.iterrows()
                ] + [
                    f"→ {r['宏观结果']} · {int(r['文献数'])}篇"
                    for _, r in b.iterrows()
                ]
            else:
                rel = mo[mo["宏观结果"] == n].head(3)
                snippets = [
                    f"{r['作用机制']} · {int(r['文献数'])}篇"
                    for _, r in rel.iterrows()
                ]

            xs.append(x); ys.append(y); zs.append(z)
            sizes.append(size)
            # Scatter3d.marker.opacity only accepts a scalar in Plotly.
            # Encode per-node transparency directly in RGBA marker colors instead.
            if str(node_color).startswith("#") and len(str(node_color)) == 7:
                h = str(node_color).lstrip("#")
                rr, gg, bb = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                rgba_color = f"rgba({rr},{gg},{bb},{node_opacity:.3f})"
            else:
                rgba_color = node_color
            colors.append(rgba_color)
            opacities.append(node_opacity)
            labels.append(n if (n in top_names or n == focus) else "")
            hover.append(
                f"<b>{n}</b>"
                f"<br><span style='color:#A7B9CC'>{layer_name}</span>"
                f"<br>累计关系文献：<b>{int(c)}</b> 篇"
                + ("<br>" + "<br>".join(snippets) if snippets else "")
                + ("<br><b>当前聚焦路径</b>" if n == focus else "")
            )

        # halo
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="markers",
                marker=dict(
                    size=[s * 1.65 for s in sizes],
                    color=base_color,
                    opacity=.07 if focus is None else .045,
                    line=dict(width=0),
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="markers+text",
                text=labels,
                textposition="top center",
                textfont=dict(color="#D9E7F6", size=10),
                marker=dict(
                    size=sizes,
                    color=colors,
                    opacity=1.0,
                    line=dict(color="rgba(255,255,255,.78)", width=.8),
                ),
                hovertext=hover,
                hoverinfo="text",
                name=layer_name,
            )
        )

    # Center halo layers.
    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0], mode="markers",
            marker=dict(size=68, color="rgba(25,150,177,.08)", line=dict(width=0)),
            hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0], mode="markers",
            marker=dict(size=48, color="rgba(35,126,191,.22)", line=dict(width=0)),
            hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode="markers+text",
            text=["KDP"],
            textposition="middle center",
            marker=dict(
                size=31,
                color="#1A89B3",
                line=dict(color="#EAF6FF", width=1.4),
            ),
            textfont=dict(color="white", size=13),
            hovertext=[
                "<b>KDP Research Core</b><br>"
                "缺陷来源 → 局部机制 → 宏观后果<br>"
                f"当前显示关系文献 {int(work['文献数'].sum())} 篇"
            ],
            hoverinfo="text",
            name="KDP研究核心",
        )
    )

    add_layer_nodes(sc.index, sc, "S", "#E8913F", "缺陷 / 应力来源", related_sources)
    add_layer_nodes(mc.index, mc, "M", "#7683E2", "局部作用机制", related_mechs)
    add_layer_nodes(oc.index, oc, "O", "#28B5B8", "宏观结果", related_outcomes)


    cameras = {
        "透视": dict(eye=dict(x=1.55, y=1.72, z=1.28), center=dict(x=0, y=0, z=0)),
        "俯视": dict(eye=dict(x=.06, y=.10, z=2.72), center=dict(x=0, y=0, z=0)),
        "侧视": dict(eye=dict(x=2.72, y=.08, z=.28), center=dict(x=0, y=0, z=0)),
    }

    focus_label = focus or "GLOBAL"

    fig.update_layout(
        paper_bgcolor="#06101D",
        plot_bgcolor="#06101D",
        margin=dict(l=0, r=0, t=58, b=0),
        legend=dict(
            orientation="h",
            y=1.035,
            x=.02,
            bgcolor="rgba(4,12,22,.45)",
            bordercolor="rgba(169,198,226,.12)",
            borderwidth=1,
            font=dict(color="#C8D6E6", size=10),
        ),
        scene=dict(
            bgcolor="#06101D",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="cube",
            camera=cameras.get(camera_name, cameras["透视"]),
            dragmode="orbit",
        ),
        font=dict(family='Inter,"Microsoft YaHei"', color="#DDE7F4"),
        annotations=[
            dict(
                x=.015, y=.985, xref="paper", yref="paper",
                showarrow=False, align="left",
                text=(
                    "<b>KDP SPHERICAL MECHANISM MAP</b>"
                    f"<br><span style='font-size:10px;color:#86A0B8'>FOCUS · {focus_label}</span>"
                ),
                font=dict(color="#DDEAF7", size=12),
                bgcolor="rgba(8,20,35,.58)",
                bordercolor="rgba(122,159,194,.16)",
                borderpad=8,
            ),
            dict(
                x=.985, y=.985, xref="paper", yref="paper",
                showarrow=False, align="right",
                text=(
                    f"<b>{len(sc)+len(mc)+len(oc)+1}</b> NODES"
                    f" · <b>{len(sm)+len(mo)}</b> LINKS"
                    f" · <b>{int(work['文献数'].sum())}</b> EVIDENCE"
                ),
                font=dict(color="#91ABC2", size=10),
                bgcolor="rgba(8,20,35,.42)",
                borderpad=6,
            ),
        ],
    )
    return fig



def _orbital_graph_lite(chain: pd.DataFrame, top_n=26, camera_name="透视"):
    """Compatibility fallback: fewer traces, no per-point alpha tricks."""
    work = _top_chain(chain, min(top_n, len(chain))).copy()
    if work.empty:
        return go.Figure()

    sc = work.groupby("缺陷/应力来源")["文献数"].sum().sort_values(ascending=False)
    mc = work.groupby("作用机制")["文献数"].sum().sort_values(ascending=False)
    oc = work.groupby("宏观结果")["文献数"].sum().sort_values(ascending=False)

    sp = _constellation_positions(list(sc.index), 2.1, .1, .1, .78, .25)
    mp = _constellation_positions(list(mc.index), 3.35, .35, .7, .82, .32)
    op = _constellation_positions(list(oc.index), 4.55, -.2, 1.2, .86, .36)

    pos = {}
    pos.update({"S|" + k: v for k, v in sp.items()})
    pos.update({"M|" + k: v for k, v in mp.items()})
    pos.update({"O|" + k: v for k, v in op.items()})

    sm = work.groupby(["缺陷/应力来源", "作用机制"], as_index=False)["文献数"].sum()
    mo = work.groupby(["作用机制", "宏观结果"], as_index=False)["文献数"].sum()

    fig = go.Figure()
    fig.add_trace(_orbit_ellipse(2.1, .1, color="rgba(232,145,63,.22)"))
    fig.add_trace(_orbit_ellipse(3.35, .35, color="rgba(118,131,226,.22)"))
    fig.add_trace(_orbit_ellipse(4.55, -.2, color="rgba(40,181,184,.22)"))

    # All links in one line trace for maximum compatibility.
    xs, ys, zs = [], [], []
    for _, r in sm.iterrows():
        a = pos["S|" + str(r["缺陷/应力来源"])]
        b = pos["M|" + str(r["作用机制"])]
        pts = _curve_points(a, b, lift=.55, inward=.45, n=18)
        xs.extend(pts[:, 0].tolist() + [None])
        ys.extend(pts[:, 1].tolist() + [None])
        zs.extend(pts[:, 2].tolist() + [None])
    for _, r in mo.iterrows():
        a = pos["M|" + str(r["作用机制"])]
        b = pos["O|" + str(r["宏观结果"])]
        pts = _curve_points(a, b, lift=.65, inward=.52, n=18)
        xs.extend(pts[:, 0].tolist() + [None])
        ys.extend(pts[:, 1].tolist() + [None])
        zs.extend(pts[:, 2].tolist() + [None])

    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs, mode="lines",
            line=dict(color="rgba(113,162,205,.28)", width=2),
            hoverinfo="skip", showlegend=False,
        )
    )

    def add_nodes(counts, positions, color, name):
        max_count = max(float(counts.max()), 1.0)
        names = list(counts.index)
        coords = [positions[n] for n in names]
        fig.add_trace(
            go.Scatter3d(
                x=[p[0] for p in coords],
                y=[p[1] for p in coords],
                z=[p[2] for p in coords],
                mode="markers+text",
                text=[n if i < 4 else "" for i, n in enumerate(names)],
                textposition="top center",
                marker=dict(
                    size=[11 + 16 * math.sqrt(float(counts[n]) / max_count) for n in names],
                    color=color,
                    opacity=.92,
                    line=dict(color="rgba(255,255,255,.7)", width=.8),
                ),
                hovertext=[
                    f"<b>{n}</b><br>{name}<br>累计关系文献：{int(counts[n])} 篇"
                    for n in names
                ],
                hoverinfo="text",
                textfont=dict(color="#DDE7F4", size=10),
                name=name,
            )
        )

    add_nodes(sc, sp, "#E8913F", "缺陷 / 应力来源")
    add_nodes(mc, mp, "#7683E2", "局部作用机制")
    add_nodes(oc, op, "#28B5B8", "宏观结果")

    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0], mode="markers+text",
            text=["KDP"], textposition="middle center",
            marker=dict(size=30, color="#178BB1", line=dict(color="white", width=1.2)),
            textfont=dict(color="white", size=13),
            hoverinfo="skip", name="KDP研究核心",
        )
    )

    cameras = {
        "透视": dict(eye=dict(x=1.45, y=1.62, z=1.1)),
        "俯视": dict(eye=dict(x=.05, y=.05, z=2.55)),
        "侧视": dict(eye=dict(x=2.55, y=.08, z=.35)),
    }
    fig.update_layout(
        paper_bgcolor="#06101D",
        plot_bgcolor="#06101D",
        margin=dict(l=0, r=0, t=42, b=0),
        scene=dict(
            bgcolor="#06101D",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="cube",
            camera=cameras.get(camera_name, cameras["透视"]),
            dragmode="orbit",
        ),
        legend=dict(
            orientation="h", y=1.02, x=.02,
            bgcolor="rgba(4,12,22,.45)",
            font=dict(color="#C8D6E6", size=10),
        ),
        font=dict(family='Inter,"Microsoft YaHei"', color="#DDE7F4"),
    )
    return fig



def _sector_positions(names, radius, az_start, az_end, phase=0.0):
    """Place structural nodes in category sectors on one mechanism sphere."""
    names = list(names)
    n = max(1, len(names))
    out = {}
    for i, name in enumerate(names):
        f = (i + .5) / n
        az = math.radians(az_start + (az_end - az_start) * f)
        elev = .38 * math.sin(2 * math.pi * f + phase)
        x = radius * math.cos(elev) * math.cos(az)
        y = radius * math.cos(elev) * math.sin(az)
        z = radius * math.sin(elev)
        out[name] = (x, y, z)
    return out


def _paper_rank(work: pd.DataFrame) -> pd.DataFrame:
    """Stable ranking for paper nodes without assuming every score column exists."""
    d = work.copy()
    d["_kg_rank"] = 0.0
    for col, weight in [
        ("V5核心排序分", 1.0),
        ("V5科研优先分", .75),
        ("综合重要度", .55),
        ("被引次数", .02),
        ("年份", .01),
    ]:
        if col in d.columns:
            d["_kg_rank"] += pd.to_numeric(d[col], errors="coerce").fillna(0) * weight

    if "V5推荐等级" in d.columns:
        tier_bonus = {
            "S 核心 50": 50,
            "A 重点 150": 25,
            "B 扩展 800": 8,
        }
        d["_kg_rank"] += d["V5推荐等级"].map(tier_bonus).fillna(0)

    dedup_cols = ["题名"]
    if "DOI" in d.columns:
        # Prefer title dedup because many old records have no DOI.
        pass
    d = d.sort_values("_kg_rank", ascending=False)
    d = d.drop_duplicates(subset=dedup_cols, keep="first")
    return d


def _rgba(hex_color, alpha):
    h = str(hex_color).lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _dense_evidence_globe(
    paper_work: pd.DataFrame,
    chain: pd.DataFrame,
    relation_limit=36,
    paper_limit=180,
    focus_layer="全局",
    focus_node=None,
    camera_name="透视",
    show_papers=True,
):
    """
    Dense 3D research evidence network.

    Structural level:
      KDP core -> defect/stress -> mechanism -> outcome

    Evidence level:
      each paper becomes a real node and is connected to its classified
      source/mechanism/outcome. Hundreds of paper links are merged into
      three Scatter3d line traces for performance.
    """
    c = _top_chain(chain, min(relation_limit, len(chain))).copy()
    if c.empty:
        return go.Figure(), pd.DataFrame(), 0, 0

    # Only papers belonging to visible structural paths.
    keys = set(
        (
            str(r["缺陷/应力来源"]),
            str(r["作用机制"]),
            str(r["宏观结果"]),
        )
        for _, r in c.iterrows()
    )
    pw = paper_work[
        paper_work.apply(
            lambda r: (
                str(r.get("缺陷/应力来源", "")),
                str(r.get("作用机制", "")),
                str(r.get("宏观结果", "")),
            ) in keys,
            axis=1,
        )
    ].copy()

    if focus_node:
        if focus_layer == "缺陷/应力来源":
            pw = pw[pw["缺陷/应力来源"].astype(str) == str(focus_node)]
            c = c[c["缺陷/应力来源"].astype(str) == str(focus_node)]
        elif focus_layer == "作用机制":
            pw = pw[pw["作用机制"].astype(str) == str(focus_node)]
            c = c[c["作用机制"].astype(str) == str(focus_node)]
        elif focus_layer == "宏观结果":
            pw = pw[pw["宏观结果"].astype(str) == str(focus_node)]
            c = c[c["宏观结果"].astype(str) == str(focus_node)]

    pw = _paper_rank(pw)
    if show_papers and paper_limit > 0:
        pw = pw.head(min(paper_limit, len(pw))).copy()
    else:
        pw = pw.head(0).copy()

    # Structural nodes.
    sc = c.groupby("缺陷/应力来源")["文献数"].sum().sort_values(ascending=False)
    mc = c.groupby("作用机制")["文献数"].sum().sort_values(ascending=False)
    oc = c.groupby("宏观结果")["文献数"].sum().sort_values(ascending=False)

    source_pos = _sector_positions(sc.index, 2.75, 125, 225, phase=.2)
    mech_pos = _sector_positions(mc.index, 2.75, 238, 352, phase=1.1)
    outcome_pos = _sector_positions(oc.index, 2.75, -5, 108, phase=2.0)

    structural_pos = {}
    structural_pos.update({"S|" + k: v for k, v in source_pos.items()})
    structural_pos.update({"M|" + k: v for k, v in mech_pos.items()})
    structural_pos.update({"O|" + k: v for k, v in outcome_pos.items()})

    fig = go.Figure()

    # Background sphere / instrument grid.
    fig.add_trace(_sphere_wireframe(3.05, "rgba(123,163,202,.11)", 1.0))
    fig.add_trace(_sphere_wireframe(4.95, "rgba(89,136,177,.055)", .8))

    rng = np.random.default_rng(20260818)
    stars = rng.normal(size=(58, 3))
    norms = np.linalg.norm(stars, axis=1, keepdims=True)
    stars = stars / np.where(norms == 0, 1, norms)
    stars = stars * rng.uniform(5.2, 6.2, size=(58, 1))
    fig.add_trace(
        go.Scatter3d(
            x=stars[:, 0], y=stars[:, 1], z=stars[:, 2],
            mode="markers",
            marker=dict(size=1.4, color="rgba(187,210,229,.23)"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Strong structural paths.
    sm = (
        c.groupby(["缺陷/应力来源", "作用机制"], as_index=False)["文献数"]
        .sum()
        .sort_values("文献数", ascending=False)
    )
    mo = (
        c.groupby(["作用机制", "宏观结果"], as_index=False)["文献数"]
        .sum()
        .sort_values("文献数", ascending=False)
    )
    max_w = max(float(c["文献数"].max()), 1.0)

    def add_structural_edges(
        df_edge,
        a_col,
        b_col,
        a_prefix,
        b_prefix,
        base_rgb,
        relation_name,
    ):
        """Aggregated structural relations with evidence-scaled line strength."""
        if df_edge.empty:
            return

        max_count = max(float(df_edge["文献数"].max()), 1.0)
        buckets = {
            "weak": {"x": [], "y": [], "z": [], "width": 1.3, "alpha": .18},
            "mid": {"x": [], "y": [], "z": [], "width": 2.7, "alpha": .42},
            "strong": {"x": [], "y": [], "z": [], "width": 4.8, "alpha": .78},
        }
        hx, hy, hz, htext = [], [], [], []

        for _, r in df_edge.iterrows():
            a_name = str(r[a_col])
            b_name = str(r[b_col])
            a = structural_pos[a_prefix + "|" + a_name]
            b = structural_pos[b_prefix + "|" + b_name]
            n_ev = int(r["文献数"])
            ratio = n_ev / max_count
            bucket = "strong" if ratio >= .55 else "mid" if ratio >= .25 else "weak"
            pts = _curve_points(a, b, lift=.32, inward=.58, n=22)
            buckets[bucket]["x"].extend(pts[:, 0].tolist() + [None])
            buckets[bucket]["y"].extend(pts[:, 1].tolist() + [None])
            buckets[bucket]["z"].extend(pts[:, 2].tolist() + [None])

            mid = pts[len(pts)//2]
            hx.append(float(mid[0])); hy.append(float(mid[1])); hz.append(float(mid[2]))
            htext.append(
                f"<b>{relation_name}</b>"
                f"<br>{a_name} → {b_name}"
                f"<br>当前数据库关联文献：<b>{n_ev}</b> 篇"
                f"<br><span style='color:#9EB2C5'>聚合文献关系，不自动等同于因果关系。</span>"
            )

        for key in ["weak", "mid", "strong"]:
            d = buckets[key]
            if not d["x"]:
                continue
            fig.add_trace(
                go.Scatter3d(
                    x=d["x"], y=d["y"], z=d["z"], mode="lines",
                    line=dict(
                        color=f"rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},{d['alpha']})",
                        width=d["width"],
                    ),
                    hoverinfo="skip", showlegend=False,
                )
            )

        fig.add_trace(
            go.Scatter3d(
                x=hx, y=hy, z=hz, mode="markers",
                marker=dict(
                    size=8,
                    color=f"rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},0.025)",
                    line=dict(width=0),
                ),
                hovertext=htext, hoverinfo="text", showlegend=False,
            )
        )

    add_structural_edges(
        sm, "缺陷/应力来源", "作用机制", "S", "M", (119,115,216),
        "聚合关系｜缺陷/应力来源 → 局部机制",
    )
    add_structural_edges(
        mo, "作用机制", "宏观结果", "M", "O", (33,173,177),
        "聚合关系｜局部机制 → 宏观结果",
    )

    # KDP core.
    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode="markers+text",
            text=["KDP"],
            textposition="middle center",
            marker=dict(
                size=36,
                color="#176BAC",
                line=dict(color="#CDE8F4", width=1.5),
            ),
            textfont=dict(color="white", size=14),
            hovertext=["<b>KDP 研究核心</b><br>结构节点与文献证据的共同中心"],
            hoverinfo="text",
            name="KDP研究核心",
        )
    )

    # Core -> source lines.
    xs, ys, zs = [], [], []
    for n in sc.index:
        p = structural_pos["S|" + str(n)]
        pts = _curve_points((0, 0, 0), p, lift=.05, inward=.72, n=18)
        xs.extend(pts[:, 0].tolist() + [None])
        ys.extend(pts[:, 1].tolist() + [None])
        zs.extend(pts[:, 2].tolist() + [None])
    fig.add_trace(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines",
            line=dict(color="rgba(225,140,62,.18)", width=1.2),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    def add_structural_nodes(counts, pos, color, label, prefix):
        names = list(counts.index)
        max_count = max(float(counts.max()), 1.0)
        coords = [pos[n] for n in names]
        text = []
        hover = []
        for i, n in enumerate(names):
            text.append(n if i < 6 or n == focus_node else "")
            hover.append(
                f"<b>{n}</b><br>{label}<br>"
                f"累计关系证据：<b>{int(counts[n])}</b> 篇"
            )

        # halo
        fig.add_trace(
            go.Scatter3d(
                x=[p[0] for p in coords],
                y=[p[1] for p in coords],
                z=[p[2] for p in coords],
                mode="markers",
                marker=dict(
                    size=[20 + 16 * math.sqrt(float(counts[n]) / max_count) for n in names],
                    color=_rgba(color, .08),
                    opacity=1,
                    line=dict(width=0),
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=[p[0] for p in coords],
                y=[p[1] for p in coords],
                z=[p[2] for p in coords],
                mode="markers+text",
                text=text,
                textposition="top center",
                textfont=dict(color="#DCE8F2", size=10),
                marker=dict(
                    size=[11 + 12 * math.sqrt(float(counts[n]) / max_count) for n in names],
                    color=color,
                    opacity=.95,
                    line=dict(color="rgba(255,255,255,.72)", width=.8),
                ),
                hovertext=hover,
                hoverinfo="text",
                name=label,
            )
        )

    add_structural_nodes(sc, source_pos, "#E28A35", "缺陷 / 应力来源", "S")
    add_structural_nodes(mc, mech_pos, "#7773D8", "局部作用机制", "M")
    add_structural_nodes(oc, outcome_pos, "#21ADB1", "宏观结果", "O")

    paper_edge_count = 0

    # --------------------------------------------------------
    # Paper-level evidence cloud: each paper is a real node.
    # --------------------------------------------------------
    if len(pw):
        years = pd.to_numeric(pw.get("年份", pd.Series(index=pw.index)), errors="coerce")
        y_min = int(years.dropna().min()) if years.notna().any() else 2000
        y_max = int(years.dropna().max()) if years.notna().any() else y_min + 1
        year_span = max(1, y_max - y_min)

        paper_coords = []
        paper_hover = []
        paper_colors = []
        paper_sizes = []
        paper_labels = []

        # One merged edge trace per classification family.
        edge_xyz = {
            "S": {"x": [], "y": [], "z": [], "hx": [], "hy": [], "hz": [], "hover": []},
            "M": {"x": [], "y": [], "z": [], "hx": [], "hy": [], "hz": [], "hover": []},
            "O": {"x": [], "y": [], "z": [], "hx": [], "hy": [], "hz": [], "hover": []},
        }

        tier_color = {
            "S 核心 50": "#F15A9B",
            "A 重点 150": "#D97AB3",
            "B 扩展 800": "#9FB5D1",
        }

        for j, (_, r) in enumerate(pw.iterrows()):
            s = str(r.get("缺陷/应力来源", ""))
            m = str(r.get("作用机制", ""))
            o = str(r.get("宏观结果", ""))

            ps = structural_pos.get("S|" + s)
            pm = structural_pos.get("M|" + m)
            po = structural_pos.get("O|" + o)
            if not (ps and pm and po):
                continue

            # Paper position is close to the mean direction of its path.
            v = np.array(ps) + np.array(pm) + np.array(po)
            norm = float(np.linalg.norm(v))
            if norm < 1e-8:
                v = np.array([1.0, 0.0, 0.0])
                norm = 1.0
            v = v / norm

            yr = r.get("年份", y_max)
            try:
                yr_f = float(yr)
            except Exception:
                yr_f = y_max
            recent = (yr_f - y_min) / year_span
            radius = 4.15 + .82 * recent

            # deterministic jitter keeps papers from sitting on top of each other
            angle = j * 2.399963229728653
            jitter = np.array([
                .18 * math.cos(angle),
                .18 * math.sin(angle),
                .12 * math.sin(angle * .7),
            ])
            pp = v * radius + jitter
            paper_coords.append(pp)

            title = str(r.get("题名", "")).strip()
            journal = str(r.get("期刊", "")).strip()
            doi = str(r.get("DOI", "")).strip()
            tier = str(r.get("V5推荐等级", "")).strip()
            score = r.get("V5科研优先分", r.get("综合重要度", ""))

            paper_hover.append(
                f"<b>{title[:120]}</b>"
                f"<br>{journal} · {r.get('年份','')}"
                f"<br>等级：{tier or '未分级'}"
                f"<br>DOI：{doi or '无'}"
                f"<br><br>{s} → {m} → {o}"
            )
            paper_colors.append(tier_color.get(tier, "#B8C5D3"))

            try:
                score_f = float(score)
            except Exception:
                score_f = 0.0
            paper_sizes.append(3.0 + min(4.5, max(0.0, score_f) / 24.0))

            # Only label the first few highest-ranked papers.
            paper_labels.append(
                f"P{j+1}" if j < 8 else ""
            )

            edge_specs = [
                ("S", ps, "文献 → 缺陷/应力来源", s),
                ("M", pm, "文献 → 局部作用机制", m),
                ("O", po, "文献 → 宏观结果", o),
            ]
            for key, target, relation_label, target_name in edge_specs:
                pts = _curve_points(pp, target, lift=.18, inward=.72, n=12)
                edge_xyz[key]["x"].extend(pts[:, 0].tolist() + [None])
                edge_xyz[key]["y"].extend(pts[:, 1].tolist() + [None])
                edge_xyz[key]["z"].extend(pts[:, 2].tolist() + [None])
                mid = pts[len(pts)//2]
                edge_xyz[key]["hx"].append(float(mid[0]))
                edge_xyz[key]["hy"].append(float(mid[1]))
                edge_xyz[key]["hz"].append(float(mid[2]))
                edge_xyz[key]["hover"].append(
                    f"<b>{relation_label}</b>"
                    f"<br>{title[:105]}"
                    f"<br>连接到：<b>{target_name}</b>"
                    f"<br>DOI：{doi or '无'}"
                    f"<br><span style='color:#9EB2C5'>该细线表示论文的分类/证据归属，不表示论文证明了因果关系。</span>"
                )
                paper_edge_count += 1

        # Hundreds of literature edges are merged into 3 line traces for performance.
        line_specs = [
            ("S", "rgba(226,138,53,.17)", "论文 → 缺陷/应力来源", (226,138,53)),
            ("M", "rgba(119,115,216,.17)", "论文 → 局部作用机制", (119,115,216)),
            ("O", "rgba(33,173,177,.17)", "论文 → 宏观结果", (33,173,177)),
        ]
        for key, color, legend_name, rgb in line_specs:
            fig.add_trace(
                go.Scatter3d(
                    x=edge_xyz[key]["x"], y=edge_xyz[key]["y"], z=edge_xyz[key]["z"],
                    mode="lines", line=dict(color=color, width=1.0),
                    hoverinfo="skip", showlegend=True, name=legend_name,
                )
            )
            fig.add_trace(
                go.Scatter3d(
                    x=edge_xyz[key]["hx"], y=edge_xyz[key]["hy"], z=edge_xyz[key]["hz"],
                    mode="markers",
                    marker=dict(
                        size=5.5,
                        color=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.02)",
                        line=dict(width=0),
                    ),
                    hovertext=edge_xyz[key]["hover"], hoverinfo="text", showlegend=False,
                )
            )

        if paper_coords:
            arr = np.vstack(paper_coords)
            fig.add_trace(
                go.Scatter3d(
                    x=arr[:, 0], y=arr[:, 1], z=arr[:, 2],
                    mode="markers+text",
                    text=paper_labels,
                    textposition="top center",
                    textfont=dict(color="rgba(244,218,235,.75)", size=8),
                    marker=dict(
                        size=paper_sizes,
                        color=paper_colors,
                        opacity=.86,
                        line=dict(color="rgba(255,255,255,.34)", width=.35),
                    ),
                    hovertext=paper_hover,
                    hoverinfo="text",
                    name="文献证据节点",
                )
            )

    structural_links = len(sm) + len(mo) + len(sc)
    total_links = structural_links + paper_edge_count

    cameras = {
        "透视": dict(eye=dict(x=1.55, y=1.62, z=1.26), center=dict(x=0, y=0, z=0)),
        "俯视": dict(eye=dict(x=.04, y=.06, z=2.78), center=dict(x=0, y=0, z=0)),
        "侧视": dict(eye=dict(x=2.72, y=.10, z=.34), center=dict(x=0, y=0, z=0)),
    }

    fig.update_layout(
        paper_bgcolor="#06101D",
        plot_bgcolor="#06101D",
        margin=dict(l=0, r=0, t=64, b=0),
        scene=dict(
            bgcolor="#06101D",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="cube",
            camera=cameras.get(camera_name, cameras["透视"]),
            dragmode="orbit",
        ),
        legend=dict(
            orientation="h",
            y=1.035, x=.02,
            bgcolor="rgba(4,12,22,.48)",
            bordercolor="rgba(171,198,222,.12)",
            borderwidth=1,
            font=dict(color="#C9D9E8", size=10),
        ),
        font=dict(family='Inter,"Microsoft YaHei"', color="#DDE7F4"),
        annotations=[
            dict(
                x=.015, y=.982, xref="paper", yref="paper",
                showarrow=False, align="left",
                text=(
                    "<b>KDP 3D EVIDENCE NETWORK</b>"
                    f"<br><span style='font-size:10px;color:#88A4BA'>"
                    f"{'FOCUS · ' + str(focus_node) if focus_node else 'GLOBAL EVIDENCE VIEW'}</span>"
                ),
                font=dict(color="#E0ECF7", size=12),
                bgcolor="rgba(8,20,35,.62)",
                bordercolor="rgba(122,159,194,.16)",
                borderpad=8,
            ),
            dict(
                x=.985, y=.982, xref="paper", yref="paper",
                showarrow=False, align="right",
                text=(
                    f"<b>{1+len(sc)+len(mc)+len(oc)+len(pw)}</b> NODES"
                    f" · <b>{total_links}</b> LINKS"
                    f" · <b>{len(pw)}</b> PAPERS"
                ),
                font=dict(color="#94ADC2", size=10),
                bgcolor="rgba(8,20,35,.42)",
                borderpad=6,
            ),
        ],
    )

    return fig, pw, total_links, structural_links


def knowledge_graph():
    df = _df()
    page_header(
        "知识图谱",
        "把KDP文献中的缺陷来源、局部机制、宏观后果与具体论文组织为可回查的证据网络。",
        "KNOWLEDGE GRAPH",
    )
    project_context_strip()

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1.05, 1.1])
        scope = c1.radio("范围", ["KDP主线", "S+A", "全库"], horizontal=True)
        hide_uncertain = c2.toggle("仅显示明确证据关系", value=True)
        core_raw_only = c3.toggle("统计仅看开裂 / 缺陷核心", value=True)

    if scope == "全库":
        work = df
    elif scope == "KDP主线":
        work = material_scope(df, "KDP主线")
    else:
        work = material_scope(df, "KDP主线")
        work = work[work["V5推荐等级"].isin(["S 核心 50", "A 重点 150"])]

    original_n = len(work)

    if hide_uncertain:
        work = work[
            ~work["缺陷/应力来源"].isin(KG_UNCERTAIN)
            & ~work["作用机制"].isin(KG_UNCERTAIN)
            & ~work["宏观结果"].isin(KG_UNCERTAIN)
        ]

    chain = (
        work.groupby(
            ["缺陷/应力来源", "作用机制", "宏观结果"],
            as_index=False,
            observed=True,
        )
        .size()
        .rename(columns={"size": "文献数"})
    )

    if chain.empty:
        st.warning("当前筛选条件下没有可用于构建知识图谱的明确关系。")
        return

    metric_cards(
        [
            {"label": "当前文献范围", "value": f"{original_n:,}", "note": scope, "accent": COLORS["primary"]},
            {"label": "有效关系文献", "value": f"{int(chain['文献数'].sum()):,}", "note": "进入主图的关系", "accent": COLORS["cyan"]},
            {"label": "来源节点", "value": chain["缺陷/应力来源"].nunique(), "note": "缺陷 / 应力来源", "accent": COLORS["orange"]},
            {"label": "机制节点", "value": chain["作用机制"].nunique(), "note": "局部机制", "accent": COLORS["violet"]},
            {"label": "结果节点", "value": chain["宏观结果"].nunique(), "note": "宏观后果", "accent": COLORS["teal"]},
        ]
    )

    # IMPORTANT:
    # st.tabs executes every tab body on every rerun. The 3D graph therefore
    # used to render even when invisible, causing expensive WebGL work and
    # making page/module switching appear frozen.
    section = st.segmented_control(
        "图谱视图",
        ["研究主线", "3D证据图谱", "分类与关系"],
        default="研究主线",
        selection_mode="single",
        label_visibility="collapsed",
        key="kg_view_mode",
    )

    if section == "研究主线":
        c1, c2 = st.columns([1, 1.25])
        with c1:
            top_n = st.slider(
                "关系矩阵保留的最强关系",
                10,
                min(40, len(chain)),
                min(26, len(chain)),
                key="kg_matrix_topn",
            )
        with c2:
            soft_note(
                "左侧观察缺陷/应力来源如何进入局部机制，右侧观察机制如何对应宏观后果；"
                "颜色和数字表示当前文献库中的关系证据规模。"
            )

        fig = _relationship_matrix(chain, top_n=top_n)
        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            height=610,
            config={"displaylogo": False},
            key="kg_relationship_matrix",
        )

        section_title(
            "高证据研究路径",
            "按当前文献库中的关系数量排序，作为进一步回查原文和机制分析的入口",
        )
        strongest = chain.sort_values("文献数", ascending=False).head(12)
        mini_cards(
            [
                (
                    f"{r['缺陷/应力来源']}  →  {r['作用机制']}  →  {r['宏观结果']}",
                    f"当前关系文献：{int(r['文献数'])} 篇",
                )
                for _, r in strongest.iterrows()
            ]
        )
        return

    if section == "3D证据图谱":
        section_title(
            "KDP三维证据网络",
            "结构节点展示“缺陷/应力来源 → 局部机制 → 宏观结果”；外层文献节点对应真实论文，并分别连接到其分类路径。",
        )

        mode_col, rel_col, paper_col, focus_col, view_col = st.columns([1.05, .9, 1.05, 1.05, .85])

        density_mode = mode_col.selectbox(
            "图谱密度",
            ["文献证据网", "机制骨架", "全景证据云"],
            index=0,
            key="kg_dense_mode",
        )

        relation_limit = rel_col.slider(
            "结构关系",
            16,
            min(70, len(chain)),
            min(40, len(chain)),
            key="kg_dense_relation_limit",
        )

        explicit_papers = work.copy()
        if "题名" in explicit_papers.columns:
            explicit_papers = explicit_papers[
                explicit_papers["题名"].fillna("").astype(str).str.len() > 4
            ]

        if density_mode == "机制骨架":
            paper_limit = 0
            paper_col.caption("文献节点：关闭")
        else:
            max_papers = min(400, max(40, len(explicit_papers)))
            default_papers = min(180 if density_mode == "文献证据网" else 300, max_papers)
            min_papers = 40 if max_papers >= 40 else 1
            paper_limit = paper_col.slider(
                "文献节点",
                min_papers,
                max_papers,
                default_papers,
                step=20 if max_papers >= 80 else 5,
                key="kg_dense_paper_limit",
            )

        focus_layer = focus_col.selectbox(
            "聚焦层",
            ["全局", "缺陷/应力来源", "作用机制", "宏观结果"],
            key="kg_dense_focus_layer",
        )

        camera_name = view_col.selectbox(
            "视角",
            ["透视", "俯视", "侧视"],
            key="kg_dense_camera",
        )

        focus_node = None
        if focus_layer != "全局":
            if focus_layer == "缺陷/应力来源":
                counts = chain.groupby("缺陷/应力来源")["文献数"].sum().sort_values(ascending=False)
            elif focus_layer == "作用机制":
                counts = chain.groupby("作用机制")["文献数"].sum().sort_values(ascending=False)
            else:
                counts = chain.groupby("宏观结果")["文献数"].sum().sort_values(ascending=False)

            focus_node = st.selectbox(
                "聚焦节点",
                list(counts.index),
                key="kg_dense_focus_node",
            )

        st.markdown("#### 线条与节点到底代表什么？")
        semantics = pd.DataFrame(
            [
                ["橙色大节点", "缺陷 / 应力来源", "例如杂质、加工缺陷、生长缺陷等"],
                ["紫色大节点", "局部作用机制", "例如电子结构/缺陷态、局域应力、氢键结构等"],
                ["青绿色大节点", "宏观结果", "例如开裂、吸收、LIDT、散射等"],
                ["粉色/淡色小节点", "具体论文", "悬停显示题名、期刊、年份、DOI和研究路径"],
                ["紫色较粗曲线", "缺陷/应力来源 → 局部机制", "聚合关系；越粗/越亮表示当前数据库关联文献越多"],
                ["青绿色较粗曲线", "局部机制 → 宏观结果", "聚合关系；越粗/越亮表示当前数据库关联文献越多"],
                ["橙色细线", "论文 → 缺陷/应力来源", "表示这篇论文被归入该来源类别"],
                ["紫色细线", "论文 → 局部作用机制", "表示这篇论文涉及/支持该机制分类"],
                ["青绿色细线", "论文 → 宏观结果", "表示这篇论文涉及该宏观结果分类"],
            ],
            columns=["图形编码", "关系含义", "解释"],
        )
        st.dataframe(semantics, width="stretch", hide_index=True, height=360)
        st.warning(
            "科学边界：图中的连接首先表示‘文献分类、共现或证据归属’，不自动等同于因果关系。"
            "若要把某条路径写成确定机理或因果链，仍需回查代表论文原文及实验/计算证据。"
        )

        with st.expander("性能说明", expanded=False):
            st.markdown(
                """
高密度模式可绘制数百篇论文和数百至上千条关系线。为了避免浏览器卡死，
同一类型的细线会合并为少量 WebGL trace；每条细线在中点设置隐藏 hover 锚点，
鼠标靠近该线中段时可查看“哪篇论文连接到哪个分类节点”。
"""
            )

        if not st.session_state.get("_kg_dense_enabled", False):
            st.info(
                "高密度3D图谱采用按需加载。进入后可在本次会话内调整文献数量、聚焦节点和视角。"
            )
            if not st.button("进入三维证据网络", type="primary", key="kg_dense_enable"):
                return
            st.session_state["_kg_dense_enabled"] = True

        try:
            with st.spinner("正在把结构关系与真实文献节点装配为三维证据网络…"):
                fig, shown_papers, total_links, structural_links = _dense_evidence_globe(
                    explicit_papers,
                    chain,
                    relation_limit=relation_limit,
                    paper_limit=paper_limit,
                    focus_layer=focus_layer,
                    focus_node=focus_node,
                    camera_name=camera_name,
                    show_papers=density_mode != "机制骨架",
                )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("Dense 3D evidence graph failed", exc_info=exc)
            st.warning("高密度证据网络未通过当前浏览器兼容检查，已切换到轻量机制图谱。")
            fig = _orbital_graph_lite(
                chain,
                top_n=min(relation_limit, 30),
                camera_name=camera_name,
            )
            shown_papers = pd.DataFrame()
            total_links = 0
            structural_links = 0

        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            height=860,
            config={
                "displaylogo": False,
                "scrollZoom": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "KDP_三维文献证据网络",
                    "scale": 2,
                },
            },
            key=f"kg_dense_{density_mode}_{relation_limit}_{paper_limit}_{focus_layer}_{focus_node}_{camera_name}",
        )

        # Quantitative summary.
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("结构节点", 1 + chain["缺陷/应力来源"].nunique() + chain["作用机制"].nunique() + chain["宏观结果"].nunique())
        m2.metric("当前文献节点", len(shown_papers))
        m3.metric("当前关系线", total_links)
        m4.metric("其中结构关系", structural_links)

        section_title(
            "当前图谱中的文献证据",
            "这里列出当前被绘制为文献节点的真实论文，并给出每篇论文对应的‘来源 → 机制 → 结果’分类路径。",
        )

        if len(shown_papers):
            table = shown_papers.copy()
            table["研究路径"] = (
                table["缺陷/应力来源"].astype(str)
                + " → "
                + table["作用机制"].astype(str)
                + " → "
                + table["宏观结果"].astype(str)
            )
            cols = [
                c for c in
                ["题名", "年份", "期刊", "DOI", "V5推荐等级", "研究路径"]
                if c in table.columns
            ]
            st.dataframe(
                table[cols].head(80),
                width="stretch",
                hide_index=True,
                height=540,
            )

            if len(shown_papers) > 80:
                st.caption(f"3D图当前包含 {len(shown_papers)} 篇文献；表格先显示排名前80篇。")
        else:
            soft_note("当前为机制骨架模式，未加载文献节点。切换到“文献证据网”或“全景证据云”可查看真实论文节点。")

        return

    # 分类与关系
    left, right = st.columns([1.08, 1], gap="large")
    with left:
        section_title("核心详细分类", "聚焦KDP缺陷、开裂及其相关方法的二级分类结构")
        raw = work["详细二级分类"].fillna("").replace("", "未命中详细分类")
        raw_counts = raw.value_counts().rename_axis("原始详细分类").reset_index(name="文献数")

        if core_raw_only:
            pattern = "|".join(re.escape(k) for k in KG_CORE_RAW_KEYWORDS)
            raw_counts = raw_counts[
                raw_counts["原始详细分类"].str.contains(
                    pattern,
                    case=False,
                    regex=True,
                )
            ]

        raw_counts = raw_counts.head(28)

        if len(raw_counts):
            bar_df = raw_counts.sort_values("文献数")
            fig = px.bar(
                bar_df,
                x="文献数",
                y="原始详细分类",
                orientation="h",
                color="文献数",
                color_continuous_scale=["#DDE5F0", "#8B84E8", "#20AFC0"],
            )
            fig.update_layout(
                coloraxis_showscale=False,
                yaxis_title="",
                xaxis_title="文献数",
            )
            fig.update_traces(marker_line_width=0)
            plotly(fig, height=700, key="kg_categories")
        else:
            st.info("当前条件下没有命中的核心详细分类。")

    with right:
        section_title("关系强度", "优先回查关系证据较厚的研究链")
        rel = chain.copy()
        rel["研究链路"] = (
            rel["缺陷/应力来源"]
            + " → "
            + rel["作用机制"]
            + " → "
            + rel["宏观结果"]
        )
        rel = rel.sort_values("文献数", ascending=False).head(30)
        st.dataframe(
            rel[["研究链路", "文献数"]],
            width="stretch",
            height=700,
            hide_index=True,
        )

def topic_review():
    df = _df()
    page_header(
        "专题调研",
        "围绕一个问题自动组织代表文献、证据规模、研究共识、争议与下一步方向。",
        "TOPIC RESEARCH",
    )

    project_context_strip()

    with st.container(border=True):
        c1, c2 = st.columns([1.25, 1])
        topic = c1.selectbox("研究专题", list(CORE_TOPICS))
        n = c2.slider("代表文献数", 8, 40, 20)

    papers = topic_search(df, topic, n, "KDP主线")

    metric_cards(
        [
            {"label": "代表文献", "value": len(papers), "note": "本次用于调研", "accent": COLORS["primary"]},
            {"label": "S / A", "value": int(papers["V5推荐等级"].isin(["S 核心 50", "A 重点 150"]).sum()), "note": "高优先级证据", "accent": COLORS["violet"]},
            {"label": "DFT / 理论", "value": int(papers["_方法标签"].str.contains("DFT|有限元|分子动力学", regex=True).sum()), "note": "理论计算相关", "accent": COLORS["cyan"]},
        ]
    )

    section_title("代表证据", "先看证据，再让 AI 做综合")
    evidence_table(papers, height=430)

    with st.expander("离线证据概览", expanded=False):
        st.markdown(offline_summary(papers, topic))

    if st.button("生成完整专题调研", type="primary"):
        ok, _ = api_status()
        if not ok:
            st.warning("当前未连接 DeepSeek。")
            return

        status = st.status("正在生成专题调研…", expanded=True)
        status.write("已完成代表文献检索")
        status.write(f"已选取 {len(papers)} 篇证据")
        try:
            answer, sources = run_agent(
                f"围绕“{topic}”生成系统专题调研。",
                papers,
                "专题调研",
            )
            status.update(label="专题调研生成完成", state="complete", expanded=False)
        except Exception as exc:
            status.update(label="AI 调用失败", state="error")
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)
            return

        with st.container(border=True):
            st.markdown(answer)
        sources_block(sources)
        render_deepseek_usage()
        st.download_button(
            "导出 Word",
            docx_bytes(topic + "专题调研", answer, sources),
            topic + "_专题调研.docx",
        )
        if st.button("保存专题调研到当前研究项目"):
            add_item(
                "ai_note",
                "专题调研：" + topic,
                answer[:1600],
                {"topic": topic, "full_answer": answer},
                "专题调研",
                "待核验",
            )
            st.success("已保存到当前项目记忆。")


def compare():
    df = _df()
    page_header(
        "多文献比较",
        "把多篇论文放在同一证据坐标系里比较对象、方法、结论、差异与可复现价值。",
        "PAPER COMPARISON",
    )

    project_context_strip()

    with st.container(border=True):
        q = st.text_input("检索候选论文", placeholder="输入关键词后缩小候选集")
        cand = search_papers(df, q, 60, "KDP主线") if q else search_papers(df, "", 60, "S+A")
        mapping = {f"{r['题名']}｜{r['年份']}": i for i, r in cand.iterrows()}
        selected = st.multiselect("选择 2–6 篇", list(mapping), max_selections=6)

    if len(selected) < 2:
        soft_note("至少选择 2 篇论文；建议比较同一缺陷、同一方法或同一结果方向的代表工作。")
        return

    chosen = df.loc[[mapping[x] for x in selected]]
    section_title("已选论文", "先看客观字段，再进行 AI 深度比较")
    st.dataframe(
        chosen[
            ["题名", "年份", "详细二级分类", "_方法标签", "自动研究问题", "自动主要结论", "DOI"]
        ],
        width="stretch",
        height=380,
        hide_index=True,
    )

    if st.button("执行深度比较", type="primary"):
        ok, _ = api_status()
        if not ok:
            st.warning("当前未连接 DeepSeek。")
            return
        try:
            with st.status("正在比较研究对象、方法与结论…", expanded=False):
                answer, sources = run_agent(
                    "比较这些论文的研究对象、方法、结论、差异和借鉴价值。",
                    chosen,
                    "多文献比较",
                )
            with st.container(border=True):
                st.markdown(answer)
            sources_block(sources)
            render_deepseek_usage()
            if st.button("保存多文献比较到当前研究项目"):
                add_item(
                    "ai_note",
                    "多文献比较：" + " / ".join([str(x)[:35] for x in selected[:3]]),
                    answer[:1600],
                    {"selected": selected, "full_answer": answer},
                    "多文献比较",
                    "待核验",
                )
                st.success("已保存到当前项目记忆。")
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def crack_diagnosis():
    df = _df()
    page_header(
        "开裂诊断",
        "先做透明的工艺先验排序，再用KDP文献证据约束判断；输出可证伪的最小验证实验，而不是让AI直接猜原因。",
        "CRACK DIAGNOSTICS",
    )

    project_context_strip()

    phenomenon = st.text_area(
        "开裂 / 缺陷现象",
        height=110,
        placeholder="例如：取晶后约30 min出现纵向裂纹，裂纹从籽晶附近开始扩展；请尽量写时间、位置、方向和发生阶段。",
    )

    options = [
        "未知", "明显异常", "偏高/偏快/强约束", "可疑",
        "一般/不确定", "较好/稳定", "偏低/偏慢/低约束",
    ]

    states = {}
    with st.container(border=True):
        section_title("实验变量快照", "未知项可以保留；系统会把“未知”视为待核，不会自动判为高风险")
        cols = st.columns(2)
        for i, variable in enumerate(VARIABLES):
            states[variable] = cols[i % 2].selectbox(
                variable,
                options,
                key="diag_" + variable,
            )

    if not st.button("执行根因诊断", type="primary"):
        soft_note("诊断结果是“风险排序 + 文献支持 + 可证伪实验”，不能替代真实实验因果证明。")
        return

    result = diagnose(states)

    # ----------------------------------------------------------
    # 已解锁的真实历史实验：只在本地页面用于统计，不自动发送给外部AI
    # ----------------------------------------------------------
    historical_rows = []
    if vault_unlocked():
        vrecords = vault_list_records()
        for rec in vrecords:
            p = rec.get("payload", {}) or {}
            historical_rows.append(
                {
                    "实验ID": rec.get("experiment_id", ""),
                    "开裂": p.get("cracked", ""),
                    "过饱和度": p.get("supersaturation_pct"),
                    "降温速率": p.get("cooling_rate"),
                    "生长时间": p.get("growth_hours"),
                    "pH": p.get("ph"),
                    "固定方式": p.get("fixation", ""),
                    "籽晶取向": p.get("seed_orientation", ""),
                    "籽晶质量": p.get("seed_quality", ""),
                }
            )

    historical = pd.DataFrame(historical_rows)

    if len(historical):
        labelled = historical[historical["开裂"].isin(["是", "否"])].copy()
        st.info(
            f"已安全调用当前项目 {len(historical)} 条受保护历史实验用于页面内统计；"
            f"其中 {len(labelled)} 条有明确开裂标签。具体实验参数不会自动发送给DeepSeek。"
        )

        assoc = []
        for col, label in [
            ("过饱和度", "过饱和度"),
            ("降温速率", "降温速率"),
            ("生长时间", "生长时间"),
            ("pH", "pH"),
        ]:
            if col not in labelled.columns:
                continue
            x = pd.to_numeric(labelled[col], errors="coerce")
            a = x[labelled["开裂"] == "是"].dropna()
            b = x[labelled["开裂"] == "否"].dropna()
            if len(a) and len(b):
                assoc.append(
                    {
                        "历史变量": label,
                        "开裂组中位数": round(float(a.median()), 4),
                        "未开裂组中位数": round(float(b.median()), 4),
                        "样本数": f"{len(a)} / {len(b)}",
                        "解释": "仅为历史关联，不代表因果",
                    }
                )
        if assoc:
            with st.expander("历史实验关联信号", expanded=False):
                st.dataframe(pd.DataFrame(assoc), width="stretch", hide_index=True)

    # 为风险最高的变量绑定独立本地文献证据。
    support_rows = []
    top_variables = result[result["风险分"] > 0].head(5)

    for _, row in top_variables.iterrows():
        q = (
            f"{phenomenon} {row['变量']} {row['检索关键词']} "
            "mechanism evidence"
        )
        papers = search_papers(df, q, 12, "KDP主线")

        if "证据使用等级" in papers.columns:
            strong = int(
                papers["证据使用等级"]
                .isin(["A 可用于重点论证", "B 可用于辅助论证"])
                .sum()
            )
        else:
            strong = 0

        direct = int(
            papers.get(
                "证据角色",
                pd.Series("", index=papers.index),
            )
            .isin(["直接核心证据", "基础支撑证据"])
            .sum()
        )

        if strong >= 4:
            evidence_strength = "较强"
        elif strong >= 2:
            evidence_strength = "中等"
        elif len(papers) > 0:
            evidence_strength = "有限"
        else:
            evidence_strength = "当前未检出"

        support_rows.append(
            {
                "变量": row["变量"],
                "工艺先验风险": row["风险"],
                "检索到文献": len(papers),
                "A/B级证据": strong,
                "直接/支撑证据": direct,
                "文献支持": evidence_strength,
                "否证判据": row["否证判据"],
            }
        )

    support = pd.DataFrame(support_rows)

    metric_cards(
        [
            {
                "label": "高风险变量",
                "value": int((result["风险"] == "高").sum()),
                "note": "仅代表工艺先验",
                "accent": COLORS["red"],
            },
            {
                "label": "已绑定证据变量",
                "value": len(support),
                "note": "优先级最高的变量",
                "accent": COLORS["primary"],
            },
            {
                "label": "较强文献支持",
                "value": int((support["文献支持"] == "较强").sum()) if len(support) else 0,
                "note": "A/B级证据≥4",
                "accent": COLORS["teal"],
            },
            {
                "label": "诊断原则",
                "value": "可证伪",
                "note": "每个主因必须能被实验否证",
                "accent": COLORS["orange"],
            },
        ]
    )

    risk_map = {"高": 3, "中": 2, "低": 1, "待核": 0}
    plot_df = result.copy()
    plot_df["_风险值"] = plot_df["风险"].map(risk_map)

    left, right = st.columns([.95, 1.35], gap="large")

    with left:
        section_title("工艺先验风险排序", "这是排查优先级，不是“已经证明的原因”")
        fig = px.bar(
            plot_df.sort_values("_风险值"),
            x="_风险值",
            y="变量",
            orientation="h",
            color="_风险值",
            color_continuous_scale=["#D9E2EA", "#E7B35C", "#C95C5C"],
        )
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(
                tickvals=[0, 1, 2, 3],
                ticktext=["待核", "低", "中", "高"],
            ),
            xaxis_title="",
            yaxis_title="",
        )
        plotly(fig, height=520, key="diagnosis_risk")

    with right:
        section_title("诊断明细", "每个判断都给出机制、最小实验、支持判据和否证判据")
        cols = [
            "变量", "当前状态", "风险", "可能机理",
            "最小对照实验", "关键指标", "否证判据",
        ]
        st.dataframe(
            result[cols],
            width="stretch",
            height=520,
            hide_index=True,
        )

    section_title(
        "风险判断与文献证据绑定",
        "把“规则认为可疑”和“文献是否支持”分开显示，避免把经验规则包装成事实",
    )

    if len(support):
        st.dataframe(
            support,
            width="stretch",
            hide_index=True,
            height=min(380, 68 + 42 * len(support)),
        )
    else:
        soft_note("当前变量均为未知/待核。建议先补充实验条件，再做风险排序。")

    evidence = search_papers(
        df,
        (
            phenomenon
            + " KDP crack thermal stress inclusion dislocation "
              "supersaturation seed defect cooling"
        ),
        18,
        "KDP主线",
    )

    section_title(
        "关联文献证据",
        "优先显示证据完整度较高的KDP直接/支撑文献；低完整度文献只能作为线索",
    )

    evidence_cols = [
        "题名", "年份", "期刊", "证据使用等级", "证据完整度分",
        "证据角色", "缺陷/应力来源", "作用机制", "宏观结果", "DOI",
    ]
    evidence_cols = [c for c in evidence_cols if c in evidence.columns]
    st.dataframe(
        evidence[evidence_cols],
        width="stretch",
        hide_index=True,
        height=430,
    )

    ok, _ = api_status()
    if ok:
        extra_lines = [
            "重要：下面风险来自工艺先验，不能直接写成因果结论。",
        ]

        for _, x in result.head(5).iterrows():
            extra_lines.append(
                f"{x['变量']}={x['当前状态']}，先验风险={x['风险']}，"
                f"否证判据={x['否证判据']}"
            )

        if len(support):
            extra_lines.append("文献绑定：" + support.to_string(index=False))

        try:
            with st.status(
                "DeepSeek 正在综合工艺先验、证据等级和可证伪实验…",
                expanded=False,
            ):
                answer, sources = run_agent(
                    phenomenon or "诊断 KDP 晶体开裂原因",
                    evidence,
                    "实验诊断",
                    "\n".join(extra_lines),
                )

            with st.container(border=True):
                st.markdown(answer)

            sources_block(sources)
            render_deepseek_usage()

        except Exception as exc:
            safe_error(
                "模型分析暂时不可用，详细错误已记录。请稍后重试。",
                exc,
            )

    if st.button("保存本次诊断到当前研究项目"):
        add_item(
            "diagnosis",
            (phenomenon[:70] if phenomenon else "KDP开裂诊断") + ("…" if len(phenomenon) > 70 else ""),
            "；".join(
                f"{r['变量']}={r['风险']}"
                for _, r in result.head(5).iterrows()
            ),
            {
                "phenomenon": phenomenon,
                "risk_table": result.to_dict("records"),
                "evidence_support": support.to_dict("records") if len(support) else [],
            },
            "开裂诊断",
            "待实验验证",
        )
        st.success("已保存。对照实验设计、AI科研助手和研究项目工作区都可以读取这次诊断。")

def experiment_design():
    page_header(
        "对照实验设计",
        "把复杂开裂问题拆成可证伪的单变量实验：基线、实验组、关键指标、支持判据、否证判据和记录要求一次给全。",
        "EXPERIMENT DESIGN",
    )

    project_context_strip()

    with st.container(border=True):
        selected = st.multiselect(
            "准备验证的变量",
            list(VARIABLES),
            default=["降温速率", "籽晶固定方式", "过饱和度"],
        )

        baseline_default = ""
        if vault_unlocked():
            history = vault_list_records()
            if history:
                p = (history[0].get("payload", {}) or {})
                baseline_default = (
                    f"参考实验 {history[0].get('experiment_id','')}；"
                    f"过饱和度={p.get('supersaturation_pct','')}；"
                    f"生长温度={p.get('growth_temp_start','')}→{p.get('growth_temp_end','')}℃；"
                    f"降温速率={p.get('cooling_rate','')}℃/h；"
                    f"籽晶取向={p.get('seed_orientation','')}；"
                    f"固定方式={p.get('fixation','')}。"
                )
                st.caption("已从最近一条受保护实验记录生成基线草案；这里只用于当前页面，不自动发送给外部AI。")

        baseline = st.text_area(
            "当前标准流程 / 基线",
            value=baseline_default,
            placeholder="填写当前生长、取晶和冷却流程；越具体，后续越容易真正做到单变量。",
        )

    if not selected:
        soft_note("至少选择一个变量后生成实验矩阵。")
        return

    matrix = experiment_matrix(selected, baseline)

    metric_cards(
        [
            {
                "label": "变量数",
                "value": len(selected),
                "note": "每次只改一个主变量",
                "accent": COLORS["primary"],
            },
            {
                "label": "探索重复",
                "value": "≥ 3",
                "note": "正式统计按方差/效应量追加",
                "accent": COLORS["orange"],
            },
            {
                "label": "核心原则",
                "value": "可证伪",
                "note": "同时保留支持与否证条件",
                "accent": COLORS["teal"],
            },
            {
                "label": "记录方式",
                "value": "时序化",
                "note": "条件—现象—表征可追溯",
                "accent": COLORS["cyan"],
            },
        ]
    )

    section_title(
        "实验矩阵",
        "可以直接作为组会讨论和下一轮实验计划草案；“≥3”只是探索起点，不等于统计学充分",
    )

    st.dataframe(
        matrix,
        width="stretch",
        height=540,
        hide_index=True,
    )

    st.download_button(
        "导出实验矩阵 Excel",
        excel_bytes(matrix, "对照实验"),
        "KDP_对照实验设计.xlsx",
    )

    soft_note(
        "正式得出因果结论前，应结合样本波动、效应量和重复性决定是否增加样本；"
        "系统不把“每组3个”包装成通用统计学标准。"
    )

    if st.button("保存实验方案到当前研究项目"):
        add_item(
            "experiment_plan",
            "对照实验方案：" + " / ".join(selected),
            baseline or "基于当前标准流程的单变量对照方案",
            {"variables": selected, "baseline": baseline, "matrix": matrix.to_dict("records")},
            "对照实验设计",
            "待执行",
        )
        st.success("已保存。执行后可到“实验研究库”记录真实结果。")

def theory():
    df = _df()
    page_header(
        "理论计算规划与分析",
        "面向KDP缺陷、电子结构与开裂机制研究，组织模型构建、参数选择、收敛验证、计算任务、结果解析及文献/实验对照；数值求解由QE、VASP、LAMMPS、COMSOL等专业软件完成。",
        "COMPUTATIONAL PLANNING & ANALYSIS",
    )
    project_context_strip()

    section_title(
        "计算研究流程",
        "将科学问题、计算模型、方法依据、求解任务、收敛验证与结果回填纳入同一研究链",
    )
    insight_strip(
        [
            {
                "kicker": "BEFORE SOLVING",
                "title": "问题定义与模型设计",
                "note": "明确研究对象、计算方法、模型边界、参数依据、参考文献与验证方案",
                "accent": COLORS["primary"],
            },
            {
                "kicker": "SOLVING",
                "title": "专业求解器执行",
                "note": "QE/VASP/LAMMPS/COMSOL等在本机或服务器完成数值求解与迭代",
                "accent": COLORS["orange"],
            },
            {
                "kicker": "AFTER SOLVING",
                "title": "结果验证与研究回填",
                "note": "检查收敛与异常，提取关键结果，并与文献证据、实验现象和研究假设交叉验证",
                "accent": COLORS["teal"],
            },
        ]
    )

    section_title(
        "示例工作流｜KDP氢空位缺陷态",
        "从科学问题到缺陷模型、数值求解和结果验证的完整计算链",
    )
    st.markdown(
        """
**科学问题** → **KDP缺陷计算文献** → **完美晶体/缺陷模型** → **结构优化与收敛测试**
→ **SCF / DOS / PDOS** → **缺陷态识别** → **完美晶体—缺陷晶体比较**
→ **与实验光学/吸收结果对照**

数值计算由所选专业求解器执行；平台负责研究问题、方法依据、任务状态、验证结果与项目记忆的统一管理。
"""
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1.2])
        method = c1.selectbox("计算类型", ["DFT/第一性原理", "分子动力学 MD", "有限元 FEA"])
        target = c2.selectbox(
            "研究对象",
            [
                "氢空位", "钾空位", "氧/磷酸根缺陷", "杂质/掺杂", "缺陷复合体",
                "包裹体附近应力", "加工亚表面损伤", "裂纹萌生", "热应力场",
                "籽晶/固定约束", "同位素对照（扩展）",
            ],
        )
        software_map = {
            "DFT/第一性原理": ["Quantum ESPRESSO", "VASP", "Materials Studio (CASTEP)", "Gaussian（簇模型/局域模型）"],
            "分子动力学 MD": ["LAMMPS", "Materials Studio (Forcite)", "Python后处理"],
            "有限元 FEA": ["COMSOL", "ANSYS", "Python后处理"],
        }
        software = c3.selectbox("主要软件/求解器", software_map[method])
        active_project = get_active_project()
        goal = st.text_area(
            "研究目标",
            value="" if not active_project else active_project.get("question", ""),
            placeholder="例如：比较不同氢空位位置与电荷态对缺陷态和光学响应的影响。",
        )

    if "Gaussian" in software and method == "DFT/第一性原理":
        st.warning(
            "Gaussian更适合分子/簇模型；KDP周期性体相第一性原理通常优先考虑QE、VASP或CASTEP。"
            "如果使用簇模型，必须解释边界截断和环境嵌入如何处理。"
        )

    workflows = {
        "DFT/第一性原理": [
            ("1. 完美晶体基准", "CIF核对 → 晶格/原子位置 → 截断能与k点收敛 → 结构优化"),
            ("2. 缺陷模型", "建立超胞 → 枚举缺陷位置/电荷态 → 检查缺陷间相互作用 → 结构弛豫"),
            ("3. 能量与电子结构", "形成能/相对稳定性 → TDOS/PDOS → 电荷密度/局域态 → 必要时光学响应"),
            ("4. 数值可靠性", "超胞、截断能、k点、泛函/赝势、展宽等必须有收敛或敏感性说明"),
            ("5. 科学验证", "与核心KDP文献和实验现象对照；异常结果先排查模型和数值参数"),
        ],
        "分子动力学 MD": [
            ("1. 结构与势函数", "建立KDP原子模型 → 明确势函数来源与适用范围 → 完美晶体基准验证"),
            ("2. 工况与边界", "缺陷/热循环/加工载荷 → 系综、时间步长、边界条件 → 尺寸与时间尺度检查"),
            ("3. 演化量", "原子应力、位移、能量、缺陷演化、微裂纹或加工损伤指标"),
            ("4. 稳健性", "时间步长、体系尺寸、升降温速率和势函数敏感性"),
            ("5. 实验映射", "与显微形貌、裂纹位置、亚表面损伤或热学行为比较"),
        ],
        "有限元 FEA": [
            ("1. 材料参数", "各向异性弹性、热膨胀、导热、密度等参数必须可追溯"),
            ("2. 几何与边界", "真实晶体尺寸 → 籽晶/夹持 → 温度/浓度边界 → 接触与约束"),
            ("3. 网格与求解", "网格无关性 → 时间步/稳态选择 → 多物理场耦合假设"),
            ("4. 场与危险区", "主应力、应变能、温度梯度、局部应力集中与裂纹危险区域"),
            ("5. 空间验证", "与真实裂纹起点/方向、固定位置和实验温度过程做共定位验证"),
        ],
    }
    section_title("计算主流程", "每个环节明确模型依据、关键输入、收敛要求与验证方式")
    mini_cards(workflows[method])

    file_checklists = {
        "Quantum ESPRESSO": [
            ("结构优化", "relax.in / vc-relax.in：先确定是否真的需要变胞"),
            ("静态基态", "scf.in：在优化结构上得到自洽电荷密度"),
            ("电子结构", "nscf.in + dos.x / projwfc.x：DOS/PDOS；能带需单独高对称路径"),
            ("光学", "根据方法和QE模块选择介电/光学后处理；不能把默认设置直接当收敛结果"),
        ],
        "VASP": [
            ("结构文件", "POSCAR + POTCAR：元素顺序和赝势版本必须记录"),
            ("优化", "INCAR-relax + KPOINTS：先做截断能/k点收敛"),
            ("静态/DOS", "静态SCF → DOS/PDOS；缺陷体系注意电荷态与有限尺寸效应"),
            ("结果归档", "OUTCAR/OSZICAR/vasprun.xml及所用输入文件一起保存，保证可复现"),
        ],
        "Materials Studio (CASTEP)": [
            ("结构", "CIF/XSD核对H位置、空间群与周期边界"),
            ("Geometry Optimization", "先做cutoff和k-point convergence，再进行缺陷比较"),
            ("Properties", "Band/DOS/Optics按研究问题选择，不把软件默认参数当科学依据"),
            ("归档", "保存结构、Calculation设置截图/参数和输出文件"),
        ],
        "Gaussian（簇模型/局域模型）": [
            ("模型边界", "说明为何采用簇模型、边界原子如何饱和/嵌入"),
            ("基组/泛函", "必须有体系适用性与收敛/敏感性说明"),
            ("结果边界", "局域簇结果不能直接替代周期体相能带/缺陷形成能结论"),
        ],
        "LAMMPS": [
            ("结构与势", "data文件 + 势函数参数，先验证晶格/弹性/热学基准"),
            ("工况脚本", "平衡 → 加载/热循环/加工 → 输出轨迹与原子应力"),
            ("稳健性", "时间步长、体系尺寸、边界和势函数敏感性"),
        ],
        "Materials Studio (Forcite)": [
            ("力场", "首先确认力场对KDP/离子/氢键体系是否适用"),
            ("动力学", "系综、时间步长、升降温路径和约束需明确"),
            ("验证", "先验证基础结构/热学性质，再用于机制推断"),
        ],
        "Python后处理": [
            ("数据入口", "承担结果处理、统计与可视化，并与专业求解器输出衔接"),
            ("可复现", "脚本版本、输入文件和输出图表一起归档"),
        ],
        "COMSOL": [
            ("几何/材料", "真实尺寸 + 各向异性材料参数 + 参数来源"),
            ("物理场", "Heat Transfer + Solid Mechanics；按问题决定是否增加传质/接触"),
            ("边界条件", "温度过程、夹持、对流/接触必须来自真实实验或有依据的假设"),
            ("验证", "网格无关性 + 参数敏感性 + 裂纹起点空间共定位"),
        ],
        "ANSYS": [
            ("模型", "几何、材料坐标系、各向异性参数与约束"),
            ("求解", "热分析 → 结构耦合或直接耦合；记录网格与时间步"),
            ("验证", "应力热点与真实裂纹位置/方向比较"),
        ],
    }
    section_title("软件输入/归档清单", "网页帮你把任务拆清楚；实际文件仍在相应软件中建立和运行")
    mini_cards(file_checklists.get(software, []))

    evidence = search_papers(df, f"{method} {target} {goal}", 18, "KDP主线")
    section_title("KDP方法证据", "计算参数和建模假设优先从KDP直接工作中找依据")
    evidence_table(evidence, height=390)

    task_payload = {
        "method": method,
        "target": target,
        "software": software,
        "goal": goal,
        "workflow": workflows[method],
        "checklist": file_checklists.get(software, []),
    }

    task_card = [
        "# KDP理论计算任务卡",
        "",
        f"- 计算类型：{method}",
        f"- 研究对象：{target}",
        f"- 外部求解器：{software}",
        f"- 科学目标：{goal}",
        "",
        "## 主流程",
    ]
    task_card += [f"- **{a}**：{b}" for a, b in workflows[method]]
    task_card += ["", "## 输入/归档清单"]
    task_card += [f"- **{a}**：{b}" for a, b in file_checklists.get(software, [])]
    task_card += [
        "",
        "## 科学边界",
        "- 本任务卡不是可直接运行的输入文件。",
        "- 真正计算必须在对应求解器中完成。",
        "- 截断能、k点、超胞、势函数/赝势、材料参数等必须做体系相关验证，不能照抄默认值。",
    ]
    task_card_text = "\n".join(task_card)

    d1, d2, d3 = st.columns([1, 1, 1])
    d1.download_button(
        "下载计算任务卡.md",
        task_card_text.encode("utf-8"),
        file_name="KDP_理论计算任务卡.md",
        mime="text/markdown",
    )

    c1, c2 = st.columns(2)
    if c1.button("保存计算任务到当前研究项目"):
        add_item(
            "theory_task",
            f"{method}｜{target}",
            goal,
            task_payload,
            "理论计算工作流",
            "待计算",
        )
        st.success("计算任务已进入项目记忆；完成外部求解后可以回到这里记录结果。")

    if c2.button("生成AI完整计算方案", type="primary"):
        ok, _ = api_status()
        if not ok:
            st.warning("当前未连接 DeepSeek。")
        else:
            try:
                with st.status("正在结合KDP证据生成计算路线…", expanded=False):
                    answer, sources = run_agent(
                        f"{method}; {target}; 软件={software}; 目标={goal}",
                        evidence,
                        "理论方案",
                        "必须明确哪些步骤由外部求解器完成，并给出收敛、验证、失败排查和结果解释边界。",
                    )
                with st.container(border=True):
                    st.markdown(answer)
                sources_block(sources)
                render_deepseek_usage()
            except Exception as exc:
                safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)

    section_title("外部计算输出本地初检", "先在浏览器会话里做最基础的完成/报错检查；不会把这段输出自动发送给DeepSeek")
    output_text = st.text_area(
        "粘贴非机密输出片段（例如QE .out / VASP OUTCAR关键部分）",
        height=140,
        placeholder="公开网站不要粘贴机密计算参数或未公开数据。真实项目建议在本地私密版使用。",
        key="solver_output_quick_check",
    )
    if st.button("本地初检输出", key="solver_output_check_btn"):
        text = output_text or ""
        low = text.lower()
        rows = []

        if "Quantum ESPRESSO" in software:
            done = "job done" in low
            bad = (
                "convergence not achieved" in low
                or "error in routine" in low
                or "%%%%%%%%%%%%" in text
            )
            energies = re.findall(r"!\\s+total energy\\s+=\\s+([-+0-9.eEdD]+)\\s+Ry", text)
            rows.append(["作业是否正常结束", "是" if done else "未确认", "查找 JOB DONE"])
            rows.append(["明显报错/未收敛", "有" if bad else "未检出", "仍需人工核对完整输出"])
            rows.append(["提取到总能量", f"{len(energies)} 个" if energies else "0 个", energies[-1] + " Ry" if energies else "—"])

        elif "VASP" in software:
            done = "reached required accuracy" in low or "general timing and accounting" in low
            bad_words = ["brmix", "zbrent", "edddav", "error"]
            bad_hit = [x for x in bad_words if x in low]
            energies = re.findall(r"free\\s+energy\\s+TOTEN\\s+=\\s+([-+0-9.eE]+)\\s+eV", text)
            rows.append(["达到优化/结束标志", "是" if done else "未确认", "需结合任务类型判断"])
            rows.append(["常见错误关键词", ", ".join(bad_hit) if bad_hit else "未检出", "关键词初筛，不等于完整诊断"])
            rows.append(["提取到TOTEN", f"{len(energies)} 个" if energies else "0 个", energies[-1] + " eV" if energies else "—"])

        elif "LAMMPS" in software:
            done = "total wall time" in low or "loop time of" in low
            errs = re.findall(r"ERROR[^\\n]*", text, flags=re.I)
            rows.append(["运行结束标志", "是" if done else "未确认", "查找 wall time / loop time"])
            rows.append(["ERROR", errs[0][:120] if errs else "未检出", "需结合完整log判断"])

        else:
            errs = [line.strip() for line in text.splitlines() if "error" in line.lower() or "failed" in line.lower()]
            rows.append(["通用错误关键词", errs[0][:160] if errs else "未检出", "COMSOL/ANSYS仍应以求解器日志与收敛图为准"])

        st.dataframe(
            pd.DataFrame(rows, columns=["检查项", "结果", "说明"]),
            width="stretch",
            hide_index=True,
        )
        st.caption("这是离线文本初检，不是完整的数值可靠性判定。是否可信仍需检查收敛测试、模型假设和物理验证。")

    with st.expander("计算结果回填", expanded=False):
        tasks = list_items("theory_task")
        if not tasks:
            st.caption("当前项目尚无已保存计算任务。")
        else:
            mapping = {f"{x['title']}｜{x['created_at'][:10]}": x for x in tasks}
            selected = st.selectbox("对应计算任务", list(mapping), key="theory_result_task")
            status = st.selectbox("计算状态", ["已收敛", "未收敛", "部分完成", "结果异常/待排查"])
            key_output = st.text_area("关键结果 / 异常 / 与实验或文献的比较", height=110)
            if st.button("保存计算结果"):
                task = mapping[selected]
                add_item(
                    "theory_result",
                    "计算结果：" + task["title"],
                    key_output,
                    {"task_id": task["id"], "calculation_status": status},
                    "理论计算工作流",
                    status,
                )
                st.success("结果已回填到项目记忆，可供后续AI分析和研究决策读取。")

def gaps():
    df = _df()
    page_header(
        "研究空白",
        "用证据规模、近期活跃度和方法覆盖判断哪些方向已拥挤，哪些方向仍值得深入。",
        "RESEARCH OPPORTUNITY MAP",
    )

    project_context_strip()

    stats = topic_stats(df).copy()
    stats["近期占比"] = (stats["近5年"] / stats["总文献"].replace(0, np.nan) * 100).fillna(0).round(1)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        section_title("研究机会地图", "横轴是证据规模，纵轴是近五年活跃度；气泡越大，高优先级文献越多")
        fig = px.scatter(
            stats,
            x="总文献",
            y="近5年",
            size="S/A",
            color="DFT",
            hover_name="专题",
            hover_data={"近期占比": True, "S/A": True, "总文献": True, "近5年": True},
            color_continuous_scale=["#CBD5E1", "#7E77E7", "#1BA8C2"],
            size_max=46,
        )
        fig.update_layout(coloraxis_colorbar=dict(title="DFT"))
        plotly(fig, height=590, key="gap_map")
    with right:
        section_title("近期活跃方向", "不是“自动判定空白”，而是用于优先排查的探索线索")
        hot = stats.sort_values(["近期占比", "近5年"], ascending=False).head(8)
        mini_cards(
            [
                (
                    r["专题"],
                    f"近5年 {int(r['近5年'])} 篇｜总量 {int(r['总文献'])} 篇｜近期占比 {r['近期占比']}%",
                )
                for _, r in hot.iterrows()
            ]
        )

    section_title("专题统计", "研究空白仍需回到具体论文、实验条件和方法缺口中确认")
    st.dataframe(stats, width="stretch", height=380, hide_index=True)

    topic = st.selectbox("深入分析专题", list(CORE_TOPICS))
    evidence = topic_search(df, topic, 25, "KDP主线")

    if st.button("识别可验证研究空白", type="primary"):
        ok, _ = api_status()
        if not ok:
            st.warning("当前未连接 DeepSeek。")
            return
        try:
            with st.status("正在分析已有工作与证据缺口…", expanded=False):
                answer, sources = run_agent(
                    f"围绕{topic}识别3–6个可验证研究空白，每个给出验证方案。",
                    evidence,
                    "研究空白",
                )
            with st.container(border=True):
                st.markdown(answer)
            sources_block(sources)
            render_deepseek_usage()
            if st.button("保存研究空白分析到当前研究项目"):
                add_item(
                    "direction_decision",
                    "研究空白分析：" + topic,
                    answer[:1600],
                    {"topic": topic, "full_answer": answer},
                    "研究空白",
                    "待导师/全文核验",
                )
                st.success("已保存到当前项目记忆。")
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def ai_agent():
    df = _df()
    page_header(
        "AI科研助手",
        "不仅回答问题，还会读取当前研究项目中已经保存的文献、假设、实验、诊断和计算记忆，保持科研工作的连续性。",
        "RESEARCH EVIDENCE DESK",
    )

    project_context_strip()

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        task = c1.selectbox(
            "任务",
            ["自动判断", "文献问答", "多文献比较", "专题调研", "研究空白", "实验诊断", "理论方案", "报告生成"],
        )
        scope = c2.selectbox("本地证据范围", ["KDP主线", "S+A", "相关扩展", "全库"])
        n = c3.slider("本地证据文献数", 6, 20, 12)
        question = st.text_area(
            "科研问题",
            height=135,
            placeholder="直接像平时提问一样描述问题；系统会自动决定如何检索和组织证据。",
        )

    if not st.button("开始科研分析", type="primary"):
        soft_note("回答中的 [P#] 来自本地文献库，[W#] 来自外部补充资料；重要精确数值仍建议回查原文。")
        return

    if not question.strip():
        st.warning("请输入科研问题。")
        return

    status = st.status("正在启动科研分析…", expanded=True)
    status.write("检索本地证据")

    evidence = search_papers(df, question, n, scope)
    status.write(f"本地检索完成：{len(evidence)} 篇候选证据")

    if "_证据层级" in evidence.columns:
        counts = evidence["_证据层级"].value_counts().to_dict()
        status.write(
            f"证据结构：强直接 {counts.get('强直接证据',0)}｜直接 {counts.get('直接主题证据',0)}｜背景 {counts.get('背景/间接证据',0)}"
        )

    section_title("本地证据", "AI 会继续补充外部资料，但不会把普通网页当作同等级论文证据")
    evidence_table(evidence, height=390)

    ok, _ = api_status()
    if not ok:
        status.update(label="AI 未连接，已完成离线检索", state="complete")
        st.markdown(offline_summary(evidence, question))
        return

    section_title("科研回答", "边生成边显示；复杂任务会自动切换更深推理")
    answer = ""
    sources = []
    model_used = ""

    with st.chat_message("assistant"):
        answer_box = st.empty()

        try:
            for event in stream_agent(question, evidence, task):
                tp = event.get("type")
                if tp == "stage":
                    status.write(event.get("text", ""))
                elif tp == "reasoning":
                    status.update(label="正在进行深度分析…", state="running")
                elif tp == "content":
                    answer += event.get("text", "")
                    answer_box.markdown(answer + "\n\n▌")
                elif tp == "done":
                    sources = event.get("sources", [])
                    model_used = event.get("model", "")
                    status.update(
                        label=f"科研分析完成 · {model_used}",
                        state="complete",
                        expanded=False,
                    )
                elif tp == "error":
                    raise RuntimeError(event.get("text", "AI 调用失败"))
            answer_box.markdown(answer)
        except Exception as exc:
            status.update(label="AI 调用失败", state="error")
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)
            return

    sources_block(sources)
    render_deepseek_usage()
    st.download_button(
        "导出回答 Word",
        docx_bytes("AI科研助手分析", answer, sources),
        "AI科研助手分析.docx",
    )

    if answer and st.button("保存这次AI分析到当前研究项目"):
        add_item(
            "ai_note",
            question[:80] + ("…" if len(question) > 80 else ""),
            answer[:1600],
            {"question": question, "task": task, "model": model_used, "full_answer": answer},
            "AI科研助手",
            "待核验",
        )
        st.success("已保存。后续AI会读取这条项目记忆，而不需要你重复讲背景。")


def reports():
    df = _df()
    page_header(
        "报告中心",
        "把专题调研、方向论证、理论方案和诊断结果直接转成可继续编辑的研究报告。",
        "REPORT STUDIO",
    )

    project_context_strip()

    templates = [
        "组会专题汇报",
        "专题文献调研",
        "开题方向论证",
        "理论计算方案总结",
        "开裂诊断报告",
    ]

    with st.container(border=True):
        kind = st.radio("报告类型", templates, horizontal=True)
        c1, c2 = st.columns([1, 1.5])
        topic = c1.selectbox("主题", list(CORE_TOPICS))
        extra = c2.text_area("额外要求", height=92, placeholder="例如：突出开裂机理与后续两周实验计划。")

    evidence = topic_search(df, topic, 20, "KDP主线")
    section_title("报告证据集", "报告会优先引用以下相关文献")
    evidence_table(evidence, height=340)

    if not st.button("生成报告", type="primary"):
        return

    ok, _ = api_status()
    if not ok:
        st.markdown(offline_summary(evidence, topic))
        return

    try:
        with st.status("正在生成报告…", expanded=False):
            answer, sources = run_agent(
                f"生成{kind}，主题={topic}。要求：{extra}",
                evidence,
                "报告生成",
            )
        with st.container(border=True):
            st.markdown(answer)
        sources_block(sources)
        render_deepseek_usage()
        st.download_button(
            "导出 Word",
            docx_bytes(topic + "-" + kind, answer, sources),
            topic + "_" + kind + ".docx",
        )
        if st.button("保存报告到当前研究项目"):
            add_item(
                "report",
                kind + "：" + topic,
                answer[:1600],
                {"kind": kind, "topic": topic, "full_answer": answer},
                "报告中心",
                "草稿",
            )
            st.success("已保存到当前项目记忆。")
    except Exception as exc:
        safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def audit():
    df = _df()
    page_header(
        "数据审计",
        "持续检查文献库覆盖、缺失字段、推荐层级和未分类记录，避免“看起来很多、实际不可用”。",
        "DATA QUALITY",
    )

    total = len(df)
    rel = len(material_scope(df, "KDP主线"))
    no_abs = int((df["摘要"].str.strip() == "").sum())
    no_doi = int((df["DOI"].str.strip() == "").sum())

    metric_cards(
        [
            {"label": "当前加载记录", "value": f"{total:,}", "note": "完整去重库", "accent": COLORS["primary"]},
            {"label": "KDP主研究池", "value": f"{rel:,}", "note": "默认研究范围", "accent": COLORS["cyan"]},
            {"label": "无摘要", "value": no_abs, "note": f"{no_abs/max(total,1)*100:.1f}% 缺失", "accent": COLORS["orange"]},
            {"label": "无 DOI", "value": no_doi, "note": f"{no_doi/max(total,1)*100:.1f}% 缺失", "accent": COLORS["red"]},
        ]
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        section_title("推荐层级分布", "S/A/B/C 是优先级，不删除任何相关文献")
        tiers = (
            df["V5推荐等级"]
            .value_counts()
            .rename_axis("等级")
            .reset_index(name="文献数")
        )
        fig = px.pie(
            tiers,
            names="等级",
            values="文献数",
            hole=.64,
            color_discrete_sequence=["#5B5BD6", "#19B6C9", "#22A699", "#9EABC0", "#D5DCE6"],
        )
        fig.update_traces(textinfo="percent+label", textfont_size=11)
        plotly(fig, height=470, key="audit_tiers")

    with right:
        section_title("字段完整性", "优先补齐摘要和 DOI，能显著提升 AI 证据质量")
        miss = pd.DataFrame(
            {
                "字段": ["摘要", "DOI"],
                "缺失": [no_abs, no_doi],
                "完整": [total-no_abs, total-no_doi],
            }
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(y=miss["字段"], x=miss["完整"], orientation="h", name="完整", marker_color="#46B394"))
        fig.add_trace(go.Bar(y=miss["字段"], x=miss["缺失"], orientation="h", name="缺失", marker_color="#E77A7E"))
        fig.update_layout(barmode="stack", xaxis_title="记录数", yaxis_title="")
        plotly(fig, height=470, key="audit_missing")

    section_title("证据质量", "不再单独设置“可信度中心”；可靠性直接作为数据审计和各科研模块的底层约束")
    kdp = material_scope(df, "KDP主线")
    s = kdp[kdp["V5推荐等级"] == "S 核心 50"]
    if len(s):
        s_complete = float((s["证据完整度分"] >= 70).mean() * 100) if "证据完整度分" in s else 0.0
        s_ab = float(s["证据使用等级"].isin(["A 可用于重点论证", "B 可用于辅助论证"]).mean() * 100) if "证据使用等级" in s else 0.0
        s_pending = int(
            (
                s["作用机制"].isin(["待核验（摘要未明确）", "摘要证据不足"])
                | s["宏观结果"].isin(["待核验（摘要未明确）", "摘要证据不足"])
                | s["_方法标签"].isin(["待核验（摘要未明确）", "摘要证据不足"])
            ).sum()
        )
    else:
        s_complete = s_ab = 0.0
        s_pending = 0

    metric_cards(
        [
            {"label": "S层完整度达标", "value": f"{s_complete:.0f}%", "note": "完整度≥70", "accent": COLORS["teal"]},
            {"label": "S层A/B可用证据", "value": f"{s_ab:.0f}%", "note": "可重点/辅助论证", "accent": COLORS["cyan"]},
            {"label": "S层待核字段", "value": s_pending, "note": "越少越好", "accent": COLORS["orange"]},
            {"label": "人工Gold Standard", "value": "待建立", "note": "未完成前不宣称AI准确率", "accent": COLORS["violet"]},
        ]
    )

    section_title("推荐等级明细", "用于确认每一层的实际记录规模")
    st.dataframe(tiers, width="stretch", hide_index=True)

    soft_note(
        "当前加载总记录代表完整去重库；相关池只是主研究标签。S 核心 / A 重点 / B 扩展仅用于阅读优先级，剩余相关文献仍保留在 C 扩展/背景中并可继续检索。"
    )
