
from __future__ import annotations

from typing import Any, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st


# 费用显示优先采用“用户 2026-08-17 DeepSeek 官方账单导出”反推的实际计费档位。
# 账单中可直接验证：
# - 13:00–14:00 Pro：未命中 4.5 元/M，输出 13.5 元/M
# - 14:00–18:00 Pro：命中 0.30 元/M，未命中 9 元/M，输出 27 元/M
# - 14:00–18:00 Flash：未命中 3 元/M，输出 9 元/M
#
# 因账单在 14:00 出现精确 2× 切换，这里按峰谷计价处理。
# Flash 谷时及部分缓存命中价格按同一 2× 结构推定；最终仍以官方账单为准。
ACCOUNT_PRICING = {
    "offpeak": {
        "flash": {
            "cache_hit_input": 0.12,
            "cache_miss_input": 1.50,
            "output": 4.50,
        },
        "pro": {
            "cache_hit_input": 0.15,
            "cache_miss_input": 4.50,
            "output": 13.50,
        },
    },
    "peak": {
        "flash": {
            "cache_hit_input": 0.24,
            "cache_miss_input": 3.00,
            "output": 9.00,
        },
        "pro": {
            "cache_hit_input": 0.30,
            "cache_miss_input": 9.00,
            "output": 27.00,
        },
    },
}


def _secret_float(name: str, default: float) -> float:
    try:
        return float(st.secrets.get(name, default))
    except Exception:
        return float(default)


def summarize_usage(model: str, usage: Any) -> Dict[str, Any]:
    u = _as_dict(usage)

    prompt = int(u.get("prompt_tokens") or 0)
    completion = int(u.get("completion_tokens") or 0)
    total = int(u.get("total_tokens") or (prompt + completion))

    hit = int(u.get("prompt_cache_hit_tokens") or 0)
    miss = int(u.get("prompt_cache_miss_tokens") or 0)

    # 某些兼容 SDK 可能把缓存字段放在 prompt_tokens_details 里。
    details = _as_dict(u.get("prompt_tokens_details"))
    if not hit:
        hit = int(
            details.get("cached_tokens")
            or details.get("cache_hit_tokens")
            or 0
        )

    # 若API没返回miss，则用 prompt-hit 做合理拆分。
    if not miss and prompt:
        miss = max(prompt - hit, 0)

    completion_details = _as_dict(u.get("completion_tokens_details"))
    reasoning = int(
        u.get("reasoning_tokens")
        or completion_details.get("reasoning_tokens")
        or 0
    )

    price = _pricing(model)

    input_hit_cost = hit / 1_000_000 * price["cache_hit_input"]
    input_miss_cost = miss / 1_000_000 * price["cache_miss_input"]
    output_cost = completion / 1_000_000 * price["output"]
    estimated_cost = input_hit_cost + input_miss_cost + output_cost

    return {
        "model": str(model or "DeepSeek"),
        "family": _model_family(model),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "cache_hit_tokens": hit,
        "cache_miss_tokens": miss,
        "reasoning_tokens": reasoning,
        "estimated_cny": float(estimated_cost),
        "input_hit_cost": float(input_hit_cost),
        "input_miss_cost": float(input_miss_cost),
        "output_cost": float(output_cost),
        "price": price,
        "billing_period": price.get("period", "offpeak"),
        "pricing_basis": "2026-08-17 DeepSeek账单校准",
    }


def record_deepseek_usage(model: str, usage: Any) -> Dict[str, Any]:
    summary = summarize_usage(model, usage)

    # 如果服务端没有返回任何 token，就不把它算进会话累计。
    if summary["total_tokens"] <= 0:
        st.session_state["_last_deepseek_usage"] = summary
        return summary

    st.session_state["_last_deepseek_usage"] = summary

    session = st.session_state.get(
        "_deepseek_session_usage",
        {
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cny": 0.0,
        },
    )

    session["requests"] += 1
    session["prompt_tokens"] += summary["prompt_tokens"]
    session["completion_tokens"] += summary["completion_tokens"]
    session["total_tokens"] += summary["total_tokens"]
    session["estimated_cny"] += summary["estimated_cny"]

    st.session_state["_deepseek_session_usage"] = session
    return summary


def get_last_deepseek_usage() -> Dict[str, Any]:
    return st.session_state.get("_last_deepseek_usage", {}) or {}


def get_session_deepseek_usage() -> Dict[str, Any]:
    return st.session_state.get("_deepseek_session_usage", {}) or {}


def render_deepseek_usage(usage: Dict[str, Any] | None = None):
    """
    在每次 DeepSeek 结果下方显示本次 token 和估算人民币费用。
    """
    usage = usage or get_last_deepseek_usage()
    if not usage or int(usage.get("total_tokens", 0)) <= 0:
        return

    session = get_session_deepseek_usage()

    st.markdown(
        """
        <div style="
            margin-top:14px;
            margin-bottom:4px;
            font-size:12px;
            font-weight:800;
            letter-spacing:.08em;
            color:#64748B;">
            DEEPSEEK API 用量
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "本次总 Tokens",
            f"{int(usage.get('total_tokens', 0)):,}",
        )

        c2.metric(
            "输入 / 输出",
            f"{int(usage.get('prompt_tokens', 0)):,} / "
            f"{int(usage.get('completion_tokens', 0)):,}",
        )

        c3.metric(
            "缓存命中",
            f"{int(usage.get('cache_hit_tokens', 0)):,}",
            help="缓存命中的输入 token 单价显著低于缓存未命中。",
        )

        c4.metric(
            "本次估算费用",
            f"¥{float(usage.get('estimated_cny', 0.0)):.4f}",
            help="根据本次API返回token和当前配置的DeepSeek人民币单价估算。",
        )

        model = usage.get("model", "DeepSeek")
        miss = int(usage.get("cache_miss_tokens", 0))
        reasoning = int(usage.get("reasoning_tokens", 0))

        period_cn = "峰时" if usage.get("billing_period") == "peak" else "谷时"
        details = (
            f"模型：**{model}**　｜　"
            f"计费档位：**{period_cn}（账单校准）**　｜　"
            f"缓存未命中：**{miss:,} tokens**"
        )
        if reasoning:
            details += f"　｜　思考 tokens：**{reasoning:,}**"

        st.caption(details)

        if session:
            st.caption(
                "当前浏览会话累计："
                f"{int(session.get('requests', 0))} 次 DeepSeek 请求 · "
                f"{int(session.get('total_tokens', 0)):,} tokens · "
                f"估算 ¥{float(session.get('estimated_cny', 0.0)):.4f}"
            )

        st.caption(
            "费用根据 2026-08-17 官方账单导出的实际 price 字段校准，并按北京时间峰/谷档估算；"
            "API 本身只返回 Tokens、不返回最终人民币扣费。最终金额仍以 DeepSeek 官方账单为准。"
        )
