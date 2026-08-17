
import streamlit as st
from openai import OpenAI

from engine import compact_context


SYSTEM = """
你是KDP/DKDP晶体开裂与缺陷研究科研智能体，服务于硕博研究。

你必须遵循：
1. 只能把提供的文献证据作为具体文献结论依据，不能捏造作者、DOI、数值或实验结果。
2. 必须区分【文献直接证据】【跨文献推断】【建议验证】。
3. 优先按照：
   缺陷/变量来源 → 局部结构/电子态/应力 → 吸收/散射/应力集中
   → 开裂或激光损伤 → 检测与控制
   的逻辑组织回答。
4. 如果直接证据不足，必须明确说明“当前文献库直接证据不足”。
5. 输出要专业、紧凑、可执行，避免空泛表述。
"""


def _get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def api_status():
    key = _get_secret("DEEPSEEK_API_KEY")
    model = _get_secret("DEEPSEEK_MODEL", "deepseek-v4-pro")
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
        "有限元", "COMSOL", "ANSYS", "计算方案"
    ]):
        return "理论方案"

    if any(k in q for k in ["空白", "创新点", "研究方向", "还能做什么"]):
        return "研究空白"

    if any(k in q for k in ["组会", "报告", "开题", "汇报"]):
        return "报告生成"

    if any(k in q for k in ["综述", "专题调研", "调研"]):
        return "专题调研"

    return "文献问答"


TASK_GUIDANCE = {
    "文献问答": "直接回答问题，并给出证据链、共识/分歧、证据不足和下一步验证建议。",
    "多文献比较": "比较研究对象、方法、条件、关键结论、证据强弱、差异原因和可复现价值。",
    "专题调研": "形成集中型调研：研究问题→方法谱系→共同结论→争议→代表文献→研究空白→建议。",
    "研究空白": "提出可验证的研究空白，并说明已有证据、缺口、验证方案和预期价值。",
    "实验诊断": "输出根因排序、证据链、变量风险、最小对照实验、观测指标和判据。",
    "理论方案": "输出模型→结构/超胞→缺陷或工况→计算方法→收敛→输出量→验证→风险。",
    "报告生成": "生成可直接用于组会、开题或阶段总结的紧凑报告。",
}


def _evidence_quality_note(evidence_df):
    if "_证据层级" not in evidence_df.columns:
        return (
            "当前检索结果没有证据层级标记。回答时仍需谨慎，"
            "不得把背景论文写成直接证据。"
        )

    counts = evidence_df["_证据层级"].value_counts().to_dict()

    strong_n = int(counts.get("强直接证据", 0))
    direct_n = int(counts.get("直接主题证据", 0))
    background_n = int(counts.get("背景/间接证据", 0))
    total_direct = strong_n + direct_n

    note = (
        f"检索证据质量：\n"
        f"- 强直接证据：{strong_n}篇\n"
        f"- 直接主题证据：{direct_n}篇\n"
        f"- 背景/间接证据：{background_n}篇\n"
    )

    if total_direct < 3:
        note += (
            "\n重要：当前直接证据少于3篇。"
            "不得把背景论文描述为直接证明；"
            "必须明确写出“当前文献库直接证据不足”，"
            "背景论文只能用于机理解释或跨文献推断。"
        )

    return note


def run_agent(question, evidence_df, task="自动判断", extra=""):
    api_key = _get_secret("DEEPSEEK_API_KEY")
    model = _get_secret("DEEPSEEK_MODEL", "deepseek-v4-pro")

    if not api_key:
        return None, []

    if task == "自动判断":
        task = route_task(question)

    context, sources = compact_context(evidence_df)
    quality_note = _evidence_quality_note(evidence_df)
    task_guidance = TASK_GUIDANCE.get(task, TASK_GUIDANCE["文献问答"])

    prompt = f"""
任务类型：
{task}

用户问题：
{question}

额外实验/计算条件：
{extra}

{quality_note}

文献证据：
{context}

执行要求：
{task_guidance}

回答必须至少包含以下部分：
1. 直接结论
2. 文献直接证据
3. 跨文献推断
4. 当前证据不足
5. 建议实验/计算验证

引用具体文献时必须使用 [P1]、[P2] 这样的编号。
不要捏造文献中没有给出的数值、作者结论或实验结果。
"""

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
    )

    return response.choices[0].message.content, sources
