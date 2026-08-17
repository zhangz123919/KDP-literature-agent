
import streamlit as st
from engine import load_data, search_papers, topic_search, topic_stats, offline_summary, TOPICS
from diagnosis import VARIABLES, diagnose, experiment_matrix
from agent import api_status, run_agent, stream_agent
from reports import excel_bytes, docx_bytes
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(
    page_title="KDP/DKDP科研智能体",
    page_icon="🔬",
    layout="wide",
)

st.markdown("""
<style>
html,body,[class*="css"]{font-family:"Microsoft YaHei","微软雅黑",Arial,sans-serif}
.block-container{padding-top:1rem;max-width:1580px}
[data-testid="stMetric"]{border:1px solid rgba(120,120,120,.18);border-radius:12px;padding:.8rem}
.chain{border-left:4px solid #4f46e5;padding:10px 14px;margin:8px 0}
</style>
""", unsafe_allow_html=True)

df = load_data()

if df.empty:
    st.error("缺少 data/KDP_全自动详细文献调研.xlsx")
    st.stop()

with st.sidebar:
    st.markdown("## 🔬 KDP/DKDP科研智能体")
    page = st.radio(
        "模块",
        [
            "🏠 科研驾驶舱",
            "📚 文献中心",
            "🗺️ 知识图谱",
            "🧭 专题调研",
            "⚖️ 多文献比较",
            "🧪 开裂诊断",
            "🧫 对照实验设计",
            "🧮 理论计算助手",
            "🕳️ 研究空白",
            "🤖 AI科研智能体",
            "📝 报告中心",
            "🩺 数据审计",
        ],
        label_visibility="collapsed",
    )

    ok, model = api_status()
    st.divider()

    if ok:
        st.success(f"AI已连接：{model}")
    else:
        st.warning("AI未连接：离线功能仍可用")

    st.caption("S/A/B只是优先级，不会删除文献。")


def sources_block(src):
    if src:
        with st.expander("查看依据文献"):
            for x in src:
                st.write(
                    f"[{x['编号']}] {x['题名']} "
                    f"({x['年份']}) DOI: {x['DOI']}"
                )


def evidence_table(data, height=None):
    cols = [
        "题名",
        "年份",
        "_证据层级",
        "V5推荐等级",
        "详细二级分类",
        "_方法标签",
        "DOI",
    ]

    cols = [c for c in cols if c in data.columns]

    st.dataframe(
        data[cols],
        use_container_width=True,
        hide_index=True,
        height=height,
    )


# =========================
# 知识图谱可视化辅助函数
# =========================

KG_UNCERTAIN = {
    "基础物性/其他",
    "机制未明确",
    "结果未明确",
    "未命中",
    "",
}

KG_CORE_RAW_KEYWORDS = [
    "缺陷", "空位", "杂质", "掺杂", "包裹体", "散射",
    "位错", "生长", "过饱和", "加工", "表面", "亚表面",
    "激光损伤", "损伤", "LIDT", "裂纹", "开裂", "应力",
    "吸收", "光热", "氢键", "质子", "籽晶", "固定",
    "DFT", "第一性原理", "分子动力学", "有限元",
]


def _kg_fibonacci_sphere(n, radius, phase=0.0):
    """在球面上均匀放置 n 个节点。"""
    if n <= 0:
        return []

    points = []
    golden = np.pi * (3.0 - np.sqrt(5.0))

    for i in range(n):
        y = 1.0 - 2.0 * (i + 0.5) / n
        ring = np.sqrt(max(0.0, 1.0 - y * y))
        theta = golden * i + phase
        x = np.cos(theta) * ring
        z = np.sin(theta) * ring
        points.append(
            (
                radius * x,
                radius * y,
                radius * z,
            )
        )

    return points


def _kg_make_sankey(chain):
    """来源 → 机制 → 后果 的聚焦型桑基图。"""
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
        chain["缺陷/应力来源"]
        .drop_duplicates()
    )
    mechanisms = list(
        chain["作用机制"]
        .drop_duplicates()
    )
    outcomes = list(
        chain["宏观结果"]
        .drop_duplicates()
    )

    labels = sources + mechanisms + outcomes
    node_index = {
        label: i
        for i, label in enumerate(labels)
    }

    link_source = []
    link_target = []
    link_value = []
    link_hover = []

    for _, row in sm.iterrows():
        link_source.append(
            node_index[row["缺陷/应力来源"]]
        )
        link_target.append(
            node_index[row["作用机制"]]
        )
        link_value.append(
            int(row["文献数"])
        )
        link_hover.append(
            f"{row['缺陷/应力来源']} → {row['作用机制']}：{int(row['文献数'])}篇"
        )

    for _, row in mo.iterrows():
        link_source.append(
            node_index[row["作用机制"]]
        )
        link_target.append(
            node_index[row["宏观结果"]]
        )
        link_value.append(
            int(row["文献数"])
        )
        link_hover.append(
            f"{row['作用机制']} → {row['宏观结果']}：{int(row['文献数'])}篇"
        )

    node_colors = (
        ["#E76F51"] * len(sources)
        + ["#457B9D"] * len(mechanisms)
        + ["#2A9D8F"] * len(outcomes)
    )

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=18,
                    thickness=22,
                    line=dict(
                        color="rgba(80,80,80,0.25)",
                        width=0.6,
                    ),
                    label=labels,
                    color=node_colors,
                    hovertemplate="%{label}<extra></extra>",
                ),
                link=dict(
                    source=link_source,
                    target=link_target,
                    value=link_value,
                    customdata=link_hover,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
            )
        ]
    )

    fig.update_layout(
        height=660,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20,
        ),
        font=dict(
            size=14,
        ),
    )

    return fig


def _kg_make_3d_ball(chain, max_relations=36):
    """
    立体球状关系图：
    中心 = KDP/DKDP开裂与缺陷研究
    第一层球壳 = 缺陷/应力来源
    第二层球壳 = 局部机制
    第三层球壳 = 宏观后果
    """
    top_chain = (
        chain.sort_values(
            "文献数",
            ascending=False,
        )
        .head(max_relations)
        .copy()
    )

    source_counts = (
        top_chain.groupby(
            "缺陷/应力来源"
        )["文献数"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    mech_counts = (
        top_chain.groupby(
            "作用机制"
        )["文献数"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    outcome_counts = (
        top_chain.groupby(
            "宏观结果"
        )["文献数"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    source_nodes = list(source_counts.index)
    mech_nodes = list(mech_counts.index)
    outcome_nodes = list(outcome_counts.index)

    positions = {
        "KDP/DKDP开裂与缺陷": (
            0.0,
            0.0,
            0.0,
        )
    }

    for name, xyz in zip(
        source_nodes,
        _kg_fibonacci_sphere(
            len(source_nodes),
            1.65,
            0.0,
        ),
    ):
        positions[
            "S|" + name
        ] = xyz

    for name, xyz in zip(
        mech_nodes,
        _kg_fibonacci_sphere(
            len(mech_nodes),
            3.15,
            0.8,
        ),
    ):
        positions[
            "M|" + name
        ] = xyz

    for name, xyz in zip(
        outcome_nodes,
        _kg_fibonacci_sphere(
            len(outcome_nodes),
            4.65,
            1.6,
        ),
    ):
        positions[
            "O|" + name
        ] = xyz

    # 边：中心→来源
    edge_rows = []

    for name, count in source_counts.items():
        edge_rows.append(
            (
                "KDP/DKDP开裂与缺陷",
                "S|" + name,
                int(count),
                f"中心 → {name}",
            )
        )

    # 来源→机制
    sm = (
        top_chain.groupby(
            ["缺陷/应力来源", "作用机制"],
            as_index=False,
        )["文献数"]
        .sum()
    )

    for _, row in sm.iterrows():
        edge_rows.append(
            (
                "S|" + row["缺陷/应力来源"],
                "M|" + row["作用机制"],
                int(row["文献数"]),
                f"{row['缺陷/应力来源']} → {row['作用机制']}",
            )
        )

    # 机制→后果
    mo = (
        top_chain.groupby(
            ["作用机制", "宏观结果"],
            as_index=False,
        )["文献数"]
        .sum()
    )

    for _, row in mo.iterrows():
        edge_rows.append(
            (
                "M|" + row["作用机制"],
                "O|" + row["宏观结果"],
                int(row["文献数"]),
                f"{row['作用机制']} → {row['宏观结果']}",
            )
        )

    max_edge = max(
        [x[2] for x in edge_rows],
        default=1,
    )

    fig = go.Figure()

    # 用多条独立线段绘制关系，宽度随文献量变化。
    for start, end, weight, desc in edge_rows:
        x0, y0, z0 = positions[start]
        x1, y1, z1 = positions[end]

        fig.add_trace(
            go.Scatter3d(
                x=[x0, x1],
                y=[y0, y1],
                z=[z0, z1],
                mode="lines",
                line=dict(
                    width=1.0
                    + 6.0
                    * np.sqrt(
                        weight / max_edge
                    ),
                    color="rgba(100,110,130,0.28)",
                ),
                hoverinfo="text",
                text=[
                    f"{desc}<br>{weight}篇",
                    f"{desc}<br>{weight}篇",
                ],
                showlegend=False,
            )
        )

    max_node = max(
        list(source_counts.values)
        + list(mech_counts.values)
        + list(outcome_counts.values)
        + [1]
    )

    def add_nodes(
        names,
        counts,
        prefix,
        color,
        layer_name,
    ):
        xs = []
        ys = []
        zs = []
        texts = []
        hover = []
        sizes = []

        for name in names:
            x, y, z = positions[
                prefix + "|" + name
            ]
            count = int(counts[name])

            xs.append(x)
            ys.append(y)
            zs.append(z)
            texts.append(name)
            hover.append(
                f"<b>{name}</b><br>"
                f"层级：{layer_name}<br>"
                f"关联文献：{count}篇"
            )
            sizes.append(
                8
                + 25
                * np.sqrt(
                    count / max_node
                )
            )

        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="markers+text",
                text=texts,
                textposition="top center",
                hovertext=hover,
                hoverinfo="text",
                marker=dict(
                    size=sizes,
                    color=color,
                    opacity=0.92,
                    line=dict(
                        color="white",
                        width=0.7,
                    ),
                ),
                name=layer_name,
            )
        )

    # 中心节点
    fig.add_trace(
        go.Scatter3d(
            x=[0],
            y=[0],
            z=[0],
            mode="markers+text",
            text=["KDP/DKDP"],
            textposition="top center",
            hovertext=[
                "<b>KDP/DKDP开裂与缺陷研究</b><br>知识图谱中心"
            ],
            hoverinfo="text",
            marker=dict(
                size=34,
                color="#F4A261",
                line=dict(
                    color="white",
                    width=1.2,
                ),
            ),
            name="研究中心",
        )
    )

    add_nodes(
        source_nodes,
        source_counts,
        "S",
        "#E76F51",
        "缺陷/应力来源",
    )

    add_nodes(
        mech_nodes,
        mech_counts,
        "M",
        "#457B9D",
        "局部机制",
    )

    add_nodes(
        outcome_nodes,
        outcome_counts,
        "O",
        "#2A9D8F",
        "宏观后果",
    )

    fig.update_layout(
        height=760,
        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0,
        ),
        legend=dict(
            orientation="h",
            y=1.02,
            x=0.02,
        ),
        scene=dict(
            xaxis=dict(
                visible=False
            ),
            yaxis=dict(
                visible=False
            ),
            zaxis=dict(
                visible=False
            ),
            aspectmode="cube",
            bgcolor="rgba(0,0,0,0)",
            camera=dict(
                eye=dict(
                    x=1.55,
                    y=1.55,
                    z=1.25,
                )
            ),
        ),
    )

    return fig


if page == "🏠 科研驾驶舱":

    st.title("🏠 科研驾驶舱")

    total = len(df)
    rel = (df["V5相关池"] == "KDP/DKDP相关池").sum()

    c = st.columns(5)
    c[0].metric("全库去重文献", f"{total:,}")
    c[1].metric("KDP/DKDP相关池", f"{rel:,}")
    c[2].metric(
        "S核心",
        int((df["V5推荐等级"] == "S 核心 50").sum()),
    )
    c[3].metric(
        "A重点",
        int((df["V5推荐等级"] == "A 重点 150").sum()),
    )
    c[4].metric(
        "B扩展",
        int((df["V5推荐等级"] == "B 扩展 800").sum()),
    )

    st.info("完整文献库始终保留；S/A/B只是阅读优先级。")

    st.markdown("""
<div class="chain"><b>① 缺陷/应力来源</b><br>
点缺陷｜杂质｜包裹体｜位错｜快速生长｜籽晶｜加工｜固定约束
</div>
<div class="chain"><b>② 局部机制</b><br>
氢键/晶格畸变｜缺陷态｜生长界面｜热-力应力
</div>
<div class="chain"><b>③ 宏观后果</b><br>
吸收/散射｜裂纹萌生｜LIDT下降｜激光损伤
</div>
<div class="chain"><b>④ 证据与控制</b><br>
DFT/MD/FEA + Raman/FTIR/XRD/AFM/光热/LIDT + 单变量对照
</div>
""", unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        stats = topic_stats(df).sort_values("总文献")
        st.plotly_chart(
            px.bar(
                stats,
                x="总文献",
                y="专题",
                orientation="h",
                title="专题证据规模",
            ),
            use_container_width=True,
        )

    with right:
        related = df[
            df["V5相关池"] == "KDP/DKDP相关池"
        ]
        trend = (
            related[related["年份"] > 0]
            .groupby("年份")
            .size()
            .reset_index(name="文献数")
        )

        st.plotly_chart(
            px.line(
                trend,
                x="年份",
                y="文献数",
                markers=True,
                title="研究趋势",
            ),
            use_container_width=True,
        )

    st.subheader("S核心50")

    top = (
        df[df["V5推荐等级"] == "S 核心 50"]
        .sort_values("V5科研优先分", ascending=False)
    )

    st.dataframe(
        top[
            [
                "题名",
                "年份",
                "期刊",
                "缺陷/应力来源",
                "作用机制",
                "宏观结果",
                "_方法标签",
                "V5科研优先分",
                "DOI",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=420,
    )


elif page == "📚 文献中心":

    st.title("📚 文献中心")

    c1, c2, c3 = st.columns(3)

    scope = c1.selectbox(
        "范围",
        ["全库", "相关池", "S+A"],
        index=1,
    )

    limit = c2.selectbox(
        "显示上限",
        [50, 100, 200, 500, 1000],
        index=2,
    )

    tiers = c3.multiselect(
        "等级",
        [
            "S 核心 50",
            "A 重点 150",
            "B 扩展 800",
            "C 扩展/背景",
            "D 非核心/待核",
        ],
    )

    q = st.text_input(
        "科研检索",
        placeholder="氢空位 额外吸收；包裹体 开裂；subsurface damage；DFT",
    )

    work = (
        df[df["V5推荐等级"].isin(tiers)]
        if tiers
        else df
    )

    result = search_papers(
        work,
        q,
        limit,
        scope,
    )

    cols = [
        "题名",
        "作者",
        "年份",
        "期刊",
        "_证据层级",
        "V5推荐等级",
        "V5科研优先分",
        "缺陷/应力来源",
        "作用机制",
        "宏观结果",
        "_方法标签",
        "被引次数",
        "DOI",
    ]

    cols = [c for c in cols if c in result.columns]

    st.success(f"当前显示 {len(result):,} 篇")

    st.dataframe(
        result[cols],
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    st.download_button(
        "下载Excel",
        excel_bytes(result[cols], "文献检索"),
        "KDP_DKDP_文献检索.xlsx",
    )


elif page == "🗺️ 知识图谱":

    @st.fragment
    def render_knowledge_graph():

        st.title("🗺️ KDP/DKDP开裂与缺陷知识图谱")
        st.caption(
            "聚焦“缺陷/应力来源 → 局部机制 → 宏观后果”，"
            "默认隐藏未明确分类，避免被大量基础物性文献淹没。"
        )

        c1, c2, c3 = st.columns(
            [1.1, 1.2, 1.4]
        )

        scope = c1.radio(
            "范围",
            [
                "相关池",
                "S+A",
                "全库",
            ],
            horizontal=False,
        )

        hide_uncertain = c2.checkbox(
            "隐藏未明确分类",
            value=True,
            help=(
                "隐藏“基础物性/其他、机制未明确、结果未明确”等"
                "低信息量节点，使图谱集中到开裂与缺陷主线。"
            ),
        )

        core_raw_only = c3.checkbox(
            "分类统计仅看开裂/缺陷核心",
            value=True,
            help=(
                "下方详细分类统计只保留缺陷、生长、加工、应力、"
                "开裂、激光损伤、理论计算等与你当前研究直接相关的分类。"
            ),
        )

        if scope == "全库":
            work = df.copy()

        elif scope == "相关池":
            work = df[
                df["V5相关池"]
                == "KDP/DKDP相关池"
            ].copy()

        else:
            work = df[
                df["V5推荐等级"].isin(
                    [
                        "S 核心 50",
                        "A 重点 150",
                    ]
                )
            ].copy()

        original_n = len(work)

        if hide_uncertain:
            work = work[
                ~work["缺陷/应力来源"].isin(
                    KG_UNCERTAIN
                )
                & ~work["作用机制"].isin(
                    KG_UNCERTAIN
                )
                & ~work["宏观结果"].isin(
                    KG_UNCERTAIN
                )
            ].copy()

        chain = (
            work.groupby(
                [
                    "缺陷/应力来源",
                    "作用机制",
                    "宏观结果",
                ],
                as_index=False,
            )
            .size()
            .rename(
                columns={
                    "size": "文献数"
                }
            )
        )

        if chain.empty:
            st.warning(
                "当前筛选条件下没有可用于构建知识图谱的关系。"
            )
            return

        active_docs = int(
            chain["文献数"].sum()
        )

        source_n = int(
            chain["缺陷/应力来源"]
            .nunique()
        )
        mech_n = int(
            chain["作用机制"]
            .nunique()
        )
        outcome_n = int(
            chain["宏观结果"]
            .nunique()
        )

        metrics = st.columns(5)

        metrics[0].metric(
            "当前文献范围",
            f"{original_n:,}",
        )
        metrics[1].metric(
            "有效关系文献",
            f"{active_docs:,}",
        )
        metrics[2].metric(
            "缺陷/应力来源",
            source_n,
        )
        metrics[3].metric(
            "局部机制",
            mech_n,
        )
        metrics[4].metric(
            "宏观后果",
            outcome_n,
        )

        st.info(
            "现在主图不再把“基础物性/其他 → 机制未明确 → 结果未明确”"
            "当成核心知识链；需要时可取消“隐藏未明确分类”查看完整情况。"
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "🔗 研究主线",
                "🌐 3D球状关系图",
                "📊 分类与关系统计",
            ]
        )

        with tab1:

            st.subheader(
                "缺陷/应力来源 → 局部机制 → 宏观后果"
            )

            st.plotly_chart(
                _kg_make_sankey(
                    chain
                ),
                use_container_width=True,
                config={
                    "displaylogo": False,
                },
            )

            st.markdown(
                "#### 最强研究链路"
            )

            top_chain = (
                chain.sort_values(
                    "文献数",
                    ascending=False,
                )
                .head(20)
                .copy()
            )

            top_chain["占有效关系比例"] = (
                top_chain["文献数"]
                / max(
                    active_docs,
                    1,
                )
                * 100
            ).round(1).astype(str) + "%"

            st.dataframe(
                top_chain[
                    [
                        "缺陷/应力来源",
                        "作用机制",
                        "宏观结果",
                        "文献数",
                        "占有效关系比例",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                height=430,
            )

        with tab2:

            st.subheader(
                "立体3D球状关系图"
            )

            st.caption(
                "中心是KDP/DKDP开裂与缺陷研究；"
                "第一层球壳=缺陷/应力来源，"
                "第二层=局部机制，第三层=宏观后果。"
                "节点越大表示关联文献越多；连线越粗表示关系越强。"
                "可用鼠标拖动旋转、滚轮缩放。"
            )

            max_rel = min(
                60,
                max(
                    12,
                    len(chain),
                ),
            )

            default_rel = min(
                36,
                max_rel,
            )

            relation_limit = st.slider(
                "3D图显示的最强关系数",
                min_value=min(
                    10,
                    max_rel,
                ),
                max_value=max_rel,
                value=default_rel,
                step=1,
                help=(
                    "关系太多会显得拥挤；一般20–40条最适合观察。"
                ),
            )

            st.plotly_chart(
                _kg_make_3d_ball(
                    chain,
                    max_relations=relation_limit,
                ),
                use_container_width=True,
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                },
            )

            st.markdown(
                """
**怎么看这张3D图：**
- 离中心最近：缺陷和应力“从哪里来”；
- 中间球壳：这些来源通过什么局部机制起作用；
- 最外球壳：最终表现为开裂、激光损伤、吸收/散射等什么后果；
- 粗连线：当前文献库中证据较多的研究路径；
- 小节点/细连线：可能是研究较少、值得进一步核查的方向。
"""
            )

        with tab3:

            left, right = st.columns(
                [1.15, 1]
            )

            with left:

                st.subheader(
                    "核心详细分类分布"
                )

                raw = (
                    work["详细二级分类"]
                    .fillna("")
                    .replace(
                        "",
                        "未命中详细分类",
                    )
                )

                raw_counts = (
                    raw.value_counts()
                    .rename_axis(
                        "原始详细分类"
                    )
                    .reset_index(
                        name="文献数"
                    )
                )

                if core_raw_only:

                    pattern = "|".join(
                        re.escape(k)
                        for k in KG_CORE_RAW_KEYWORDS
                    )

                    core_mask = (
                        raw_counts[
                            "原始详细分类"
                        ]
                        .str.contains(
                            pattern,
                            case=False,
                            regex=True,
                        )
                    )

                    raw_counts = (
                        raw_counts[
                            core_mask
                        ]
                        .copy()
                    )

                raw_counts = (
                    raw_counts
                    .head(35)
                )

                if not raw_counts.empty:

                    st.plotly_chart(
                        px.bar(
                            raw_counts.sort_values(
                                "文献数"
                            ),
                            x="文献数",
                            y="原始详细分类",
                            orientation="h",
                            title="详细分类文献量",
                        ),
                        use_container_width=True,
                    )

                else:
                    st.info(
                        "当前条件下没有命中的核心详细分类。"
                    )

            with right:

                st.subheader(
                    "关系强度排名"
                )

                relation_table = (
                    chain.assign(
                        研究链路=(
                            chain[
                                "缺陷/应力来源"
                            ]
                            + " → "
                            + chain[
                                "作用机制"
                            ]
                            + " → "
                            + chain[
                                "宏观结果"
                            ]
                        )
                    )
                    .sort_values(
                        "文献数",
                        ascending=False,
                    )
                    .head(30)
                )

                st.dataframe(
                    relation_table[
                        [
                            "研究链路",
                            "文献数",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=620,
                )

    render_knowledge_graph()

elif page == "🧭 专题调研":

    st.title("🧭 专题自动调研")

    topic = st.selectbox(
        "专题",
        list(TOPICS),
    )

    n = st.slider(
        "代表文献数",
        8,
        40,
        20,
    )

    papers = topic_search(
        df,
        topic,
        n,
        "相关池",
    )

    evidence_table(
        papers,
        height=420,
    )

    st.markdown(
        offline_summary(
            papers,
            topic,
        )
    )

    if st.button(
        "AI生成完整专题调研",
        type="primary",
    ):
        ok, _ = api_status()

        if not ok:
            st.warning(
                "未配置DeepSeek API Key。"
            )
        else:
            with st.status(
                "正在生成专题调研……",
                expanded=True,
            ) as status:

                st.write("✅ 已完成文献检索")
                st.write(
                    f"📚 已选取 {len(papers)} 篇证据文献"
                )
                st.write("🧠 DeepSeek 正在综合证据……")

                try:
                    answer, sources = run_agent(
                        f"围绕“{topic}”生成系统专题调研。",
                        papers,
                        "专题调研",
                    )

                    status.update(
                        label="专题调研生成完成",
                        state="complete",
                    )

                except Exception as exc:
                    status.update(
                        label="AI调用失败",
                        state="error",
                    )
                    st.error(
                        f"DeepSeek调用失败：{exc}"
                    )
                    st.stop()

            st.markdown(answer)
            sources_block(sources)

            st.download_button(
                "下载Word",
                docx_bytes(
                    topic + "专题调研",
                    answer,
                    sources,
                ),
                topic + "_专题调研.docx",
            )


elif page == "⚖️ 多文献比较":

    st.title("⚖️ 多文献比较")

    q = st.text_input(
        "检索候选论文"
    )

    cand = (
        search_papers(
            df,
            q,
            60,
            "相关池",
        )
        if q
        else search_papers(
            df,
            "",
            60,
            "S+A",
        )
    )

    mapping = {
        f"{r['题名']}｜{r['年份']}": i
        for i, r in cand.iterrows()
    }

    selected = st.multiselect(
        "选择2–6篇",
        list(mapping),
        max_selections=6,
    )

    if len(selected) >= 2:

        chosen = df.loc[
            [mapping[x] for x in selected]
        ]

        st.dataframe(
            chosen[
                [
                    "题名",
                    "年份",
                    "详细二级分类",
                    "_方法标签",
                    "自动研究问题",
                    "自动主要结论",
                    "DOI",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        if st.button(
            "AI深度比较",
            type="primary",
        ):
            ok, _ = api_status()

            if not ok:
                st.warning(
                    "未配置DeepSeek。"
                )
            else:
                try:
                    with st.spinner(
                        "DeepSeek正在比较文献……"
                    ):
                        answer, sources = run_agent(
                            "比较这些论文的研究对象、方法、结论、差异和借鉴价值。",
                            chosen,
                            "多文献比较",
                        )

                    st.markdown(answer)
                    sources_block(sources)

                except Exception as exc:
                    st.error(
                        f"DeepSeek调用失败：{exc}"
                    )

    else:
        st.info(
            "至少选择2篇论文。"
        )


elif page == "🧪 开裂诊断":

    st.title("🧪 开裂与缺陷诊断")

    phenomenon = st.text_area(
        "本次开裂/缺陷现象",
        height=110,
    )

    options = [
        "未知",
        "明显异常",
        "偏高/偏快/强约束",
        "可疑",
        "一般/不确定",
        "较好/稳定",
        "偏低/偏慢/低约束",
    ]

    states = {}
    cols = st.columns(2)

    for i, variable in enumerate(VARIABLES):
        states[variable] = cols[i % 2].selectbox(
            variable,
            options,
            key=variable,
        )

    if st.button(
        "执行根因诊断",
        type="primary",
    ):

        result = diagnose(states)

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        evidence = search_papers(
            df,
            phenomenon
            + " crack thermal stress inclusion dislocation supersaturation",
            15,
            "相关池",
        )

        st.subheader(
            "关联文献证据"
        )

        evidence_table(
            evidence,
            height=420,
        )

        ok, _ = api_status()

        if ok:
            extra = "\n".join(
                f"{x['变量']}={x['当前状态']}，风险={x['风险']}"
                for _, x in result.iterrows()
            )

            try:
                with st.spinner(
                    "DeepSeek正在综合实验条件和文献证据……"
                ):
                    answer, sources = run_agent(
                        phenomenon
                        or "诊断KDP/DKDP开裂原因",
                        evidence,
                        "实验诊断",
                        extra,
                    )

                st.markdown(answer)
                sources_block(sources)

            except Exception as exc:
                st.error(
                    f"DeepSeek调用失败：{exc}"
                )


elif page == "🧫 对照实验设计":

    st.title("🧫 对照实验设计")

    selected = st.multiselect(
        "变量",
        list(VARIABLES),
        default=[
            "降温速率",
            "籽晶固定方式",
            "过饱和度",
        ],
    )

    baseline = st.text_area(
        "当前标准流程/基线"
    )

    if selected:

        matrix = experiment_matrix(
            selected,
            baseline,
        )

        st.dataframe(
            matrix,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "下载实验矩阵Excel",
            excel_bytes(
                matrix,
                "对照实验",
            ),
            "KDP_DKDP_对照实验设计.xlsx",
        )


elif page == "🧮 理论计算助手":

    st.title("🧮 理论计算助手")

    c1, c2 = st.columns(2)

    method = c1.selectbox(
        "计算类型",
        [
            "DFT/第一性原理",
            "分子动力学 MD",
            "有限元 FEA",
        ],
    )

    target = c1.selectbox(
        "对象",
        [
            "氢空位",
            "钾空位",
            "氧/磷酸根缺陷",
            "杂质/掺杂",
            "缺陷复合体",
            "包裹体附近应力",
            "加工亚表面损伤",
            "裂纹萌生",
            "热应力场",
            "籽晶/固定约束",
            "DKDP同位素效应",
        ],
    )

    software = c2.multiselect(
        "软件",
        [
            "Materials Studio",
            "Quantum ESPRESSO",
            "VASP",
            "Gaussian",
            "LAMMPS",
            "COMSOL",
            "ANSYS",
            "Python",
        ],
    )

    goal = c2.text_area(
        "研究目标"
    )

    evidence = search_papers(
        df,
        f"{method} {target} {goal}",
        18,
        "相关池",
    )

    evidence_table(
        evidence,
        height=420,
    )

    skeleton = {
        "DFT/第一性原理":
            "结构验证 → 超胞/k点/截断能收敛 → 缺陷/电荷态 → 优化 → 形成能 → TDOS/PDOS/电荷密度 → 光学性质 → 实验验证",

        "分子动力学 MD":
            "势函数验证 → 完整晶体基准 → 缺陷/热/加工工况 → 位错/裂纹演化 → 原子应力/能量 → 实验比较",

        "有限元 FEA":
            "各向异性参数 → 温度/浓度/夹持边界 → 网格收敛 → 主应力/应变能 → 危险区 → 裂纹位置验证",
    }

    st.info(
        skeleton[method]
    )

    if st.button(
        "AI生成完整计算方案",
        type="primary",
    ):
        ok, _ = api_status()

        if not ok:
            st.warning(
                "未配置DeepSeek。"
            )
        else:
            try:
                with st.spinner(
                    "DeepSeek正在生成计算路线……"
                ):
                    answer, sources = run_agent(
                        f"{method}; {target}; 软件={software}; 目标={goal}",
                        evidence,
                        "理论方案",
                    )

                st.markdown(answer)
                sources_block(sources)

            except Exception as exc:
                st.error(
                    f"DeepSeek调用失败：{exc}"
                )


elif page == "🕳️ 研究空白":

    st.title("🕳️ 研究空白")

    stats = topic_stats(df)

    st.dataframe(
        stats,
        use_container_width=True,
        hide_index=True,
    )

    st.plotly_chart(
        px.scatter(
            stats,
            x="总文献",
            y="近5年",
            size="S/A",
            color="DFT",
            hover_name="专题",
        ),
        use_container_width=True,
    )

    topic = st.selectbox(
        "深入分析",
        list(TOPICS),
    )

    evidence = topic_search(
        df,
        topic,
        25,
        "相关池",
    )

    if st.button(
        "AI识别可验证空白",
        type="primary",
    ):
        ok, _ = api_status()

        if not ok:
            st.warning(
                "未配置DeepSeek。"
            )
        else:
            try:
                with st.spinner(
                    "DeepSeek正在分析研究空白……"
                ):
                    answer, sources = run_agent(
                        f"围绕{topic}识别3–6个可验证研究空白，每个给出验证方案。",
                        evidence,
                        "研究空白",
                    )

                st.markdown(answer)
                sources_block(sources)

            except Exception as exc:
                st.error(
                    f"DeepSeek调用失败：{exc}"
                )


elif page == "🤖 AI科研智能体":

    @st.fragment
    def render_ai_agent():

        st.title("🤖 AI科研智能体")
        st.caption("默认自动检索本地文献与最新资料；回答会边生成边显示，不再长时间空等。")

        task = st.selectbox(
            "任务",
            [
                "自动判断",
                "文献问答",
                "多文献比较",
                "专题调研",
                "研究空白",
                "实验诊断",
                "理论方案",
                "报告生成",
            ],
        )

        question = st.text_area(
            "科研问题",
            height=130,
        )

        scope = st.selectbox(
            "证据范围",
            ["相关池", "S+A", "全库"],
        )

        n = st.slider(
            "本地证据文献数",
            6,
            20,
            12,
        )

        if st.button(
            "执行科研任务",
            type="primary",
        ):
            if not question.strip():
                st.warning("请输入问题。")
                return

            status = st.status(
                "正在启动科研分析…",
                expanded=True,
            )

            status.write("🔍 正在检索本地文献…")

            evidence = search_papers(
                df,
                question,
                n,
                scope,
            )

            status.write(
                f"✅ 本地检索完成：{len(evidence)} 篇候选证据"
            )

            if "_证据层级" in evidence.columns:
                counts = evidence["_证据层级"].value_counts().to_dict()
                status.write(
                    "📊 证据结构："
                    f"强直接 {counts.get('强直接证据',0)}；"
                    f"直接 {counts.get('直接主题证据',0)}；"
                    f"背景 {counts.get('背景/间接证据',0)}"
                )

            st.subheader("检索到的本地文献证据")
            evidence_table(
                evidence,
                height=430,
            )

            ok, _ = api_status()

            if not ok:
                status.update(
                    label="AI未连接，已完成离线检索",
                    state="complete",
                )
                st.markdown(
                    offline_summary(
                        evidence,
                        question,
                    )
                )
                return

            st.subheader("AI科研回答")

            answer_box = st.empty()
            answer = ""
            sources = []
            model_used = ""

            try:
                for event in stream_agent(
                    question,
                    evidence,
                    task,
                ):
                    event_type = event.get("type")

                    if event_type == "stage":
                        status.write(
                            "🌐 " + event.get("text", "")
                        )

                    elif event_type == "reasoning":
                        # 只显示状态，不展示模型私有思维链内容。
                        status.update(
                            label="🧠 DeepSeek正在深度分析证据…",
                            state="running",
                        )

                    elif event_type == "content":
                        answer += event.get("text", "")
                        answer_box.markdown(
                            answer + "\n\n▌"
                        )

                    elif event_type == "done":
                        sources = event.get("sources", [])
                        model_used = event.get("model", "")
                        status.update(
                            label=f"✅ 回答完成 · {model_used}",
                            state="complete",
                            expanded=False,
                        )

                    elif event_type == "error":
                        raise RuntimeError(
                            event.get("text", "AI调用失败")
                        )

                answer_box.markdown(answer)

                sources_block(sources)

                st.download_button(
                    "下载回答Word",
                    docx_bytes(
                        "科研智能体回答",
                        answer,
                        sources,
                    ),
                    "科研智能体回答.docx",
                )

            except Exception as exc:
                status.update(
                    label="AI调用失败",
                    state="error",
                )
                st.error(
                    f"DeepSeek调用失败：{exc}"
                )

    render_ai_agent()

elif page == "📝 报告中心":

    st.title("📝 报告中心")

    kind = st.selectbox(
        "类型",
        [
            "组会专题汇报",
            "专题文献调研",
            "开题方向论证",
            "理论计算方案总结",
            "开裂诊断报告",
        ],
    )

    topic = st.selectbox(
        "主题",
        list(TOPICS),
    )

    extra = st.text_area(
        "额外要求"
    )

    evidence = topic_search(
        df,
        topic,
        20,
        "相关池",
    )

    if st.button(
        "生成报告",
        type="primary",
    ):

        ok, _ = api_status()

        if not ok:

            st.markdown(
                offline_summary(
                    evidence,
                    topic,
                )
            )

        else:

            try:
                with st.spinner(
                    "DeepSeek正在生成报告……"
                ):

                    answer, sources = run_agent(
                        f"生成{kind}，主题={topic}。要求：{extra}",
                        evidence,
                        "报告生成",
                    )

                st.markdown(answer)
                sources_block(sources)

                st.download_button(
                    "下载Word",
                    docx_bytes(
                        topic + "-" + kind,
                        answer,
                        sources,
                    ),
                    topic + "_" + kind + ".docx",
                )

            except Exception as exc:
                st.error(
                    f"DeepSeek调用失败：{exc}"
                )


elif page == "🩺 数据审计":

    st.title("🩺 数据审计")

    c = st.columns(4)

    c[0].metric(
        "当前加载总记录",
        f"{len(df):,}",
    )

    c[1].metric(
        "相关池",
        f"{(df['V5相关池']=='KDP/DKDP相关池').sum():,}",
    )

    c[2].metric(
        "无摘要",
        int(
            (df["摘要"].str.strip() == "")
            .sum()
        ),
    )

    c[3].metric(
        "无DOI",
        int(
            (df["DOI"].str.strip() == "")
            .sum()
        ),
    )

    st.dataframe(
        df["V5推荐等级"]
        .value_counts()
        .rename_axis("等级")
        .reset_index(name="文献数"),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("""
- `当前加载总记录`：优先读取 Excel 的 `全部详细分类` / `全部去重`，代表完整去重库。
- `相关池`：只是标签，不删除其他记录。
- `S核心50 / A重点150 / B扩展800`：只是阅读优先级。
- 剩余相关文献仍在 `C 扩展/背景` 中，可继续检索。
""")
