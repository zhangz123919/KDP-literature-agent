
import re

import streamlit as st
from openai import OpenAI

from engine import compact_context
from web_research import research_web, source_links_markdown


SYSTEM = """
你是“KDP/DKDP晶体开裂与缺陷研究科研智能体”，服务于硕博研究。

你默认拥有三类知识来源：
1. [P#]：用户现有KDP/DKDP文献数据库中的证据；
2. [W#]：当前问题触发的最新外部资料检索结果，包括学术元数据与网页资料；
3. 你的通用专业知识与综合推理。

回答时不要把这三类来源混为一谈。

科研证据规则：
1. 用户没有要求“只依据本地文献库”时，应综合本地文献、最新外部资料和通用专业知识回答。
2. [P#] 中的摘要/结论可作为本地文献证据。
3. [W#] 如果只有书目信息而没有摘要，只能用于“发现/定位论文”，不能单独证明具体机理或精确数值。
4. 普通网页搜索摘要属于辅助资料；重要科研结论优先由论文、期刊、出版社、数据库、软件官方文档等高质量来源支持。
5. 不得捏造作者、DOI、波长、形成能、能级位置、温度、浓度、阈值、百分比等信息。
6. 精确数值只有在提供的证据文本中明确出现时才能引用；否则写“需回查原文确认”。
7. 必须区分：
   【有来源支持的结论】
   【综合推断】
   【建议验证】
8. 如果本地文献库没有直接证据，但外部资料有可靠证据，可以正常回答，并明确引用 [W#]。
9. 如果所有检索资料都不足，可基于专业知识给出解释，但必须明确标成“专业推断/待验证”，不能伪装成文献结论。
10. 优先按：
   缺陷/变量来源
   → 局部结构/电子态/应力
   → 吸收/散射/应力集中
   → 开裂或激光损伤
   → 检测与控制
   组织科研问题。
"""


TASK_GUIDANCE = {
    "文献问答": "直接回答问题；给出主要机制、支持来源、分歧/限制和下一步验证。",
    "多文献比较": "比较研究对象、方法、条件、关键结论、证据强弱、差异原因和可复现价值。",
    "专题调研": "形成集中型调研：问题→方法谱系→共同结论→争议→代表工作→空白→建议。",
    "研究空白": "提出可验证研究空白；每个空白说明已有工作、缺口、验证方案和价值。",
    "实验诊断": "输出根因排序、证据链、变量风险、最小对照实验、观测指标和判据。",
    "理论方案": "输出模型→结构/超胞→缺陷/工况→方法→收敛→输出量→验证→风险。",
    "报告生成": "生成可直接用于组会、开题或阶段总结的紧凑报告。",
}


def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def api_status():
    key = _secret("DEEPSEEK_API_KEY")
    model = _secret("DEEPSEEK_MODEL", "deepseek-v4-pro")
    return bool(key), model


def route_task(question):
    q = str(question or "")

    if any(k in q for k in ["比较", "差异", "区别", "对比"]):
        return "多文献比较"

    if any(k in q for k in ["开裂", "裂纹", "诊断", "原因", "为什么裂"]):
        return "实验诊断"

    if any(k in q for k in [
        "DFT", "第一性原理", "VASP", "QE",
        "Quantum ESPRESSO", "MD", "分子动力学",
        "有限元", "COMSOL", "ANSYS", "计算方案",
    ]):
        return "理论方案"

    if any(k in q for k in ["空白", "创新点", "研究方向", "还能做什么"]):
        return "研究空白"

    if any(k in q for k in ["组会", "报告", "开题", "汇报"]):
        return "报告生成"

    if any(k in q for k in ["综述", "专题调研", "调研"]):
        return "专题调研"

    return "文献问答"


def _extract_numbers(text):
    patterns = [
        r"\b\d+(?:\.\d+)?\s*nm\b",
        r"\b\d+(?:\.\d+)?\s*eV\b",
        r"\b\d+(?:\.\d+)?\s*K\b",
        r"\b\d+(?:\.\d+)?\s*°C\b",
        r"\b\d+(?:\.\d+)?\s*%\b",
        r"\b\d+(?:\.\d+)?\s*J/cm2\b",
        r"\b\d+(?:\.\d+)?\s*J/cm\^2\b",
        r"\b\d+(?:\.\d+)?\s*MPa\b",
        r"\b\d+(?:\.\d+)?\s*GPa\b",
    ]

    found = []

    for pattern in patterns:
        found.extend(
            re.findall(
                pattern,
                str(text or ""),
                flags=re.IGNORECASE,
            )
        )

    return list(dict.fromkeys(found))[:120]


def _numeric_guard(local_context, web_context):
    nums = _extract_numbers(
        str(local_context)
        + "\n"
        + str(web_context)
    )

    if not nums:
        return (
            "当前提供给你的证据片段中没有可靠提取到精确数值。"
            "不要主动生成新的波长、能量、形成能、温度、浓度、阈值等数字；"
            "需要时写“需回查原文确认”。"
        )

    return (
        "证据片段中实际出现过的数值表达包括："
        + "、".join(nums)
        + "。回答中的精确数值应限于证据明确支持的范围；"
        "其他数字必须标注“需回查原文确认”。"
    )


def _local_quality(evidence_df):
    if "_证据层级" not in evidence_df.columns:
        return "本地文献未完成证据分层。"

    counts = evidence_df["_证据层级"].value_counts().to_dict()

    return (
        f"本地证据结构："
        f"强直接 {counts.get('强直接证据',0)} 篇；"
        f"直接主题 {counts.get('直接主题证据',0)} 篇；"
        f"背景/间接 {counts.get('背景/间接证据',0)} 篇。"
    )


def run_agent(question, evidence_df, task="自动判断", extra=""):
    api_key = _secret("DEEPSEEK_API_KEY")
    model = _secret("DEEPSEEK_MODEL", "deepseek-v4-pro")

    if not api_key:
        return None, []

    if task == "自动判断":
        task = route_task(question)

    local_context, local_sources = compact_context(evidence_df)

    # 默认自动补充最新学术与网页资料；失败时不会阻塞本地知识库。
    web_context, web_sources, web_status = research_web(question)

    numeric_guard = _numeric_guard(
        local_context,
        web_context,
    )

    local_quality = _local_quality(evidence_df)

    guidance = TASK_GUIDANCE.get(
        task,
        TASK_GUIDANCE["文献问答"],
    )

    prompt = f"""
任务类型：
{task}

用户问题：
{question}

额外实验/计算条件：
{extra}

{local_quality}

外部资料检索状态：
Crossref={web_status.get('crossref')}
OpenAlex={web_status.get('openalex')}
Web={web_status.get('web')}

数值约束：
{numeric_guard}

====================
本地KDP/DKDP文献证据
====================
{local_context}

====================
当前补充资料
====================
{web_context if web_context else "本次没有获得可用的外部检索结果。"}

执行要求：
{guidance}

回答要求：

## 1. 结论
先像正常科研问答一样直接解决用户问题，不要先解释你用了什么检索模式。

## 2. 依据与机理
用 [P#] / [W#] 绑定重要结论。
优先使用论文/期刊/数据库/官方文档等来源。
只有书目信息、没有摘要的 [W#] 只能用于定位论文，不能声称其“直接证明了”某个具体机理。

## 3. 综合判断
可以结合你的专业知识做推理，但明确写出哪些属于综合判断，而不是论文原话。

## 4. 不确定性
只列真正重要的证据缺口。不要为了格式机械地说“证据不足”。

## 5. 下一步
如果问题属于科研决策、实验、计算或研究方向，给出可执行的下一步。
普通知识问题不必强行设计实验。

不要编造文献、DOI、URL或精确数值。
"""

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.12,
    )

    answer = response.choices[0].message.content

    # 来源链接由程序确定性追加，避免模型自己生成或改写 URL。
    answer += source_links_markdown(web_sources)

    return answer, local_sources
