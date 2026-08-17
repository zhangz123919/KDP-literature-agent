
from openai import OpenAI
import streamlit as st

def _paper_context(df, max_papers=12):
    blocks, sources = [], []
    for i,(_,r) in enumerate(df.head(max_papers).iterrows(), start=1):
        title = str(r.get("题名",""))
        year = str(r.get("年份",""))
        journal = str(r.get("期刊",""))
        doi = str(r.get("DOI",""))
        abstract = str(r.get("摘要",""))
        conclusion = str(r.get("自动主要结论",""))
        category = str(r.get("详细二级分类",""))
        method = str(r.get("研究方法",""))
        blocks.append(
            f"[文献{i}]\n题名：{title}\n年份：{year}\n期刊：{journal}\nDOI：{doi}\n"
            f"分类：{category}\n方法：{method}\n摘要：{abstract[:2200]}\n自动结论：{conclusion[:1200]}"
        )
        sources.append(f"{title}（{year}，{journal}） DOI: {doi}")
    return "\n\n".join(blocks), sources

def ask_agent(question, evidence_df):
    client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    model = st.secrets.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    context, sources = _paper_context(evidence_df)
    system = """你是KDP/DKDP晶体缺陷、激光损伤、开裂与理论计算方向的科研智能体。
只能依据提供的文献证据回答，不得捏造文献、DOI、数值或结论。
证据不足时必须明确指出。
优先建立“缺陷来源→微观结构/电子态→吸收/散射/应力→损伤/开裂→检测与控制”的因果链。
区分共识、分歧和证据强弱。"""
    user = f"""用户问题：{question}

检索到的文献证据：
{context}

请给出：
1. 直接结论；
2. 证据链；
3. 代表性文献之间的共识与差异；
4. 当前仍缺少的证据；
5. 对后续KDP/DKDP研究的可执行建议。
引用文献时用[文献1]、[文献2]编号。"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.2,
    )
    return resp.choices[0].message.content, sources
