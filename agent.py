
import re

import streamlit as st
from openai import OpenAI

from engine import compact_context
from web_research import research_web, source_links_markdown
from security import enforce_ai_quota, validate_user_text


SYSTEM = """
你是“KDP/DKDP晶体开裂与缺陷研究科研智能体”，服务于硕博研究。
默认综合：
[P#] 用户本地文献库；
[W#] 当前问题自动补充的外部学术/网页资料；
以及通用专业知识。

规则：
- 不捏造作者、DOI、URL或精确数值。
- 只有书目信息而没有摘要的外部结果，只用于定位论文，不能单独证明机理。
- 重要科研结论优先由论文、数据库、出版社或官方资料支持。
- 精确数值只有证据片段明确出现时才能引用，否则写“需回查原文确认”。
- 区分有来源支持的结论、综合判断和建议验证。
"""


TASK_GUIDANCE = {
    "文献问答": "直接回答问题，给主要机制、支持来源、限制和下一步。",
    "多文献比较": "比较对象、方法、条件、结论、证据强弱和差异原因。",
    "专题调研": "形成集中调研：问题→方法→共识→争议→代表工作→空白→建议。",
    "研究空白": "提出可验证研究空白，并说明已有工作、缺口、验证方案和价值。",
    "实验诊断": "输出根因排序、证据链、变量风险、对照实验、指标和判据。",
    "理论方案": "输出模型→结构/超胞→工况→方法→收敛→输出量→验证→风险。",
    "报告生成": "生成可直接用于组会、开题或阶段总结的报告。",
}


def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def api_status():
    key = _secret("DEEPSEEK_API_KEY")
    if not key:
        return False, "未连接"
    return True, "DeepSeek 智能加速"


def route_task(question):
    q = str(question or "")
    if any(k in q for k in ["比较","差异","区别","对比"]):
        return "多文献比较"
    if any(k in q for k in ["开裂","裂纹","诊断","原因","为什么裂"]):
        return "实验诊断"
    if any(k in q for k in ["DFT","第一性原理","VASP","QE","Quantum ESPRESSO","MD","分子动力学","有限元","COMSOL","ANSYS","计算方案"]):
        return "理论方案"
    if any(k in q for k in ["空白","创新点","研究方向","还能做什么"]):
        return "研究空白"
    if any(k in q for k in ["组会","报告","开题","汇报"]):
        return "报告生成"
    if any(k in q for k in ["综述","专题调研","调研"]):
        return "专题调研"
    return "文献问答"


def _profile(task, question):
    q = str(question or "")
    deep = (
        task in {"研究空白","理论方案"}
        or any(k in q for k in ["深入","非常详细","系统论证","最高质量","完整计算方案"])
    )
    if deep:
        return {
            "model": _secret("DEEPSEEK_MODEL", "deepseek-v4-pro"),
            "thinking": True,
        }
    return {
        "model": _secret("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash"),
        "thinking": False,
    }


def _prompt(question, evidence_df, task, extra, web_context, web_status):
    local_context, local_sources = compact_context(evidence_df)

    if "_证据层级" in evidence_df.columns:
        counts = evidence_df["_证据层级"].value_counts().to_dict()
        local_quality = (
            f"本地证据：强直接{counts.get('强直接证据',0)}篇；"
            f"直接主题{counts.get('直接主题证据',0)}篇；"
            f"背景{counts.get('背景/间接证据',0)}篇。"
        )
    else:
        local_quality = "本地文献未完成证据分层。"

    prompt = f"""
任务：{task}
问题：{question}
额外条件：{extra}

{local_quality}

外部检索状态：
Crossref={web_status.get('crossref')}
OpenAlex={web_status.get('openalex')}
Web={web_status.get('web')}

【本地文献】
{local_context}

【外部补充资料】
{web_context if web_context else "本次没有获得可用外部资料。"}

要求：
{TASK_GUIDANCE.get(task, TASK_GUIDANCE["文献问答"])}

回答时：
1. 直接解决问题，不介绍检索模式。
2. 重要结论尽量绑定[P#]/[W#]。
3. 综合判断要明确，不伪装成论文原结论。
4. 不编造精确数值、DOI或URL。
5. 科研决策/实验/计算问题给出可执行下一步。
"""
    return prompt, local_sources


def stream_agent(question, evidence_df, task="自动判断", extra=""):
    enforce_ai_quota()
    question = validate_user_text(question, "科研问题")
    extra = validate_user_text(extra, "额外条件")

    """
    事件流：
    stage     -> 页面进度提示
    reasoning -> 仅告诉页面“正在深度分析”，不展示模型私有思维链
    content   -> 最终答案逐段流式显示
    done      -> 来源等元数据
    """
    api_key = _secret("DEEPSEEK_API_KEY")
    if not api_key:
        yield {"type": "error", "text": "未配置DeepSeek API Key"}
        return

    if task == "自动判断":
        task = route_task(question)

    yield {"type": "stage", "text": "正在补充最新学术与网页资料…"}
    web_context, web_sources, web_status = research_web(question)

    yield {
        "type": "stage",
        "text": (
            "外部检索完成："
            f"Crossref {web_status.get('crossref')}；"
            f"网页 {web_status.get('web')}"
        ),
    }

    prompt, local_sources = _prompt(
        question,
        evidence_df,
        task,
        extra,
        web_context,
        web_status,
    )

    profile = _profile(task, question)
    model = profile["model"]

    yield {
        "type": "stage",
        "text": f"正在调用 {model} 分析证据…",
    }

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=60.0,
        max_retries=1,
    )

    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }

    if profile["thinking"]:
        kwargs["reasoning_effort"] = "high"
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    else:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        kwargs["temperature"] = 0.15

    max_tokens = _secret("AI_MAX_OUTPUT_TOKENS", 8000)
    try:
        kwargs["max_tokens"] = int(max_tokens)
    except Exception:
        pass

    response = client.chat.completions.create(**kwargs)

    reasoning_started = False

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        content = getattr(delta, "content", None)

        if reasoning and not reasoning_started:
            reasoning_started = True
            yield {
                "type": "reasoning",
                "text": "DeepSeek正在进行深度分析…",
            }

        if content:
            yield {
                "type": "content",
                "text": content,
            }

    source_md = source_links_markdown(web_sources)

    if source_md:
        yield {
            "type": "content",
            "text": source_md,
        }

    yield {
        "type": "done",
        "sources": local_sources,
        "model": model,
    }


def run_agent(question, evidence_df, task="自动判断", extra=""):
    """兼容其他模块的非流式调用。"""
    answer_parts = []
    sources = []

    for event in stream_agent(question, evidence_df, task, extra):
        if event["type"] == "content":
            answer_parts.append(event["text"])
        elif event["type"] == "done":
            sources = event.get("sources", [])
        elif event["type"] == "error":
            raise RuntimeError(event["text"])

    return "".join(answer_parts), sources
