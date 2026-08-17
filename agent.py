
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
    client=OpenAI(api_key=_get("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com")
    prompt=f"任务:{task}\n问题:{q}\n额外条件:{extra}\n文献证据:\n{ctx}\n请给直接结论、证据链、共识/分歧、证据不足和下一步建议。引用用[P1][P2]。"
    r=client.chat.completions.create(model=model,messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],temperature=0.15)
    return r.choices[0].message.content,src
