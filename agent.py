
import streamlit as st
from openai import OpenAI
from engine import compact_context

SYSTEM="你是KDP/DKDP晶体开裂与缺陷研究科研智能体。只能依据提供的文献证据回答；必须区分直接证据、跨文献推断和建议验证；优先按缺陷来源→机制→损伤/开裂→检测控制组织。"

def _get(k,d=None):
    try:return st.secrets.get(k,d)
    except:return d
def api_status():
    key=_get("DEEPSEEK_API_KEY");model=_get("DEEPSEEK_MODEL","deepseek-chat")
    return bool(key),model
def run_agent(q,df,task="文献问答",extra=""):
    ok,model=api_status()
    if not ok:return None,[]
    ctx,src=compact_context(df)
        quality_note = ""

    if "_证据层级" in df.columns:

        counts = (
            df["_证据层级"]
            .value_counts()
            .to_dict()
        )

        strong_n = counts.get(
            "强直接证据", 0
        )

        direct_n = counts.get(
            "直接主题证据", 0
        )

        total_direct = (
            strong_n + direct_n
        )

        quality_note = f"""
检索证据质量：
强直接证据：{strong_n}篇
直接主题证据：{direct_n}篇
其余为背景/间接证据。

"""

        if total_direct < 3:

            quality_note += """
警告：
当前直接证据少于3篇。

不得把背景论文写成直接证明。
必须明确告诉用户：
“当前文献库中的直接证据不足”。

可以使用背景文献解释机理，
但必须标记为跨文献推断。
"""
    client=OpenAI(api_key=_get("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com")
    prompt=f"任务:{task}\n问题:{q}\n额外条件:{extra}\n文献证据:\n{ctx}\n请给直接结论、证据链、共识/分歧、证据不足和下一步建议。引用用[P1][P2]。"
    r=client.chat.completions.create(model=model,messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],temperature=0.15)
    return r.choices[0].message.content,src
