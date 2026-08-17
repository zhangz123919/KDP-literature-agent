
from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI

from engine import TOPICS, load_data, search_papers, topic_search, topic_stats
from reports import docx_bytes, excel_bytes
from security import enforce_ai_quota, remaining_ai_calls, safe_error, validate_user_text
from ui import COLORS, metric_cards, page_header, plotly, section_title, soft_note
from usage_monitor import record_deepseek_usage, render_deepseek_usage
from web_research import research_web, source_links_markdown


SYSTEM = """
你是“KDP/DKDP晶体开裂与缺陷研究方向决策顾问”。

你的任务不是泛泛介绍KDP，而是基于用户已有的大规模文献数据库、代表性论文证据和最新外部资料，
帮助硕博研究者确定未来6–12个月可以真正推进的研究问题与研究课题。

必须遵守：
1. [P#] 是用户本地文献库证据；[W#] 是外部补充资料。
2. 不得捏造文献、DOI、实验结果、具体数值。
3. 只有书目信息而没有摘要的外部结果，只能用于“发现论文”，不能作为具体机理的直接证据。
4. 必须区分：
   - 已有较强证据的共识
   - 仍存在争议或证据不足的问题
   - 你基于证据提出的研究假设
5. 不要为了“创新”而硬造研究空白。研究空白必须能说明：
   已有人做了什么 → 还缺什么 → 为什么值得做 → 怎么验证。
6. 课题推荐必须兼顾科学价值、可验证性、工作量、实验/计算条件和毕业周期。
7. 具体题目建议要落到“研究对象 + 科学问题 + 方法 + 可验证结果”，不能只写大方向。
8. 对于每个推荐题目，必须给出风险和“如果做不出来怎么办”的备选路线。
"""


def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _clean(x):
    return "" if pd.isna(x) else re.sub(r"\s+", " ", str(x)).strip()


def _build_evidence_pack(
    df: pd.DataFrame,
    focus: str,
    per_topic: int = 5,
    max_total: int = 55,
) -> pd.DataFrame:
    """
    快速代表证据包：
    - 不再对15个专题逐一调用完整 search_papers（旧版最主要卡顿来源）
    - 直接利用预处理后的 _text 做专题真实命中
    - 每个专题在命中文献中按科研优先分/被引/年份选代表文献
    - 只有用户自定义重点问题再调用一次 search_papers
    """
    rel = df[df["V5相关池"] == "KDP/DKDP相关池"].copy()
    if rel.empty:
        return df.head(0).copy()

    pieces = []
    text_series = rel["_text"].fillna("").astype(str)

    for topic, terms in TOPICS.items():
        terms = [str(t).strip() for t in terms if str(t).strip()]
        if not terms:
            continue

        pattern = "|".join(re.escape(t) for t in terms)
        hit = text_series.str.contains(pattern, case=False, regex=True, na=False)
        d = rel.loc[hit].copy()

        if len(d):
            d = d.sort_values(
                ["V5科研优先分", "被引次数", "年份"],
                ascending=False,
            ).head(per_topic)
            d["_方向专题"] = topic
            pieces.append(d)

    if str(focus or "").strip():
        targeted = search_papers(df, focus, 14, "相关池").copy()
        if len(targeted):
            targeted["_方向专题"] = "用户重点问题"
            pieces.append(targeted)

    if not pieces:
        return df.head(0).copy()

    pack = pd.concat(pieces, axis=0)

    dedupe_key = (
        pack["DOI"].fillna("").astype(str).str.strip()
        .where(
            pack["DOI"].fillna("").astype(str).str.strip() != "",
            pack["题名"].astype(str),
        )
    )
    pack = pack.assign(_dedupe_key=dedupe_key).drop_duplicates("_dedupe_key")

    pack = pack.sort_values(
        ["V5科研优先分", "被引次数", "年份"],
        ascending=False,
    ).head(max_total)

    return pack.drop(columns=["_dedupe_key"], errors="ignore")

def _topic_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    stats = topic_stats(df).copy()
    stats["近5年占比"] = (
        stats["近5年"] / stats["总文献"].replace(0, np.nan) * 100
    ).fillna(0).round(1)

    stats["核心文献密度"] = (
        stats["S/A"] / stats["总文献"].replace(0, np.nan) * 100
    ).fillna(0).round(1)

    stats["DFT占比"] = (
        stats["DFT"] / stats["总文献"].replace(0, np.nan) * 100
    ).fillna(0).round(1)

    return stats


def _stats_text(stats: pd.DataFrame) -> str:
    lines = []
    for _, r in stats.sort_values("总文献", ascending=False).iterrows():
        lines.append(
            f"- {r['专题']}：总量{int(r['总文献'])}；"
            f"近5年{int(r['近5年'])}（{r['近5年占比']}%）；"
            f"S/A={int(r['S/A'])}；DFT={int(r['DFT'])}（{r['DFT占比']}%）"
        )
    return "\n".join(lines)


def _evidence_context(pack: pd.DataFrame, maxp: int = 48) -> Tuple[str, List[Dict]]:
    blocks = []
    sources = []

    for i, (_, r) in enumerate(pack.head(maxp).iterrows(), 1):
        topic = _clean(r.get("_方向专题", ""))
        blocks.append(
            f"[P{i}]\n"
            f"专题：{topic}\n"
            f"题名：{_clean(r.get('题名',''))}\n"
            f"年份：{r.get('年份','')}\n"
            f"期刊：{_clean(r.get('期刊',''))}\n"
            f"DOI：{_clean(r.get('DOI',''))}\n"
            f"等级：{_clean(r.get('V5推荐等级',''))}\n"
            f"分类：{_clean(r.get('详细二级分类',''))}\n"
            f"来源：{_clean(r.get('缺陷/应力来源',''))}\n"
            f"机制：{_clean(r.get('作用机制',''))}\n"
            f"后果：{_clean(r.get('宏观结果',''))}\n"
            f"方法：{_clean(r.get('_方法标签',''))}\n"
            f"摘要：{_clean(r.get('摘要',''))[:900]}\n"
            f"已有结论：{_clean(r.get('自动主要结论',''))[:420]}"
        )
        sources.append(
            {
                "编号": f"P{i}",
                "题名": _clean(r.get("题名", "")),
                "年份": r.get("年份", ""),
                "期刊": _clean(r.get("期刊", "")),
                "DOI": _clean(r.get("DOI", "")),
            }
        )

    return "\n\n".join(blocks), sources


def _make_landscape_figure(stats: pd.DataFrame):
    s = stats.sort_values("总文献", ascending=True)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=s["总文献"],
            y=s["专题"],
            orientation="h",
            name="全部相关文献",
            marker_color="#DCE4EF",
            hovertemplate="<b>%{y}</b><br>总量 %{x} 篇<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=s["近5年"],
            y=s["专题"],
            orientation="h",
            name="近五年",
            marker_color=COLORS["cyan"],
            hovertemplate="<b>%{y}</b><br>近五年 %{x} 篇<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="overlay",
        bargap=.28,
        xaxis_title="文献数",
        yaxis_title="",
        legend=dict(orientation="h", x=0, y=1.08),
    )

    return fig


def _make_method_gap_figure(stats: pd.DataFrame):
    s = stats.copy().sort_values("近5年占比", ascending=False)

    fig = go.Figure(
        go.Scatter(
            x=s["总文献"],
            y=s["近5年占比"],
            mode="markers+text",
            text=s["专题"],
            textposition="top center",
            marker=dict(
                size=np.clip(12 + s["S/A"].to_numpy() * .18, 14, 48),
                color=s["DFT占比"],
                colorscale=[
                    [0, "#D7E0EC"],
                    [.45, "#8C84E9"],
                    [1, "#20AFC0"],
                ],
                colorbar=dict(title="DFT占比 %"),
                line=dict(color="white", width=1),
                opacity=.92,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "总文献 %{x}<br>"
                "近五年占比 %{y:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title="证据规模（文献数）",
        yaxis_title="近五年占比（%）",
    )
    return fig



def _usage_dict(usage) -> dict:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
        "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", 0),
        "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", 0),
    }


def _estimate_rmb(model: str, usage) -> dict:
    """
    按 DeepSeek 官方 2026-08 公开价做前端估算。
    实际扣费以 DeepSeek 控制台账单为准。
    """
    u = _usage_dict(usage)
    hit = int(u.get("prompt_cache_hit_tokens") or 0)
    miss = int(u.get("prompt_cache_miss_tokens") or 0)
    prompt = int(u.get("prompt_tokens") or 0)
    completion = int(u.get("completion_tokens") or 0)

    # 某些SDK/响应若未拆分hit/miss，则保守按全部未命中估算
    if hit == 0 and miss == 0 and prompt:
        miss = prompt

    m = str(model or "").lower()
    if "flash" in m:
        hit_price, miss_price, out_price = 0.02, 1.0, 2.0
    else:
        hit_price, miss_price, out_price = 0.025, 3.0, 6.0

    cost = (
        hit / 1_000_000 * hit_price
        + miss / 1_000_000 * miss_price
        + completion / 1_000_000 * out_price
    )
    return {
        "cache_hit_tokens": hit,
        "cache_miss_tokens": miss,
        "completion_tokens": completion,
        "prompt_tokens": prompt,
        "total_tokens": int(u.get("total_tokens") or (prompt + completion)),
        "estimated_cny": cost,
    }


def stream_direction_report(
    df: pd.DataFrame,
    focus: str,
    constraints: str,
    horizon: str,
    theory_weight: str,
    quick: bool = False,
):
    enforce_ai_quota()

    focus = validate_user_text(focus, "重点问题")
    constraints = validate_user_text(constraints, "现实约束")

    yield {"type": "stage", "text": "正在扫描全部 KDP/DKDP 相关文献的专题结构…"}

    stats = _topic_snapshot(df)

    if quick:
        pack = _build_evidence_pack(df, focus, per_topic=2, max_total=30)
        local_context, local_sources = _evidence_context(pack, maxp=24)
    else:
        pack = _build_evidence_pack(df, focus, per_topic=5, max_total=55)
        local_context, local_sources = _evidence_context(pack, maxp=48)

    yield {
        "type": "stage",
        "text": f"已构建跨专题代表证据包：{len(pack)} 篇；正在补充最新外部资料…",
    }

    web_query = (
        "KDP DKDP crystal cracking defects growth thermal stress inclusion "
        "hydrogen vacancy laser damage first principles review research gap 2022 2026 "
        + str(focus or "")
    )
    web_context, web_sources, web_status = research_web(web_query)

    yield {
        "type": "stage",
        "text": (
            "外部资料补充完成："
            f"Crossref {web_status.get('crossref')}；Web {web_status.get('web')}"
        ),
    }

    quick_instruction = (
        "【快速测试模式】请保留完整12部分结构，但每部分压缩表达；"
        "候选课题给3个、优先论文给10篇，重点验证检索、证据引用、方向判断和流式输出是否正常。"
        if quick else
        "【正式报告模式】请充分展开分析，形成可用于与导师讨论和后续选题的完整方向决策报告。"
    )

    prompt = f"""
{quick_instruction}

请生成一份可以直接用于“本人 + 导师共同确定研究课题”的
《KDP/DKDP晶体缺陷、开裂与损伤研究方向决策型文献调研报告》。

【研究者重点关注】
{focus or "尚未限定，请从全景调研中识别最值得深入的问题"}

【现实约束】
{constraints or "暂无额外约束，请按硕博阶段个人科研可执行性进行判断"}

【希望覆盖的研究周期】
{horizon}

【理论计算权重偏好】
{theory_weight}

====================
一、全库专题统计
====================
{_stats_text(stats)}

注意：
上述统计来自用户KDP/DKDP相关文献池的全库扫描。
它用于判断领域规模、近期活跃度和方法覆盖；
但“研究空白”不能仅靠文献数量自动得出。

====================
二、跨专题代表性本地证据
====================
{local_context}

====================
三、外部最新补充资料
====================
{web_context if web_context else "本次外部检索未获得可用资料。"}

请严格按以下结构生成报告：

# 0. 一页式结论摘要
要求导师在3分钟内看懂：
- 这个领域现在主要研究什么
- 哪些方向已经比较成熟
- 哪些问题仍没有真正解决
- 最值得本研究者继续做的1个主方向 + 2个备选方向
- 为什么这样选

# 1. 调研范围、数据基础与可信度
说明：
- 本地数据库规模和专题扫描方法
- 代表证据是如何选出来的
- 当前调研能够回答什么、不能回答什么
- 哪些关键结论仍需回查全文

# 2. KDP/DKDP领域整体研究版图
不要按论文逐篇罗列。
按“研究问题”组织：
- 晶体生长与快速生长
- 本征点缺陷/氢空位
- 杂质与掺杂
- 包裹体与散射中心
- 位错与晶格应变
- 表面/亚表面加工损伤
- 热应力、残余应力与开裂
- 激光损伤/LIDT
- DKDP氘化与同位素
- DFT/MD/有限元
- Raman/FTIR/XRD/AFM/光热等表征

每个主题都回答：
已有共识是什么？
代表方法是什么？
与开裂/缺陷的关系是什么？
主要不足是什么？

# 3. “缺陷来源 → 局部机制 → 宏观后果”科学链条
至少建立3–6条证据链，例如：
生长/包裹体 → 应力集中 → 裂纹萌生；
氢空位/缺陷态 → 局域吸收 → LIDT下降。
每条链必须区分“有证据支持”和“仍是研究假设”。

# 4. 方法学版图
分别评价：
- 水溶液生长实验
- 缺陷/光学/应力表征
- DFT
- MD
- 有限元
- 多尺度耦合
说明哪些方法已经成熟，哪些组合最值得用于下一阶段。

# 5. 目前真正存在的科学问题与争议
至少提出5–10个。
不能写泛泛的“机理仍不清楚”。
必须具体到可实验或可计算验证的问题。

# 6. 研究空白
每个研究空白按：
已有工作 → 缺的证据 → 为什么重要 → 如何验证 → 失败风险
进行说明。
严禁仅因为“论文少”就判定为空白。

# 7. 候选研究课题矩阵
提出4–6个具体课题。
每个课题必须包含：
- 可直接用于开题的中文题目
- 核心科学问题
- 创新点
- 实验路线
- 理论计算路线
- 关键表征
- 6–12个月可得到什么结果
- 难度：低/中/高
- 风险
- 备选路线
- 支持证据 [P#]/[W#]

并用表格给出：
科学价值、创新潜力、可行性、理论计算价值、实验可验证性、毕业风险（各1–5级）。

# 8. 最推荐的主课题
只选1个。
必须给出：
- 为什么优先于其他候选题
- 第一阶段要验证的核心假设
- 最小可行实验
- 最小可行计算
- 3个月内的“成败判据”
- 如果失败如何转向备选课题

# 9. 备选课题
给出2个，并说明什么情况下切换。

# 10. 未来3个月 / 6个月 / 12个月研究路线
明确：
文献 → 实验 → 表征 → 计算 → 迭代 → 输出成果。

# 11. 应优先精读的核心论文
从当前证据中选20–30篇最关键的论文。
优先给出 [P#]/[W#]、题名、年份、DOI及“为什么必须读”。

# 12. 导师讨论清单
列出10个下一次与导师讨论时最值得问清楚的问题，
让导师可以直接对研究课题做取舍。

科研写作要求：
- 中文
- 学术、严谨、清楚
- 不要写宣传性语言
- 不要把模型推断冒充文献事实
- 关键判断尽量绑定[P#]/[W#]
- 如果某个方向证据不足，直接写“当前证据不足”
"""

    client = OpenAI(
        api_key=_secret("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        timeout=90.0,
        max_retries=1,
    )

    # 快速测试的目标是“验证流程”，不应付出正式研究报告的模型成本。
    # 正式报告才使用 Pro + 深度思考。
    if quick:
        model = _secret("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash")
        thinking_enabled = False
    else:
        model = _secret("DEEPSEEK_MODEL", "deepseek-v4-pro")
        thinking_enabled = True

    yield {
        "type": "stage",
        "text": (
            f"正在使用 {model} "
            + ("（快速非思考模式）" if quick else "（深度思考模式）")
            + "进行跨专题综合与课题决策分析…"
        ),
    }

    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        # DeepSeek官方支持在流式最后返回整次请求usage
        "stream_options": {"include_usage": True},
        "extra_body": {
            "thinking": {"type": "enabled" if thinking_enabled else "disabled"}
        },
    }

    if thinking_enabled:
        kwargs["reasoning_effort"] = "high"

    max_tokens = _secret("AI_MAX_OUTPUT_TOKENS", 10000)
    try:
        max_tokens = int(max_tokens)
        # 快速测试只验证方向判断与证据链，不生成超长正文
        kwargs["max_tokens"] = min(max_tokens, 2600) if quick else max_tokens
    except Exception:
        kwargs["max_tokens"] = 2600 if quick else 10000

    response = client.chat.completions.create(**kwargs)

    reasoning_seen = False
    final_usage = None

    for chunk in response:
        # include_usage=True 时，最后一个chunk通常没有choices但带usage
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            final_usage = usage

        if not getattr(chunk, "choices", None):
            continue

        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        content = getattr(delta, "content", None)

        if reasoning and not reasoning_seen:
            reasoning_seen = True
            yield {
                "type": "reasoning",
                "text": "正在比较不同方向的证据成熟度、研究空白与可执行性…",
            }

        if content:
            yield {"type": "content", "text": content}

    source_md = source_links_markdown(web_sources)
    if source_md:
        yield {"type": "content", "text": source_md}

    usage_summary = record_deepseek_usage(model, final_usage)

    yield {
        "type": "done",
        "local_sources": local_sources,
        "evidence_pack": pack,
        "stats": stats,
        "model": model,
        "usage": usage_summary,
    }


def direction_review_page():
    df = load_data()
    if df.empty:
        st.error("缺少文献数据库。")
        return

    page_header(
        "全景文献调研与研究方向决策",
        "不是只找几篇论文，而是扫描整个KDP/DKDP相关文献池，形成领域版图、科学问题、研究空白、候选课题和6–12个月研究路线。",
        "RESEARCH DIRECTION REVIEW",
    )

    rel = df[df["V5相关池"] == "KDP/DKDP相关池"]
    stats = _topic_snapshot(df)
    max_year = int(rel["年份"].max()) if len(rel) else 0

    metric_cards(
        [
            {
                "label": "全库去重文献",
                "value": f"{len(df):,}",
                "note": "完整数据库",
                "accent": COLORS["primary"],
            },
            {
                "label": "KDP/DKDP相关池",
                "value": f"{len(rel):,}",
                "note": "全景扫描对象",
                "accent": COLORS["cyan"],
            },
            {
                "label": "研究专题",
                "value": len(stats),
                "note": "跨主题扫描",
                "accent": COLORS["violet"],
            },
            {
                "label": "数据库最新年份",
                "value": max_year or "—",
                "note": "用于判断近期活跃度",
                "accent": COLORS["teal"],
            },
        ]
    )

    section = st.segmented_control(
        "方向决策工作区",
        ["领域全景", "代表证据与候选方向", "生成完整方向决策报告"],
        default="领域全景",
        selection_mode="single",
        label_visibility="collapsed",
        key="direction_workspace",
    )

    # 重要：旧版使用 st.tabs，Streamlit 会把三个页签内容全部执行。
    # 即使用户只打开“生成报告”，后台仍会绘图并对15个专题逐一检索，
    # 因此页面会长时间变灰。现在只运行当前选中的一个工作区。
    if section == "领域全景":
        left, right = st.columns([1.1, 1], gap="large")

        with left:
            section_title(
                "专题证据规模",
                "灰色代表长期积累，青色代表近五年；先看真实研究规模和近期活跃度",
            )
            fig = _make_landscape_figure(stats)
            plotly(fig, height=650, key="direction_landscape")

        with right:
            section_title(
                "研究机会地图",
                "横轴=证据规模，纵轴=近五年占比，节点颜色=DFT覆盖；用于发现值得深入核查的方向",
            )
            fig = _make_method_gap_figure(stats)
            plotly(fig, height=650, key="direction_gap")

        section_title(
            "全库专题统计",
            "这是定量扫描结果，不等于研究空白结论；真正选题仍要结合代表论文和实验条件",
        )
        st.dataframe(
            stats.sort_values("总文献", ascending=False),
            width="stretch",
            height=470,
            hide_index=True,
        )
        return

    if section == "代表证据与候选方向":
        focus_preview = st.text_input(
            "先输入你最关心的问题（可选）",
            placeholder="例如：KDP生长/降温过程开裂；氢空位与吸收；包裹体作为裂纹萌生源",
            key="direction_preview_focus",
        )

        with st.spinner("正在构建跨专题代表证据包…"):
            pack = _build_evidence_pack(
                df,
                focus_preview,
                per_topic=4,
                max_total=45,
            )

        section_title(
            "跨专题代表证据包",
            "每个专题选代表工作，再加入你的重点问题；不是按单一关键词随机抓取",
        )

        show_cols = [
            "_方向专题",
            "题名",
            "年份",
            "V5推荐等级",
            "详细二级分类",
            "_方法标签",
            "自动研究问题",
            "自动主要结论",
            "DOI",
        ]
        show_cols = [c for c in show_cols if c in pack.columns]

        st.dataframe(
            pack[show_cols],
            width="stretch",
            height=590,
            hide_index=True,
        )

        st.download_button(
            "导出代表证据包 Excel",
            excel_bytes(pack[show_cols], "方向决策证据包"),
            "KDP_DKDP_研究方向决策证据包.xlsx",
        )

        soft_note(
            "这里展示的是“用于做方向判断的代表证据”，完整5928篇相关文献仍保留在文献中心。"
            "最终方向决策报告会同时使用全库统计、代表证据和外部最新资料。"
        )
        return

    # 只在真正进入“生成报告”工作区时运行这一段。
    with st.container(border=True):
        focus = st.text_area(
            "希望重点解决的问题",
            height=100,
            placeholder=(
                "可以留空让系统从全景中判断。也可以写："
                "希望围绕KDP/DKDP水溶液生长后的开裂问题，重点关注降温、籽晶、包裹体、位错和理论计算。"
            ),
        )

        c1, c2 = st.columns(2)

        horizon = c1.selectbox(
            "希望形成的研究周期",
            ["6个月可形成阶段成果", "12个月形成系统研究", "18个月以上长期课题"],
            index=1,
        )

        theory_weight = c2.selectbox(
            "理论计算权重",
            ["较低：实验为主", "中等：实验 + DFT/FEA协同", "较高：适当提高理论计算权重"],
            index=2,
        )

        constraints = st.text_area(
            "现实约束 / 已有条件",
            height=100,
            placeholder=(
                "例如：当前实验数据有限；希望课题能先从文献+计算启动；"
                "后续可开展晶体生长、Raman/XRD/显微、DFT或有限元等。"
            ),
        )

        run_mode = st.radio(
            "运行模式",
            ["快速测试", "正式报告"],
            horizontal=True,
            index=0,
            help="第一次建议先用快速测试验证整条链路；确认正常后再生成正式长报告。",
        )

    soft_note(
        f"当前会话剩余AI调用次数：{remaining_ai_calls()}。"
        + (
            " 快速测试会减少代表证据数量并压缩输出，用于验证功能是否正常。"
            if run_mode == "快速测试"
            else " 正式方向报告会比普通问答更长，请把真正想与导师讨论的约束一次写清楚。"
        )
    )

    button_label = (
        "快速测试：生成精简方向决策报告"
        if run_mode == "快速测试"
        else "生成《KDP/DKDP研究方向决策型文献调研报告》"
    )

    if not st.button(button_label, type="primary"):
        return

    status = st.status(
        "正在启动全景文献调研…",
        expanded=True,
    )

    answer = ""
    answer_box = st.empty()
    local_sources = []
    evidence_pack = None
    report_stats = None
    model = ""
    api_usage = {}

    try:
        for event in stream_direction_report(
            df,
            focus,
            constraints,
            horizon,
            theory_weight,
            quick=(run_mode == "快速测试"),
        ):
            tp = event.get("type")

            if tp == "stage":
                status.write(event.get("text", ""))

            elif tp == "reasoning":
                status.update(
                    label="正在比较研究方向、研究空白与可执行性…",
                    state="running",
                )

            elif tp == "content":
                answer += event.get("text", "")
                answer_box.markdown(answer + "\n\n▌")

            elif tp == "done":
                local_sources = event.get("local_sources", [])
                evidence_pack = event.get("evidence_pack")
                report_stats = event.get("stats")
                model = event.get("model", "")
                api_usage = event.get("usage") or {}
                cost_text = ""
                if api_usage:
                    cost_text = f" · 估算 ¥{api_usage.get('estimated_cny', 0):.4f}"
                status.update(
                    label=f"方向决策报告完成 · {model}{cost_text}",
                    state="complete",
                    expanded=False,
                )

        answer_box.markdown(answer)

    except PermissionError as exc:
        status.update(label="当前无法调用AI", state="error")
        st.warning(str(exc))
        return

    except Exception as exc:
        status.update(label="报告生成失败", state="error")
        safe_error(
            "报告生成过程中出现异常，详细错误已记录。请稍后重试。",
            exc,
        )
        return

    if api_usage:
        render_deepseek_usage(api_usage)

    section_title(
        "报告使用建议",
        "建议先由本人标记“同意/不同意/待核实”，再与导师共同确定最终课题，而不是把AI推荐直接当成结论。",
    )

    st.download_button(
        "导出方向决策报告 Word",
        docx_bytes(
            "KDP_DKDP_研究方向决策型文献调研报告",
            answer,
            local_sources,
        ),
        "KDP_DKDP_研究方向决策型文献调研报告.docx",
    )

    if evidence_pack is not None and len(evidence_pack):
        st.download_button(
            "导出本次证据包 Excel",
            excel_bytes(evidence_pack, "方向决策证据包"),
            "KDP_DKDP_方向决策证据包.xlsx",
        )
