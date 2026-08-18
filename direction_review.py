
from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI

from engine import CORE_TOPICS, TOPICS, load_data, material_scope, search_papers, topic_search, topic_stats
from reports import docx_bytes, excel_bytes
from research_memory import add_item, build_project_context, get_active_project, project_context_strip
from security import enforce_ai_quota, guard_duplicate_ai_request, remaining_ai_calls, safe_error, validate_user_text
from ui import COLORS, insight_strip, metric_cards, page_header, plotly, section_title, soft_note
from usage_monitor import record_deepseek_usage, render_deepseek_usage
from web_research import research_web, source_links_markdown


SYSTEM = """
你是“KDP晶体缺陷与大尺寸生长研究方向决策顾问”。

你的任务不是泛泛介绍KDP，而是基于用户已有的大规模文献数据库、代表性论文证据和最新外部资料，
帮助一名即将进入研二的硕士研究生，在约12个月有效科研周期内确定可以真正推进、能够形成实验—理论闭环的研究问题与研究课题。

必须遵守：
1. [P#] 是用户本地文献库证据；[W#] 是外部补充资料。
2. 不得捏造文献、DOI、实验结果、具体数值。
3. 只有书目信息而没有摘要的外部结果，只能用于“发现论文”，不能作为具体机理的直接证据。
4. 必须区分：
   - 已有较强证据的共识
   - 仍存在争议或证据不足的问题
   - 基于证据提出、仍需验证的研究假设
5. 不要为了“创新”而硬造研究空白。研究空白必须能说明：
   已有人做了什么 → 还缺什么证据 → 为什么值得做 → 怎么验证。
6. 默认研究对象必须是 KDP。除非用户明确提出氘化/同位素比较，DKDP只能作为对照或扩展证据。
7. 默认以“大尺寸KDP水溶液生长”为当前主线，优先关注：
   尺寸效应 → 流场/传质/表面过饱和度 → 生长界面稳定性 → 白纹/相位跃变、串丝/液态包裹体 → 热应力/开裂 → 工艺优化。
8. 用户是硕士研究生，不允许把课题规划成博士级“大而全”方案。正式推荐应控制为：1个主课题 + 2个备选课题；优先形成一条可在12个月左右完成的主线。
9. 实验与理论计算必须一一对应：实验告诉计算“算什么”，计算必须给出可被后续实验验证的预测；不得把实验和计算写成两条互不相关的平行线。
10. 理论方法按科学问题调用：CFD优先解决流场/传质/表面过饱和度；FEA解决温度场/应力/开裂；DFT/MD只有在明确的原子/微观问题出现时再加入，不得为了“计算丰富”而全部列为必做。
11. 推荐课题必须兼顾科学价值、样品与仪器可获得性、计算学习成本、实验周期、论文产出和毕业风险。
12. 每个主/备选课题都必须给出“3个月成败判据”和失败后的转向条件。
"""


DEFAULT_MASTER_FOCUS = (
    "围绕大尺寸KDP晶体生长中的典型缺陷开展研究，优先聚焦白纹/相位跃变与串丝/液态包裹体中的1—2类关键问题，"
    "研究晶体由小尺寸向大尺寸生长过程中流场、传质、局部过饱和度和生长界面稳定性的变化及其与缺陷形成之间的关系。"
    "希望通过已有样品表征、小—中—大尺寸对比、CFD流场—传质计算和针对性对照实验，建立“实验现象—理论解释—实验验证—工艺优化”的研究闭环；"
    "开裂与热—力问题根据前期结果作为第二阶段拓展。"
)

DEFAULT_MASTER_CONSTRAINTS = (
    "本人为硕士研究生，即将进入研二阶段，后续有效科研周期有限，需要在约12个月内形成较完整、可验证的阶段性成果，并为论文撰写、投稿和毕业工作预留时间。"
    "研究方案应避免战线过长，优先选择与现有大尺寸KDP生长实际问题联系紧密、样品和测试条件可获得、能够形成实验—理论闭环的内容。"
    "当前已完成KDP相关文献的初步调研与筛选，但系统实验数据积累仍有限；实验室具备大尺寸KDP晶体生长及样品获取条件。"
    "后续优先聚焦1条主线和1—2类典型缺陷，不要求同时覆盖全部缺陷。理论方面优先采用能直接解释实验现象的CFD和必要的热—力有限元，DFT/MD仅在出现明确微观科学问题时作为补充。"
    "研究目标以“问题明确、实验可做、计算可验证、结果可发表、毕业风险可控”为原则。"
)


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
    rel = material_scope(df, "KDP主线")
    if rel.empty:
        return df.head(0).copy()

    pieces = []
    text_series = rel["_text"].fillna("").astype(str)

    for topic, terms in CORE_TOPICS.items():
        terms = [str(t).strip() for t in terms if str(t).strip()]
        if not terms:
            continue

        pattern = "|".join(re.escape(t) for t in terms)
        hit = text_series.str.contains(pattern, case=False, regex=True, na=False)
        d = rel.loc[hit].copy()

        if len(d):
            d = d.sort_values(
                ["V5核心排序分", "证据完整度分", "V5科研优先分", "被引次数", "年份"],
                ascending=False,
            ).head(per_topic)
            d["_方向专题"] = topic
            pieces.append(d)

    if str(focus or "").strip():
        targeted = search_papers(df, focus, 14, "KDP主线").copy()
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
        ["V5核心排序分", "证据完整度分", "V5科研优先分", "被引次数", "年份"],
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
            f"核心角色：{_clean(r.get('核心证据层级','—'))}\n"
            f"证据完整度：{r.get('证据完整度分','')} / 100（{_clean(r.get('证据完整度状态',''))}）\n"
            f"证据角色：{_clean(r.get('证据角色',''))}\n"
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
            name="长期积累",
            marker=dict(color="#DCE5EE", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>全部相关文献 %{x} 篇<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=s["近5年"],
            y=s["专题"],
            orientation="h",
            name="近五年",
            marker=dict(color=COLORS["primary"], line=dict(width=0)),
            text=s["近5年"].where(s["近5年"] > 0, ""),
            textposition="outside",
            textfont=dict(size=10, color="#52677F"),
            hovertemplate="<b>%{y}</b><br>近五年 %{x} 篇<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="overlay",
        bargap=.32,
        xaxis_title="文献数",
        yaxis_title="",
        legend=dict(orientation="h", x=0, y=1.07),
    )

    return fig


def _make_method_gap_figure(stats: pd.DataFrame):
    s = stats.copy().sort_values("近五年占比", ascending=False)
    if s.empty:
        return go.Figure()

    x_mid = float(s["总文献"].median())
    y_mid = float(s["近五年占比"].median())

    # 只给最值得辨认的点常驻标签，避免像默认散点图一样满屏文字。
    label_score = (
        s["近五年占比"].rank(pct=True)
        + s["S/A"].rank(pct=True)
        + s["总文献"].rank(pct=True) * .45
    )
    top_label_idx = set(label_score.nlargest(min(7, len(s))).index)
    labels = [row["专题"] if idx in top_label_idx else "" for idx, row in s.iterrows()]

    fig = go.Figure()

    # 四象限的极淡背景，只作为读图辅助。
    x_max = max(float(s["总文献"].max()) * 1.08, x_mid + 1)
    y_max = max(float(s["近五年占比"].max()) * 1.12, y_mid + 1)

    fig.add_shape(
        type="rect", x0=x_mid, x1=x_max, y0=y_mid, y1=y_max,
        fillcolor="rgba(19,89,166,.045)", line_width=0, layer="below"
    )

    fig.add_vline(x=x_mid, line_width=1, line_dash="dot", line_color="rgba(91,109,130,.45)")
    fig.add_hline(y=y_mid, line_width=1, line_dash="dot", line_color="rgba(91,109,130,.45)")

    fig.add_trace(
        go.Scatter(
            x=s["总文献"],
            y=s["近五年占比"],
            mode="markers+text",
            text=labels,
            textposition="top center",
            textfont=dict(size=10, color="#314B67"),
            customdata=np.stack(
                [s["专题"], s["S/A"], s["DFT"], s["核心文献密度"]],
                axis=-1,
            ),
            marker=dict(
                size=np.clip(12 + s["S/A"].to_numpy() * .16, 14, 42),
                color=s["DFT占比"],
                colorscale=[
                    [0, "#D6E2EE"],
                    [.52, "#4E82BE"],
                    [1, "#0E8F96"],
                ],
                colorbar=dict(
                    title=dict(text="DFT占比", font=dict(size=10)),
                    thickness=9,
                    len=.62,
                    outlinewidth=0,
                ),
                line=dict(color="#FFFFFF", width=1.2),
                opacity=.93,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "证据规模 %{x} 篇<br>"
                "近五年占比 %{y:.1f}%<br>"
                "S/A %{customdata[1]} 篇<br>"
                "DFT %{customdata[2]} 篇"
                "<extra></extra>"
            ),
        )
    )

    fig.add_annotation(
        x=x_max, y=y_max,
        text="证据较厚 · 近期更活跃",
        showarrow=False,
        xanchor="right", yanchor="top",
        font=dict(size=10, color="#1359A6"),
    )

    fig.update_layout(
        xaxis_title="证据规模（文献数）",
        yaxis_title="近五年占比（%）",
        showlegend=False,
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



def _merge_usage(total: dict, current: dict | None) -> dict:
    """合并分段请求的 DeepSeek 用量，供页面显示整份报告的总消耗。"""
    current = current or {}
    if not current:
        return total or {}

    if not total:
        total = dict(current)
        total["requests"] = 1
        return total

    for key in [
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cache_hit_tokens",
        "cache_miss_tokens",
        "reasoning_tokens",
    ]:
        total[key] = int(total.get(key, 0) or 0) + int(current.get(key, 0) or 0)

    for key in ["estimated_cny", "input_hit_cost", "input_miss_cost", "output_cost"]:
        total[key] = float(total.get(key, 0.0) or 0.0) + float(current.get(key, 0.0) or 0.0)

    total["requests"] = int(total.get("requests", 1) or 1) + 1
    # 价格档位、模型名称沿用最新一次请求；正式报告各段通常使用同一模型。
    for key in ["model", "family", "price", "billing_period", "pricing_basis"]:
        if current.get(key) is not None:
            total[key] = current.get(key)
    return total


def _stream_deepseek_call(
    client,
    model: str,
    messages: list,
    max_tokens: int,
    thinking_enabled: bool,
):
    """
    单次 DeepSeek 流式请求。
    - 不把网络中断直接抛到页面层；返回已生成文本 + 错误，便于自动续写。
    - 记录 finish_reason 和 usage。
    """
    kwargs = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "extra_body": {
            "thinking": {"type": "enabled" if thinking_enabled else "disabled"}
        },
        "max_tokens": int(max_tokens),
    }
    if thinking_enabled:
        kwargs["reasoning_effort"] = "high"

    text_parts = []
    final_usage = None
    finish_reason = None
    reasoning_seen = False
    error = None

    try:
        response = client.chat.completions.create(**kwargs)
        for chunk in response:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                final_usage = usage

            choices = getattr(chunk, "choices", None)
            if not choices:
                continue

            choice = choices[0]
            fr = getattr(choice, "finish_reason", None)
            if fr:
                finish_reason = fr

            delta = choice.delta
            reasoning = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)

            if reasoning and not reasoning_seen:
                reasoning_seen = True
                yield {
                    "type": "reasoning",
                    "text": "正在比较证据成熟度、研究空白、实验可行性与毕业风险…",
                }

            if content:
                text_parts.append(content)
                yield {"type": "content", "text": content}

    except Exception as exc:
        error = exc

    try:
        usage_summary = record_deepseek_usage(model, final_usage)
    except Exception:
        # 用量统计不能影响正文生成。
        usage_summary = {}
    return {
        "text": "".join(text_parts),
        "usage": usage_summary,
        "finish_reason": finish_reason,
        "error": error,
    }


def _formal_report_segments() -> list[tuple[str, str, str]]:
    """把正式报告拆成4段，避免一次超长流式输出在尾部失败。"""
    return [
        (
            "A",
            "研究问题与证据版图",
            """
请只生成以下四部分，不要提前写后面的章节：
# 0. 一页式结论摘要
导师3分钟内能看懂：当前KDP大尺寸生长缺陷领域的关键问题、最推荐主方向、2个备选方向及选择理由。

# 1. 调研范围、数据基础与可信度
说明本地数据库、代表证据、外部补充资料的作用；指出哪些结论仍需回查全文。

# 2. 面向大尺寸KDP的研究版图
以“尺寸放大 → 局部场 → 生长界面 → 缺陷 → 热力/开裂”为主轴，重点讨论：
小/中/大尺寸尺度效应；流场/传质/表面过饱和度；白纹/相位跃变；串丝/液态包裹体；位错/应变；热应力/开裂。
点缺陷、激光损伤、加工损伤只作为必要支线，不要抢占主线。

# 3. 证据支持的机制链与待验证假设
建立3—5条“工艺/尺度 → 局部机制 → 缺陷/后果”链条；逐条标明“已有证据”“合理推断”“待验证”。
""",
        ),
        (
            "B",
            "方法、科学问题与研究空白",
            """
请只生成以下三部分：
# 4. 实验—理论协同方法学版图
必须把每类实验与对应计算配对：宏观/显微/结构/光学/应力表征 ↔ CFD/FEA/必要时DFT或MD。
明确哪些是当前硕士阶段“必做”、哪些是“可选扩展”。

# 5. 当前最值得验证的科学问题
提出5—8个具体、可以通过实验或计算证伪的问题，优先围绕大尺寸尺度效应、白纹/相位跃变、串丝/包裹体、开裂。

# 6. 真正可成立的研究空白
每个空白按：已有工作 → 缺的关键证据 → 为什么重要 → 最小验证方法 → 失败风险。
不要把“论文少”直接当研究空白。
""",
        ),
        (
            "C",
            "硕士主课题与备选路线",
            """
请只生成以下三部分：
# 7. 硕士候选课题矩阵
只提出3个课题：1个优先候选 + 2个备选。每个必须包含：
中文题目、核心科学问题、创新点、实验路线、计算路线、关键测试、3个月成败判据、6—12个月可形成的结果、难度、主要风险、转向条件、支持证据[P#]/[W#]。
并给出简洁评分表：科学价值、创新潜力、可行性、实验可验证性、计算价值、毕业风险（1—5级）。

# 8. 最推荐主课题
只选1个，说明为什么最适合“即将研二的硕士研究生”，以及最小可行实验、最小可行计算、第一篇阶段论文最可能来自哪里。

# 9. 两个备选课题与切换条件
明确什么结果出现时应该从主课题切换，避免到研三才发现主线不可做。
""",
        ),
        (
            "D",
            "执行计划、核心文献与导师讨论",
            """
请只生成以下三部分：
# 10. 两周 / 3个月 / 6个月 / 12个月执行路线
写成真正可执行的时间表。必须体现：文献收口 → 历史样品/生长记录 → 缺陷地图 → 表征 → CFD/FEA → 对照实验 → 模型修正 → 论文输出。

# 11. 优先精读论文清单
从现有证据中选15—20篇最关键论文；给出[P#]/[W#]、题名、年份、DOI（若有）和“为什么现在必须读”。优先2022—2026与大尺寸、流场传质、白纹/串丝、热应力直接相关的工作；经典基础论文可少量保留。

# 12. 导师讨论清单
列出8个下一次与导师必须确认的问题，重点确认：主缺陷选哪一个、现有样品/历史数据、可用表征设备、是否能做尺寸对照、CFD/FEA优先级、第一阶段成果判据。

最后用一个不超过200字的“建议结论”收尾。
""",
        ),
    ]


def _common_direction_context(
    stats_text: str,
    local_context: str,
    web_context: str,
    focus: str,
    constraints: str,
    project_context: str,
    horizon: str,
    theory_weight: str,
) -> str:
    return f"""
请生成《大尺寸KDP晶体缺陷研究方向决策报告》的指定章节。

【研究者重点关注】
{focus}

【现实约束】
{constraints}

【当前研究项目记忆】
{project_context if project_context else "当前没有额外项目记忆。"}

【研究周期】
{horizon}

【理论计算权重】
{theory_weight}

====================
全库专题统计
====================
{stats_text}

====================
本地代表性证据
====================
{local_context}

====================
外部补充资料
====================
{web_context if web_context else "本次外部检索未获得可用资料。"}

写作规则：
- 中文，学术、严谨、直接；不要宣传性语言。
- 关键判断尽量绑定[P#]/[W#]。
- 本地证据与外部资料不能支持的内容，必须写“当前证据不足”或明确标记为研究假设。
- KDP为绝对主线；DKDP只在同位素对照确有价值时出现。
- 所有推荐都必须考虑“研二硕士、约12个月有效周期”的现实约束。
- 实验与计算必须互相验证，不得平行堆砌。
"""



def _segment_required_sections(seg_id: str) -> list[str]:
    """正式报告每段必须出现的章节号；用于防止流式连接提前结束却被误判为完成。"""
    return {
        "A": ["0", "1", "2", "3"],
        "B": ["4", "5", "6"],
        "C": ["7", "8", "9"],
        "D": ["10", "11", "12"],
    }.get(seg_id, [])


def _segment_is_complete(seg_id: str, text: str) -> bool:
    """不仅看 finish_reason，还检查本段要求的章节是否真的都生成出来。"""
    if not text or not text.strip():
        return False
    for no in _segment_required_sections(seg_id):
        # 接受 '# 0.' / '## 0 ' / '0. 标题' / '0、标题' 等常见Markdown写法。
        pat = rf"(?m)^\\s*(?:#{{1,4}}\\s*)?{re.escape(no)}(?:\\.|、|：|:|\\s)"
        if not re.search(pat, text):
            return False
    return True


def _missing_segment_sections(seg_id: str, text: str) -> list[str]:
    missing = []
    for no in _segment_required_sections(seg_id):
        pat = rf"(?m)^\\s*(?:#{{1,4}}\\s*)?{re.escape(no)}(?:\\.|、|：|:|\\s)"
        if not re.search(pat, text or ""):
            missing.append(no)
    return missing


def stream_direction_report(
    df: pd.DataFrame,
    focus: str,
    constraints: str,
    horizon: str,
    theory_weight: str,
    quick: bool = False,
    skip_segments: set | None = None,
):
    """
    稳定版方向报告生成器。

    正式模式：4段独立生成 + 单段自动续写/重试 + 失败保留已完成段。
    快速模式：单次短报告，用于低成本验证链路。
    """
    enforce_ai_quota()

    focus = validate_user_text(focus, "重点问题")
    constraints = validate_user_text(constraints, "现实约束")
    project_context = build_project_context(for_external_ai=True)
    resume_mode = skip_segments is not None
    if not resume_mode:
        guard_duplicate_ai_request(
            f"direction-v2|{focus}|{constraints}|{horizon}|{theory_weight}|{quick}",
            window_seconds=25,
        )

    yield {"type": "stage", "text": "正在扫描KDP主研究文献，并构建大尺寸生长缺陷证据包…"}
    stats = _topic_snapshot(df)

    if quick:
        pack = _build_evidence_pack(df, focus, per_topic=2, max_total=28)
        local_context, local_sources = _evidence_context(pack, maxp=22)
    else:
        pack = _build_evidence_pack(df, focus, per_topic=4, max_total=46)
        local_context, local_sources = _evidence_context(pack, maxp=40)

    yield {
        "type": "stage",
        "text": f"已构建代表证据包：{len(pack)}篇；正在补充2022—2026大尺寸KDP相关外部资料…",
    }

    web_query = (
        "KDP KH2PO4 large size crystal growth scale effect hydrodynamics mass transfer "
        "surface supersaturation growth interface growth striation phase jump white striation "
        "hair inclusion liquid inclusion thermal stress cracking CFD FEA 2022 2023 2024 2025 2026 "
        + str(focus or "")
    )
    try:
        web_context, web_sources, web_status = research_web(web_query)
    except Exception:
        web_context, web_sources = "", []
        web_status = {"crossref": "失败", "web": "失败"}
        yield {
            "type": "warning",
            "text": "外部补充检索暂时失败，将继续基于本地KDP证据库生成报告。",
        }

    yield {
        "type": "stage",
        "text": (
            "外部资料补充完成："
            f"Crossref {web_status.get('crossref')}；Web {web_status.get('web')}。"
        ),
    }

    if quick:
        model = _secret("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash")
        thinking_enabled = False
    else:
        model = _secret("DEEPSEEK_MODEL", "deepseek-v4-pro")
        # 正式长报告以“完整、稳定输出”为优先。证据扫描与选题结构已经由程序完成，
        # 这里关闭深度思考，避免 reasoning_content 占用大量输出预算并提高长流中断概率。
        thinking_enabled = False

    # 比旧版90秒更宽裕；仍可在Secrets里覆盖。
    timeout_value = _secret("DIRECTION_API_TIMEOUT", 180)
    try:
        timeout_value = min(max(float(timeout_value), 90.0), 300.0)
    except Exception:
        timeout_value = 180.0

    client = OpenAI(
        api_key=_secret("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        timeout=timeout_value,
        max_retries=1,
    )

    yield {
        "type": "metadata",
        "local_sources": local_sources,
        "evidence_pack": pack,
        "stats": stats,
        "model": model,
    }

    common = _common_direction_context(
        _stats_text(stats),
        local_context,
        web_context,
        focus,
        constraints,
        project_context,
        horizon,
        theory_weight,
    )

    total_usage = {}
    segment_finish_reasons = {}

    if quick:
        quick_prompt = common + """

【快速测试】
请用较短篇幅生成一个完整的导师讨论版报告，包含：
1. 3分钟摘要；
2. 当前最值得做的3个科学问题；
3. 1个主课题 + 2个备选；
4. 实验—理论闭环；
5. 两周/3个月/6个月/12个月计划；
6. 10篇优先论文；
7. 6个导师讨论问题。
"""
        result = yield from _stream_deepseek_call(
            client,
            model,
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": quick_prompt},
            ],
            2800,
            thinking_enabled,
        )
        total_usage = _merge_usage(total_usage, result.get("usage"))
        if result.get("error"):
            yield {
                "type": "failed",
                "text": "快速报告流式连接中断。已生成内容已经保留。",
                "segment": "Q",
                "model": model,
                "usage": total_usage,
            }
            return
        segment_finish_reasons["Q"] = result.get("finish_reason")

    else:
        skip_segments = set(skip_segments or set())
        try:
            segment_max = int(_secret("DIRECTION_SEGMENT_MAX_TOKENS", 7600))
            segment_max = min(max(segment_max, 5200), 12000)
        except Exception:
            segment_max = 7600

        for seg_id, seg_title, seg_instruction in _formal_report_segments():
            if seg_id in skip_segments:
                yield {
                    "type": "stage",
                    "text": f"已保留第{seg_id}段《{seg_title}》，跳过重复生成。",
                }
                continue

            yield {
                "type": "segment_start",
                "segment": seg_id,
                "title": seg_title,
                "text": f"正在生成第{seg_id}段：{seg_title}…",
            }

            base_user = common + "\n\n" + seg_instruction
            segment_text = ""
            continuation_count = 0
            transport_retry_count = 0
            segment_ok = False

            while True:
                if segment_text:
                    messages = [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": base_user},
                        {"role": "assistant", "content": segment_text},
                        {
                            "role": "user",
                            "content": (
                                "上一轮在本段中途结束。请严格从最后一句之后继续，只补齐尚未完成的章节。"
                                f"本段完整时必须包含章节：{', '.join(_segment_required_sections(seg_id))}。"
                                "不要重写已经出现的章节标题、表格或段落；不要从本段开头重新开始。"
                            ),
                        },
                    ]
                else:
                    messages = [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": base_user},
                    ]

                result = yield from _stream_deepseek_call(
                    client,
                    model,
                    messages,
                    segment_max,
                    thinking_enabled,
                )
                new_text = result.get("text", "") or ""
                segment_text += new_text
                total_usage = _merge_usage(total_usage, result.get("usage"))
                finish_reason = result.get("finish_reason")
                error = result.get("error")

                if error is not None:
                    if segment_text.strip() and continuation_count < 4:
                        continuation_count += 1
                        yield {
                            "type": "warning",
                            "text": (
                                f"第{seg_id}段流式连接在已生成部分内容后中断，"
                                f"正在自动从中断处续写（{continuation_count}/4）…"
                            ),
                        }
                        continue

                    if not segment_text.strip() and transport_retry_count < 3:
                        transport_retry_count += 1
                        yield {
                            "type": "warning",
                            "text": (
                                f"第{seg_id}段连接未开始输出，正在自动重试"
                                f"（{transport_retry_count}/3）…"
                            ),
                        }
                        continue

                    yield {
                        "type": "failed",
                        "text": (
                            f"第{seg_id}段《{seg_title}》连续重试后仍未完成。"
                            "前面已经完整生成的段落已保留，可直接点击“继续生成未完成部分”。"
                        ),
                        "segment": seg_id,
                        "model": model,
                        "usage": total_usage,
                    }
                    return

                # 不能再把 finish_reason=None 直接当“正常完成”。
                # 流式连接若提前断开，SDK有时可能只留下部分正文；必须同时做章节完整性校验。
                complete_now = _segment_is_complete(seg_id, segment_text)
                missing_sections = _missing_segment_sections(seg_id, segment_text)

                if finish_reason == "stop" and complete_now:
                    segment_finish_reasons[seg_id] = "stop"
                    segment_ok = True
                    break

                if finish_reason in ("length", None, "insufficient_system_resource") or not complete_now:
                    if continuation_count < 4:
                        continuation_count += 1
                        reason_text = {
                            "length": "达到单次输出上限",
                            None: "流提前结束且未收到完整结束标志",
                            "insufficient_system_resource": "服务端推理资源临时不足",
                        }.get(finish_reason, "本段章节尚未完整")
                        miss = "、".join(missing_sections) if missing_sections else "正文尾部"
                        yield {
                            "type": "warning",
                            "text": (
                                f"第{seg_id}段{reason_text}，当前仍缺少章节 {miss}；"
                                f"正在自动续写（{continuation_count}/4），无需手动重新点击。"
                            ),
                        }
                        continue

                    yield {
                        "type": "failed",
                        "text": (
                            f"第{seg_id}段自动续写多次后仍不完整（缺少："
                            f"{'、'.join(missing_sections) if missing_sections else '正文尾部'}）。"
                            "前面完整段落已保留，可稍后从本段继续。"
                        ),
                        "segment": seg_id,
                        "model": model,
                        "usage": total_usage,
                    }
                    return

                if finish_reason not in ("stop",):
                    yield {
                        "type": "failed",
                        "text": (
                            f"第{seg_id}段以状态 {finish_reason} 停止，且未通过完整性校验。"
                            "已完成段落已保留。"
                        ),
                        "segment": seg_id,
                        "model": model,
                        "usage": total_usage,
                    }
                    return

            if segment_ok:
                yield {
                    "type": "segment_done",
                    "segment": seg_id,
                    "title": seg_title,
                    "text": f"第{seg_id}段《{seg_title}》完成。",
                }

    # 外部来源格式化不能再让整篇报告在最后一步判定失败。
    try:
        source_md = source_links_markdown(web_sources)
    except Exception:
        source_md = ""
        yield {
            "type": "warning",
            "text": "报告正文已完成，但外部来源链接格式化失败；不会影响正文和Word导出。",
        }

    if source_md:
        yield {"type": "content", "text": "\n\n" + source_md}

    yield {
        "type": "done",
        "local_sources": local_sources,
        "evidence_pack": pack,
        "stats": stats,
        "model": model,
        "usage": total_usage,
        "finish_reason": segment_finish_reasons,
        "truncated": False,
    }


def direction_review_page():
    df = load_data()
    if df.empty:
        st.error("缺少文献数据库。")
        return

    page_header(
        "全景文献调研与研究方向决策",
        "基于KDP主研究文献池，系统分析研究主题、核心证据、方法演化与潜在研究空白，并形成候选课题、优先方向及6–12个月研究路线。",
        "RESEARCH DIRECTION REVIEW",
    )

    project_context_strip()

    rel = material_scope(df, "KDP主线")
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
                "label": "KDP主研究池",
                "value": f"{len(rel):,}",
                "note": "默认全景扫描对象",
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

    valid = stats[stats["总文献"] > 0].copy()
    if len(valid):
        # 首页方向卡不再被“文献数量最多”自动带回点缺陷旧主线。
        # 优先展示当前大尺寸KDP研究真正需要的三个方向；如果旧数据库没有对应专题，再回退到统计最强项。
        def _row_for(topic_name: str):
            hit = valid[valid["专题"] == topic_name]
            return hit.iloc[0] if len(hit) else None

        scale_row = _row_for("大尺寸/尺度效应")
        field_row = _row_for("流场/传质/表面过饱和度")

        defect_candidates = valid[valid["专题"].isin([
            "白纹/生长条纹",
            "串丝/发丝状包裹体",
            "晶体开裂",
        ])].copy()
        defect_row = None
        if len(defect_candidates):
            defect_row = defect_candidates.sort_values(
                ["近5年占比", "S/A", "总文献"], ascending=False
            ).iloc[0]

        if scale_row is None:
            scale_row = valid.sort_values(["近5年占比", "近5年"], ascending=False).iloc[0]
        if field_row is None:
            field_row = valid.sort_values(["总文献", "S/A"], ascending=False).iloc[0]
        if defect_row is None:
            defect_row = valid.sort_values(["S/A", "近5年占比"], ascending=False).iloc[0]

        insight_strip(
            [
                {
                    "kicker": "SCALE EFFECT",
                    "title": scale_row["专题"],
                    "note": f"证据 {int(scale_row['总文献'])} 篇 · 近五年 {scale_row['近5年占比']:.1f}%",
                    "accent": COLORS["primary"],
                },
                {
                    "kicker": "LOCAL FIELD",
                    "title": field_row["专题"],
                    "note": f"证据 {int(field_row['总文献'])} 篇 · S/A {int(field_row['S/A'])} 篇",
                    "accent": COLORS["cyan"],
                },
                {
                    "kicker": "DEFECT MAINLINE",
                    "title": defect_row["专题"],
                    "note": f"近五年 {int(defect_row['近5年'])} 篇 · 核心文献 {int(defect_row['S/A'])} 篇",
                    "accent": COLORS["orange"],
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
                "浅灰表示长期积累，国科蓝表示近五年；用来观察不同专题的证据厚度与近期动量",
            )
            fig = _make_landscape_figure(stats)
            plotly(fig, height=650, key="direction_landscape")

        with right:
            section_title(
                "研究机会地图",
                "横轴看证据厚度，纵轴看近期动量；节点大小反映核心文献，颜色反映DFT覆盖",
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
            "KDP_研究方向决策证据包.xlsx",
        )

        soft_note(
            "这里展示的是“用于做方向判断的代表证据”，完整KDP主研究文献仍保留在文献中心。"
            "最终方向决策报告会同时使用全库统计、代表证据和外部最新资料。"
        )
        return

    # 只在真正进入“生成报告”工作区时运行这一段。
    with st.container(border=True):
        active_project = get_active_project()
        project_question = str(active_project.get("question", "") or "").strip()

        focus = st.text_area(
            "希望重点解决的问题",
            value=project_question or DEFAULT_MASTER_FOCUS,
            height=145,
            help="建议只围绕1条硕士主线写清楚，不要把所有KDP缺陷一次性塞进课题。",
        )

        c1, c2 = st.columns(2)

        horizon = c1.selectbox(
            "希望形成的研究周期",
            ["6个月可形成阶段成果", "12个月形成系统研究", "18个月以上长期课题"],
            index=1,
        )

        theory_weight = c2.selectbox(
            "理论计算权重",
            [
                "较低：实验为主",
                "中等：实验主线 + CFD/FEA协同",
                "较高：实验—理论闭环，优先CFD/FEA，DFT/MD按需",
            ],
            index=2,
        )

        constraints = st.text_area(
            "现实约束 / 已有条件",
            value=DEFAULT_MASTER_CONSTRAINTS,
            height=170,
            help="这里已经按“即将研二的硕士研究生”写入默认约束，可根据实验室实际条件继续补充。",
        )

        run_mode = st.radio(
            "运行模式",
            ["快速测试", "正式报告"],
            horizontal=True,
            index=1,
            help=(
                "点击一次后会自动连续完成A—D全部内容；程序会在后台分段以提高稳定性，"
                "但不需要你逐段点击。只有多次自动重试仍失败时才会出现恢复入口。"
            ),
        )

    soft_note(
        f"当前会话剩余AI调用次数：{remaining_ai_calls()}。"
        + (
            " 快速测试用于低成本确认链路。"
            if run_mode == "快速测试"
            else " 正式报告采用4段生成 + 自动续写 + 失败保留，适合直接形成导师讨论版材料。"
        )
    )

    saved = st.session_state.get("_direction_report_resume") or {}
    saved_incomplete = bool(saved and not saved.get("complete"))

    do_resume = False
    if saved_incomplete and run_mode == "正式报告":
        with st.container(border=True):
            st.markdown("**检测到上一次未完成的正式报告**")
            done_text = "、".join(saved.get("completed_segments", [])) or "暂无完整段"
            st.caption(
                f"已完整保留段落：{done_text}。继续生成时会从下一未完成段开始，不会把整篇报告重新跑一遍。"
            )
            do_resume = st.button(
                "继续生成未完成部分",
                type="primary",
                key="resume_direction_report",
            )

    button_label = (
        "快速测试：生成精简方向报告"
        if run_mode == "快速测试"
        else "一键生成完整《大尺寸KDP晶体缺陷研究方向决策报告》"
    )

    # 有未完成正式报告时，不再同时显示“重新生成”大按钮，避免用户误点后清空恢复点、从A段重跑。
    if saved_incomplete and run_mode == "正式报告":
        do_new = False
        with st.expander("需要放弃旧报告并从头生成？", expanded=False):
            st.caption("只有当你确实想换研究问题/约束条件时才使用。")
            if st.button("清除未完成报告", key="clear_direction_report"):
                st.session_state.pop("_direction_report_resume", None)
                st.rerun()
    else:
        do_new = st.button(button_label, type="primary", key="new_direction_report")

    if not do_new and not do_resume:
        return

    if do_resume:
        # 恢复时使用上次报告的参数，避免用户修改输入后造成前后段逻辑不一致。
        focus_run = saved.get("focus", focus)
        constraints_run = saved.get("constraints", constraints)
        horizon_run = saved.get("horizon", horizon)
        theory_weight_run = saved.get("theory_weight", theory_weight)
        completed_segments = set(saved.get("completed_segments", []))
        answer = saved.get("stable_answer", "") or ""
    else:
        focus_run = focus
        constraints_run = constraints
        horizon_run = horizon
        theory_weight_run = theory_weight
        completed_segments = set()
        answer = ""
        st.session_state["_direction_report_resume"] = {
            "complete": False,
            "focus": focus_run,
            "constraints": constraints_run,
            "horizon": horizon_run,
            "theory_weight": theory_weight_run,
            "completed_segments": [],
            "stable_answer": "",
        }

    status = st.status(
        "正在启动KDP研究方向报告生成…",
        expanded=True,
    )

    answer_box = st.empty()
    if answer:
        answer_box.markdown(answer + "\n\n▌")

    local_sources = []
    evidence_pack = None
    report_stats = None
    model = ""
    api_usage = {}
    generation_failed = False
    current_segment = None

    try:
        for event in stream_direction_report(
            df,
            focus_run,
            constraints_run,
            horizon_run,
            theory_weight_run,
            quick=(run_mode == "快速测试"),
            skip_segments=completed_segments if do_resume else None,
        ):
            tp = event.get("type")

            if tp == "stage":
                status.write(event.get("text", ""))

            elif tp == "segment_start":
                current_segment = event.get("segment")
                status.write(event.get("text", ""))

            elif tp == "segment_done":
                seg = event.get("segment")
                if seg and seg not in completed_segments:
                    completed_segments.add(seg)
                status.write(event.get("text", ""))
                # 只有完整段落才进入稳定恢复点。
                resume_state = st.session_state.get("_direction_report_resume") or {}
                resume_state.update(
                    {
                        "complete": False,
                        "focus": focus_run,
                        "constraints": constraints_run,
                        "horizon": horizon_run,
                        "theory_weight": theory_weight_run,
                        "completed_segments": sorted(completed_segments),
                        "stable_answer": answer,
                    }
                )
                st.session_state["_direction_report_resume"] = resume_state

            elif tp == "warning":
                status.write("提示：" + event.get("text", ""))

            elif tp == "reasoning":
                status.update(
                    label="正在比较研究方向、证据成熟度与硕士阶段可执行性…",
                    state="running",
                )

            elif tp == "metadata":
                local_sources = event.get("local_sources", [])
                evidence_pack = event.get("evidence_pack")
                report_stats = event.get("stats")
                model = event.get("model", "")

            elif tp == "content":
                answer += event.get("text", "")
                answer_box.markdown(answer + "\n\n▌")

            elif tp == "failed":
                generation_failed = True
                model = event.get("model", model)
                api_usage = event.get("usage") or api_usage
                current_segment = event.get("segment", current_segment)
                status.update(
                    label="本次连接未完全结束，但已完成内容已保留",
                    state="error",
                    expanded=True,
                )
                status.write(event.get("text", ""))

            elif tp == "done":
                local_sources = event.get("local_sources", local_sources)
                evidence_pack = event.get("evidence_pack", evidence_pack)
                report_stats = event.get("stats", report_stats)
                model = event.get("model", model)
                api_usage = event.get("usage") or api_usage
                status.update(
                    label=(
                        f"方向决策报告完成 · {model}"
                        + (f" · 估算 ¥{api_usage.get('estimated_cny', 0):.4f}" if api_usage else "")
                    ),
                    state="complete",
                    expanded=False,
                )

        answer_box.markdown(answer)

    except PermissionError as exc:
        status.update(label="当前无法调用AI", state="error")
        st.warning(str(exc))
        return

    except Exception as exc:
        generation_failed = True
        status.update(label="报告生成出现异常，已保留当前内容", state="error")
        safe_error(
            "本次生成遇到未预期异常，但已经生成的内容不会丢失。可以先导出，再点击“继续生成未完成部分”。",
            exc,
        )

    if generation_failed:
        # 失败时，恢复点仍停在最后一个完整段，避免续跑时重复半截内容。
        resume_state = st.session_state.get("_direction_report_resume") or {}
        resume_state.update(
            {
                "complete": False,
                "focus": focus_run,
                "constraints": constraints_run,
                "horizon": horizon_run,
                "theory_weight": theory_weight_run,
                "completed_segments": sorted(completed_segments),
                "stable_answer": resume_state.get("stable_answer", ""),
                "failed_segment": current_segment,
            }
        )
        st.session_state["_direction_report_resume"] = resume_state
        st.warning(
            "本次不是“整篇作废”。已经完整完成的段落已保存为恢复点；"
            "重新进入本页后点击“继续生成未完成部分”即可从未完成段继续。"
        )
    else:
        # 快速模式或正式模式正常完成。
        st.session_state["_direction_report_resume"] = {
            "complete": True,
            "focus": focus_run,
            "constraints": constraints_run,
            "horizon": horizon_run,
            "theory_weight": theory_weight_run,
            "completed_segments": sorted(completed_segments),
            "stable_answer": answer,
        }

    if api_usage:
        render_deepseek_usage(api_usage)

    section_title(
        "报告使用建议",
        "先标记“同意 / 不同意 / 待核实”，再与导师共同确定主课题。AI负责整合证据和规划，不代替导师对实验条件与课题边界的最终判断。",
    )

    if answer:
        st.download_button(
            "导出方向决策报告 Word" if not generation_failed else "导出当前已生成部分 Word",
            docx_bytes(
                "大尺寸KDP晶体缺陷研究方向决策报告",
                answer,
                local_sources,
            ),
            "KDP_大尺寸晶体缺陷研究方向决策报告.docx"
            if not generation_failed
            else "KDP_研究方向报告_已保留部分.docx",
        )

    if evidence_pack is not None and len(evidence_pack):
        st.download_button(
            "导出本次证据包 Excel",
            excel_bytes(evidence_pack, "方向决策证据包"),
            "KDP_方向决策证据包.xlsx",
        )

    if answer and not generation_failed:
        if st.button("保存本次方向报告到当前研究项目"):
            add_item(
                "direction_decision",
                "大尺寸KDP研究方向决策报告",
                answer[:1800],
                {
                    "focus": focus_run,
                    "constraints": constraints_run,
                    "horizon": horizon_run,
                    "theory_weight": theory_weight_run,
                    "model": model,
                    "full_report": answer,
                },
                "研究方向决策",
                "待导师审核",
            )
            st.success("已保存到研究项目工作区，后续实验设计、理论计算与AI助手可以读取本次方向决策。")

