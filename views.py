
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
from engine import TOPICS, load_data, offline_summary, search_papers, topic_search, topic_stats
from reports import docx_bytes, excel_bytes
from security import safe_error
from ui import (
    COLORS,
    evidence_table,
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
        "把文献、缺陷机制、实验变量与计算路线压缩到同一个研究视野中。",
        "RESEARCH COMMAND CENTER",
    )

    rel = int((df["V5相关池"] == "KDP/DKDP相关池").sum())
    tiers = _tier_counts(df)
    related = df[df["V5相关池"] == "KDP/DKDP相关池"]
    max_year = int(related["年份"].max()) if len(related) else 0
    recent_n = int((related["年份"] >= max_year - 4).sum()) if max_year else 0

    metric_cards(
        [
            {"label": "全库去重文献", "value": f"{len(df):,}", "note": "完整数据库", "accent": COLORS["primary"]},
            {"label": "KDP / DKDP 相关池", "value": f"{rel:,}", "note": "主研究证据池", "accent": COLORS["cyan"]},
            {"label": "S 核心", "value": tiers["S"], "note": "最高优先级", "accent": COLORS["violet"]},
            {"label": "A 重点", "value": tiers["A"], "note": "重点精读层", "accent": COLORS["orange"]},
            {"label": "B 扩展", "value": tiers["B"], "note": "主题扩展层", "accent": COLORS["teal"]},
            {"label": "近五年相关文献", "value": f"{recent_n:,}", "note": f"{max_year-4}–{max_year}" if max_year else "—", "accent": COLORS["green"]},
        ]
    )

    section_title("研究主线", "统一用“来源—机制—后果—验证”组织开裂与缺陷问题")
    research_chain()

    left, right = st.columns([1.04, 1], gap="large")
    with left:
        section_title("专题证据规模", "快速判断哪些问题已有较厚证据，哪些仍需补充")
        stats = topic_stats(df).sort_values("总文献", ascending=True)

        fig = go.Figure()

        # 总证据规模：低饱和背景条
        fig.add_trace(
            go.Bar(
                x=stats["总文献"],
                y=stats["专题"],
                orientation="h",
                name="全部相关文献",
                marker=dict(
                    color="#DCE4EF",
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
                    color="#22AFC3",
                    line=dict(width=0),
                ),
                text=stats["近5年"].where(stats["近5年"] > 0, ""),
                textposition="outside",
                textfont=dict(size=10, color="#5E6E84"),
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
        fig.update_layout(xaxis_title="年份", yaxis_title="发文量")
        plotly(fig, height=520, key="dashboard_trend")

    section_title("核心证据库", "S 核心 50：用于开题、机制论证和关键路线设计的优先文献")
    top = (
        df[df["V5推荐等级"] == "S 核心 50"]
        .sort_values("V5科研优先分", ascending=False)
    )
    show_cols = [
        "题名", "年份", "期刊", "缺陷/应力来源", "作用机制", "宏观结果",
        "_方法标签", "V5科研优先分", "DOI",
    ]
    show_cols = [c for c in show_cols if c in top.columns]
    st.dataframe(
        top[show_cols],
        width="stretch",
        height=450,
        hide_index=True,
        column_config={
            "V5科研优先分": st.column_config.ProgressColumn(
                "科研优先分", min_value=0, max_value=100, format="%.1f"
            )
        },
    )


def literature():
    df = _df()
    page_header(
        "文献中心",
        "从 6,000+ 条记录中快速定位真正相关的证据，并保留 DOI、分类、方法和证据层级。",
        "LITERATURE INTELLIGENCE",
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1.15])
        scope = c1.selectbox("证据范围", ["全库", "相关池", "S+A"], index=1)
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
        "题名", "作者", "年份", "期刊", "_证据层级", "V5推荐等级", "V5科研优先分",
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
            )
        },
    )
    st.download_button(
        "导出当前结果为 Excel",
        excel_bytes(result[cols], "文献检索"),
        "KDP_DKDP_文献检索.xlsx",
    )


# ---- Knowledge graph -------------------------------------------------------

KG_UNCERTAIN = {"基础物性/其他", "机制未明确", "结果未明确", "未命中", ""}
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
    双矩阵研究路径图：
    左：缺陷/应力来源 × 局部机制
    右：局部机制 × 宏观后果

    相比桑基图，它不会因为粗线交叉导致信息糊成一片，
    还能直接看出“哪一对关系”证据最强。
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
        horizontal_spacing=.13,
        subplot_titles=(
            "缺陷 / 应力来源  ×  局部机制",
            "局部机制  ×  宏观后果",
        ),
    )

    colorscale = [
        [0.00, "#0E1728"],
        [0.14, "#17233B"],
        [0.35, "#314269"],
        [0.62, "#5D63C8"],
        [0.82, "#4A8FC1"],
        [1.00, "#20B6B0"],
    ]

    fig.add_trace(
        go.Heatmap(
            z=sm_pivot.values,
            x=sm_pivot.columns,
            y=sm_pivot.index,
            colorscale=colorscale,
            zmin=0,
            showscale=False,
            text=np.where(
                sm_pivot.values > 0,
                sm_pivot.values.astype(int).astype(str),
                "",
            ),
            texttemplate="%{text}",
            textfont=dict(size=12, color="#F2F6FB"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "→ %{x}<br>"
                "证据文献 %{z:.0f} 篇"
                "<extra></extra>"
            ),
            xgap=4,
            ygap=4,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Heatmap(
            z=mo_pivot.values,
            x=mo_pivot.columns,
            y=mo_pivot.index,
            colorscale=colorscale,
            zmin=0,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="文献数",
                    font=dict(color="#AFC0D5"),
                ),
                thickness=10,
                len=.70,
                x=1.02,
                tickfont=dict(color="#AFC0D5"),
            ),
            text=np.where(
                mo_pivot.values > 0,
                mo_pivot.values.astype(int).astype(str),
                "",
            ),
            texttemplate="%{text}",
            textfont=dict(size=12, color="#F2F6FB"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "→ %{x}<br>"
                "证据文献 %{z:.0f} 篇"
                "<extra></extra>"
            ),
            xgap=4,
            ygap=4,
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        paper_bgcolor="#0B1220",
        plot_bgcolor="#0B1220",
        height=610,
        margin=dict(l=30, r=90, t=80, b=30),
        font=dict(
            family='Inter, "Microsoft YaHei", Arial',
            color="#DCE7F4",
            size=12,
        ),
    )

    fig.update_annotations(
        font=dict(
            color="#EEF4FA",
            size=15,
        )
    )

    fig.update_xaxes(
        side="top",
        tickangle=-22,
        tickfont=dict(color="#B7C5D7", size=11),
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        tickfont=dict(color="#B7C5D7", size=11),
        showgrid=False,
        zeroline=False,
        autorange="reversed",
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


def _orbital_graph(chain: pd.DataFrame, top_n=34):
    chain = _top_chain(chain, top_n)

    sc = chain.groupby("缺陷/应力来源")["文献数"].sum().sort_values(ascending=False)
    mc = chain.groupby("作用机制")["文献数"].sum().sort_values(ascending=False)
    oc = chain.groupby("宏观结果")["文献数"].sum().sort_values(ascending=False)

    positions = {"CENTER": (0., 0., 0.)}
    for n, p in zip(sc.index, _sphere_points(len(sc), 1.55, .1)):
        positions["S|" + n] = p
    for n, p in zip(mc.index, _sphere_points(len(mc), 2.95, .9)):
        positions["M|" + n] = p
    for n, p in zip(oc.index, _sphere_points(len(oc), 4.25, 1.7)):
        positions["O|" + n] = p

    fig = go.Figure()

    for radius in (1.55, 2.95, 4.25):
        for plane in ("xy", "xz", "yz"):
            fig.add_trace(_orbit_trace(radius, plane))

    max_w = max(chain["文献数"].max(), 1)

    # center -> source
    for n, w in sc.items():
        x0, y0, z0 = positions["CENTER"]
        x1, y1, z1 = positions["S|" + n]
        fig.add_trace(
            go.Scatter3d(
                x=[x0, x1], y=[y0, y1], z=[z0, z1],
                mode="lines",
                line=dict(color=_rgba(COLORS["orange"], .22), width=1.3 + 3.5*math.sqrt(w/max_w)),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    sm = chain.groupby(["缺陷/应力来源", "作用机制"], as_index=False)["文献数"].sum()
    for _, r in sm.iterrows():
        x0, y0, z0 = positions["S|" + r["缺陷/应力来源"]]
        x1, y1, z1 = positions["M|" + r["作用机制"]]
        fig.add_trace(
            go.Scatter3d(
                x=[x0, x1], y=[y0, y1], z=[z0, z1],
                mode="lines",
                line=dict(color="rgba(141,124,255,.25)", width=1 + 3*math.sqrt(r["文献数"]/max_w)),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    mo = chain.groupby(["作用机制", "宏观结果"], as_index=False)["文献数"].sum()
    for _, r in mo.iterrows():
        x0, y0, z0 = positions["M|" + r["作用机制"]]
        x1, y1, z1 = positions["O|" + r["宏观结果"]]
        fig.add_trace(
            go.Scatter3d(
                x=[x0, x1], y=[y0, y1], z=[z0, z1],
                mode="lines",
                line=dict(color="rgba(29,190,207,.22)", width=1 + 3*math.sqrt(r["文献数"]/max_w)),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    def add_nodes(names, counts, prefix, color, layer):
        xs, ys, zs, hover, size = [], [], [], [], []
        mx = max(counts.max(), 1)
        for n in names:
            x, y, z = positions[prefix + "|" + n]
            xs.append(x); ys.append(y); zs.append(z)
            hover.append(f"<b>{n}</b><br>{layer}<br>关联文献 {int(counts[n])} 篇")
            size.append(10 + 18*math.sqrt(counts[n]/mx))

        # glow
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs, mode="markers",
                marker=dict(size=[s*1.55 for s in size], color=_rgba(color, .09), line=dict(width=0)),
                hoverinfo="skip", showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs, mode="markers",
                marker=dict(size=size, color=color, opacity=.96, line=dict(color="rgba(255,255,255,.8)", width=.8)),
                hovertext=hover, hoverinfo="text",
                name=layer,
            )
        )

    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode="markers+text",
            text=["KDP / DKDP"],
            textposition="top center",
            marker=dict(size=34, color="#F5A55B", line=dict(color="white", width=1.4)),
            textfont=dict(color="#F3F7FB", size=13),
            hovertext=["KDP/DKDP 开裂与缺陷研究中心"],
            hoverinfo="text",
            name="研究中心",
        )
    )

    add_nodes(list(sc.index), sc, "S", "#E87755", "缺陷 / 应力来源")
    add_nodes(list(mc.index), mc, "M", "#6379D6", "局部机制")
    add_nodes(list(oc.index), oc, "O", "#20B6B0", "宏观后果")

    fig.update_layout(
        paper_bgcolor="#07111E",
        plot_bgcolor="#07111E",
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(
            orientation="h", y=1.02, x=.02,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#B8C6D8", size=11),
        ),
        scene=dict(
            bgcolor="#07111E",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="cube",
            camera=dict(eye=dict(x=1.35, y=1.55, z=1.12)),
        ),
        font=dict(family='Inter,"Microsoft YaHei"', color="#DDE7F4"),
    )
    return fig


def knowledge_graph():
    df = _df()
    page_header(
        "知识图谱",
        "把数千篇文献压缩成可旋转、可追踪的“来源—机制—后果”研究网络，而不是堆叠默认图表。",
        "KNOWLEDGE GRAPH",
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1.05, 1.1])
        scope = c1.radio("范围", ["相关池", "S+A", "全库"], horizontal=True)
        hide_uncertain = c2.toggle("隐藏未明确分类", value=True)
        core_raw_only = c3.toggle("统计仅看开裂 / 缺陷核心", value=True)

    if scope == "全库":
        work = df.copy()
    elif scope == "相关池":
        work = df[df["V5相关池"] == "KDP/DKDP相关池"].copy()
    else:
        work = df[df["V5推荐等级"].isin(["S 核心 50", "A 重点 150"])].copy()

    original_n = len(work)
    if hide_uncertain:
        work = work[
            ~work["缺陷/应力来源"].isin(KG_UNCERTAIN)
            & ~work["作用机制"].isin(KG_UNCERTAIN)
            & ~work["宏观结果"].isin(KG_UNCERTAIN)
        ].copy()

    chain = (
        work.groupby(["缺陷/应力来源", "作用机制", "宏观结果"], as_index=False)
        .size()
        .rename(columns={"size": "文献数"})
    )

    if chain.empty:
        st.warning("当前筛选条件下没有可用于构建知识图谱的关系。")
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

    tab1, tab2, tab3 = st.tabs(["研究主线", "3D 关系星图", "分类与关系"])

    with tab1:
        c1, c2 = st.columns([1, 1.25])
        with c1:
            top_n = st.slider(
                "关系矩阵保留的最强关系",
                10,
                min(40, len(chain)),
                min(26, len(chain)),
            )
        with c2:
            soft_note(
                "研究主线已从桑基图改成“双矩阵路径图”："
                "左边看来源如何进入机制，右边看机制如何走向后果。"
                "颜色越亮、数字越大，说明文献证据越厚。"
            )

        fig = _relationship_matrix(chain, top_n=top_n)
        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            height=610,
            config={"displaylogo": False},
        )

        section_title(
            "最强研究路径",
            "把双矩阵中的高强度关系重新组合成完整的来源—机制—后果路径",
        )

        strongest = (
            chain.sort_values("文献数", ascending=False)
            .head(12)
            .copy()
        )

        mini_cards(
            [
                (
                    f"{r['缺陷/应力来源']}  →  {r['作用机制']}  →  {r['宏观结果']}",
                    f"当前文献库关联证据：{int(r['文献数'])} 篇",
                )
                for _, r in strongest.iterrows()
            ]
        )

    with tab2:
        left, right = st.columns([1, 1.2])
        with left:
            relation_limit = st.slider("星图保留关系数", 12, min(50, len(chain)), min(32, len(chain)))
        with right:
            soft_note("深色星图采用三层轨道：来源 → 机制 → 后果。节点标签默认隐藏，悬停查看，避免文字互相遮挡。")
        fig = _orbital_graph(chain, top_n=relation_limit)
        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            height=780,
            config={"displaylogo": False, "scrollZoom": True},
        )

    with tab3:
        left, right = st.columns([1.08, 1], gap="large")
        with left:
            section_title("核心详细分类", "保留与你当前开裂与缺陷方向直接相关的二级分类")
            raw = work["详细二级分类"].fillna("").replace("", "未命中详细分类")
            raw_counts = raw.value_counts().rename_axis("原始详细分类").reset_index(name="文献数")
            if core_raw_only:
                pattern = "|".join(re.escape(k) for k in KG_CORE_RAW_KEYWORDS)
                raw_counts = raw_counts[
                    raw_counts["原始详细分类"].str.contains(pattern, case=False, regex=True)
                ].copy()
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
                fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="文献数")
                fig.update_traces(marker_line_width=0)
                plotly(fig, height=700, key="kg_categories")
            else:
                st.info("当前条件下没有命中的核心详细分类。")

        with right:
            section_title("关系强度", "优先看文献证据较厚的研究链")
            rel = chain.copy()
            rel["研究链路"] = (
                rel["缺陷/应力来源"] + " → " + rel["作用机制"] + " → " + rel["宏观结果"]
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

    with st.container(border=True):
        c1, c2 = st.columns([1.25, 1])
        topic = c1.selectbox("研究专题", list(TOPICS))
        n = c2.slider("代表文献数", 8, 40, 20)

    papers = topic_search(df, topic, n, "相关池")

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
        st.download_button(
            "导出 Word",
            docx_bytes(topic + "专题调研", answer, sources),
            topic + "_专题调研.docx",
        )


def compare():
    df = _df()
    page_header(
        "多文献比较",
        "把多篇论文放在同一证据坐标系里比较对象、方法、结论、差异与可复现价值。",
        "PAPER COMPARISON",
    )

    with st.container(border=True):
        q = st.text_input("检索候选论文", placeholder="输入关键词后缩小候选集")
        cand = search_papers(df, q, 60, "相关池") if q else search_papers(df, "", 60, "S+A")
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
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def crack_diagnosis():
    df = _df()
    page_header(
        "开裂诊断",
        "将实验现象、工艺变量和文献证据放在同一诊断链中，优先找最可能的根因与最小验证实验。",
        "CRACK DIAGNOSTICS",
    )

    phenomenon = st.text_area(
        "开裂 / 缺陷现象",
        height=110,
        placeholder="例如：取晶后约 30 min 出现纵向裂纹，裂纹从籽晶附近开始扩展……",
    )

    options = [
        "未知", "明显异常", "偏高/偏快/强约束", "可疑",
        "一般/不确定", "较好/稳定", "偏低/偏慢/低约束",
    ]

    states = {}
    with st.container(border=True):
        section_title("实验变量快照", "不要求一次填全；未知项可保留为“未知”")
        cols = st.columns(2)
        for i, variable in enumerate(VARIABLES):
            states[variable] = cols[i % 2].selectbox(variable, options, key="diag_" + variable)

    if not st.button("执行根因诊断", type="primary"):
        return

    result = diagnose(states)
    risk_map = {"高": 3, "中": 2, "低": 1, "待核": 0}
    plot_df = result.copy()
    plot_df["_风险值"] = plot_df["风险"].map(risk_map)

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        section_title("风险排序", "优先验证高风险变量")
        fig = px.bar(
            plot_df.sort_values("_风险值"),
            x="_风险值",
            y="变量",
            orientation="h",
            color="_风险值",
            color_continuous_scale=["#CBD5E1", "#F4C56C", "#E66D72"],
        )
        fig.update_layout(coloraxis_showscale=False, xaxis=dict(tickvals=[0,1,2,3], ticktext=["待核","低","中","高"]), xaxis_title="", yaxis_title="")
        plotly(fig, height=510, key="diagnosis_risk")
    with right:
        section_title("诊断明细", "机制、最小对照实验与关键判据")
        st.dataframe(
            result[["变量", "当前状态", "风险", "可能机理", "最小对照实验", "关键指标"]],
            width="stretch",
            height=510,
            hide_index=True,
        )

    evidence = search_papers(
        df,
        phenomenon + " crack thermal stress inclusion dislocation supersaturation",
        15,
        "相关池",
    )
    section_title("关联文献证据", "诊断建议应与直接或间接文献证据对应")
    evidence_table(evidence, height=400)

    ok, _ = api_status()
    if ok:
        extra = "\n".join(
            f"{x['变量']}={x['当前状态']}，风险={x['风险']}"
            for _, x in result.iterrows()
        )
        try:
            with st.status("DeepSeek 正在综合变量与证据…", expanded=False):
                answer, sources = run_agent(
                    phenomenon or "诊断 KDP/DKDP 开裂原因",
                    evidence,
                    "实验诊断",
                    extra,
                )
            with st.container(border=True):
                st.markdown(answer)
            sources_block(sources)
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def experiment_design():
    page_header(
        "对照实验设计",
        "把复杂开裂问题拆成单变量可验证矩阵，明确基线、实验组、关键指标与判据。",
        "EXPERIMENT DESIGN",
    )

    with st.container(border=True):
        selected = st.multiselect(
            "准备验证的变量",
            list(VARIABLES),
            default=["降温速率", "籽晶固定方式", "过饱和度"],
        )
        baseline = st.text_area(
            "当前标准流程 / 基线",
            placeholder="填写你当前稳定使用的生长与冷却流程；不填则使用“当前标准流程”。",
        )

    if not selected:
        soft_note("至少选择一个变量后生成实验矩阵。")
        return

    matrix = experiment_matrix(selected, baseline)
    metric_cards(
        [
            {"label": "变量数", "value": len(selected), "note": "单变量对照", "accent": COLORS["primary"]},
            {"label": "建议重复", "value": "≥ 3", "note": "每组独立样品 / 批次", "accent": COLORS["orange"]},
            {"label": "设计原则", "value": "单变量", "note": "其余流程保持一致", "accent": COLORS["teal"]},
        ]
    )
    section_title("实验矩阵", "可以直接作为组会讨论或实验计划草案")
    st.dataframe(matrix, width="stretch", height=480, hide_index=True)
    st.download_button(
        "导出实验矩阵 Excel",
        excel_bytes(matrix, "对照实验"),
        "KDP_DKDP_对照实验设计.xlsx",
    )


def theory():
    df = _df()
    page_header(
        "理论计算助手",
        "把 DFT、MD、有限元的研究目标转成可执行的建模—收敛—输出—验证路线。",
        "COMPUTATIONAL WORKBENCH",
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1.15])
        method = c1.selectbox("计算类型", ["DFT/第一性原理", "分子动力学 MD", "有限元 FEA"])
        target = c2.selectbox(
            "研究对象",
            [
                "氢空位", "钾空位", "氧/磷酸根缺陷", "杂质/掺杂", "缺陷复合体",
                "包裹体附近应力", "加工亚表面损伤", "裂纹萌生", "热应力场",
                "籽晶/固定约束", "DKDP同位素效应",
            ],
        )
        software = c3.multiselect(
            "软件",
            ["Materials Studio", "Quantum ESPRESSO", "VASP", "Gaussian", "LAMMPS", "COMSOL", "ANSYS", "Python"],
        )
        goal = st.text_area("研究目标", placeholder="例如：比较不同氢空位位置与电荷态对吸收边和缺陷态的影响。")

    skeletons = {
        "DFT/第一性原理": [
            ("结构与基准", "CIF / 超胞 / k 点 / 截断能 / 泛函与收敛"),
            ("缺陷模型", "缺陷位置 / 电荷态 / 结构优化 / 形成能"),
            ("电子与光学", "TDOS / PDOS / 电荷密度 / 介电函数 / 吸收谱"),
            ("实验验证", "与 UV 吸收、缺陷表征和损伤现象对照"),
        ],
        "分子动力学 MD": [
            ("模型与势函数", "完整晶体基准 / 势函数有效性"),
            ("工况设计", "缺陷 / 热循环 / 加工 / 冲击"),
            ("演化量", "位错 / 裂纹 / 原子应力 / 能量"),
            ("验证", "与形貌、裂纹位置、热学结果比较"),
        ],
        "有限元 FEA": [
            ("材料参数", "各向异性弹性 / 热膨胀 / 导热"),
            ("边界条件", "温度 / 浓度 / 夹持 / 籽晶固定"),
            ("场分布", "主应力 / 应变能 / 危险区"),
            ("实验映射", "与裂纹起点和方向进行空间共定位"),
        ],
    }
    section_title("推荐工作流", "根据计算类型自动给出主干路线")
    mini_cards(skeletons[method])

    evidence = search_papers(df, f"{method} {target} {goal}", 18, "相关池")
    section_title("方法证据", "优先参考已有 KDP/DKDP 理论工作，避免模型与参数脱离体系")
    evidence_table(evidence, height=390)

    if st.button("生成完整计算方案", type="primary"):
        ok, _ = api_status()
        if not ok:
            st.warning("当前未连接 DeepSeek。")
            return
        try:
            with st.status("正在生成计算路线…", expanded=False):
                answer, sources = run_agent(
                    f"{method}; {target}; 软件={software}; 目标={goal}",
                    evidence,
                    "理论方案",
                )
            with st.container(border=True):
                st.markdown(answer)
            sources_block(sources)
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def gaps():
    df = _df()
    page_header(
        "研究空白",
        "用证据规模、近期活跃度和方法覆盖判断哪些方向已拥挤，哪些方向仍值得深入。",
        "RESEARCH OPPORTUNITY MAP",
    )

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

    topic = st.selectbox("深入分析专题", list(TOPICS))
    evidence = topic_search(df, topic, 25, "相关池")

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
        except Exception as exc:
            safe_error("AI 服务暂时不可用，详细错误已记录。请稍后重试。", exc)


def ai_agent():
    df = _df()
    page_header(
        "AI 科研智能体",
        "默认融合本地文献库、最新外部资料与专业推理；全过程显示检索与生成状态，并保留证据来源。",
        "AI RESEARCH COPILOT",
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        task = c1.selectbox(
            "任务",
            ["自动判断", "文献问答", "多文献比较", "专题调研", "研究空白", "实验诊断", "理论方案", "报告生成"],
        )
        scope = c2.selectbox("本地证据范围", ["相关池", "S+A", "全库"])
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
    st.download_button(
        "导出回答 Word",
        docx_bytes("科研智能体回答", answer, sources),
        "科研智能体回答.docx",
    )


def reports():
    df = _df()
    page_header(
        "报告中心",
        "把专题调研、方向论证、理论方案和诊断结果直接转成可继续编辑的研究报告。",
        "REPORT STUDIO",
    )

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
        topic = c1.selectbox("主题", list(TOPICS))
        extra = c2.text_area("额外要求", height=92, placeholder="例如：突出开裂机理与后续两周实验计划。")

    evidence = topic_search(df, topic, 20, "相关池")
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
        st.download_button(
            "导出 Word",
            docx_bytes(topic + "-" + kind, answer, sources),
            topic + "_" + kind + ".docx",
        )
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
    rel = int((df["V5相关池"] == "KDP/DKDP相关池").sum())
    no_abs = int((df["摘要"].str.strip() == "").sum())
    no_doi = int((df["DOI"].str.strip() == "").sum())

    metric_cards(
        [
            {"label": "当前加载记录", "value": f"{total:,}", "note": "完整去重库", "accent": COLORS["primary"]},
            {"label": "相关池", "value": f"{rel:,}", "note": "KDP / DKDP 主库", "accent": COLORS["cyan"]},
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

    section_title("推荐等级明细", "用于确认每一层的实际记录规模")
    st.dataframe(tiers, width="stretch", hide_index=True)

    soft_note(
        "当前加载总记录代表完整去重库；相关池只是主研究标签。S 核心 / A 重点 / B 扩展仅用于阅读优先级，剩余相关文献仍保留在 C 扩展/背景中并可继续检索。"
    )
