
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from retrieval import load_literature, search_papers, topic_summary
from agent import ask_agent

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "KDP_全自动详细文献调研.xlsx"

st.set_page_config(page_title="KDP/DKDP 文献研究智能体", page_icon="🔬", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {font-family:"Microsoft YaHei","微软雅黑",Arial,sans-serif;}
.block-container {padding-top:1.2rem;padding-bottom:3rem;max-width:1500px;}
[data-testid="stMetric"] {border:1px solid rgba(120,120,120,.18);padding:.8rem;border-radius:.8rem}
</style>
""", unsafe_allow_html=True)

st.title("🔬 KDP/DKDP 晶体缺陷与激光损伤研究智能体")
st.caption("围绕“缺陷来源 → 微观机制 → 光学响应 → 激光损伤/开裂 → 检测与控制”组织文献。")

if not DATA_FILE.exists():
    st.error("缺少数据文件：data/KDP_全自动详细文献调研.xlsx")
    st.info("请把你本地 output 文件夹中的 KDP_全自动详细文献调研.xlsx 上传到 GitHub 仓库的 data 文件夹。")
    st.stop()

df = load_literature(DATA_FILE)
related = df[df["材料相关性"].astype(str).eq("KDP/DKDP相关")].copy() if "材料相关性" in df.columns else df.copy()

with st.sidebar:
    st.header("研究范围")
    min_year = int(pd.to_numeric(related["年份"], errors="coerce").dropna().min()) if "年份" in related else 1940
    max_year = int(pd.to_numeric(related["年份"], errors="coerce").dropna().max()) if "年份" in related else 2026
    years = st.slider("年份", min_year, max_year, (max(1990, min_year), max_year))
    q = st.text_input("快速检索", placeholder="hydrogen vacancy / 包裹体 / DFT / subsurface damage")
    st.divider()
    st.markdown("**集中研究主线**")
    st.markdown("1. 缺陷从哪里来")
    st.markdown("2. 缺陷改变了什么")
    st.markdown("3. 为什么会导致损伤/开裂")
    st.markdown("4. 如何检测与控制")

work = related.copy()
if "年份" in work.columns:
    work["年份"] = pd.to_numeric(work["年份"], errors="coerce").fillna(0).astype(int)
    work = work[work["年份"].between(years[0], years[1])]
if q:
    work = search_papers(work, q, top_k=min(500, len(work)))

tabs = st.tabs(["研究主线", "专题调研", "文献库", "AI科研助手"])

with tabs[0]:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("相关文献", f"{len(work):,}")
    c2.metric("S核心必读", int((work["优先级"].astype(str)=="S 核心必读").sum()) if "优先级" in work else "—")
    c3.metric("A重点", int((work["优先级"].astype(str)=="A 重点").sum()) if "优先级" in work else "—")
    c4.metric("当前年份范围", f"{years[0]}–{years[1]}")

    st.subheader("一条主线看懂KDP/DKDP缺陷研究")
    st.markdown("""
**① 缺陷来源**  
本征点缺陷、杂质/掺杂、晶体生长缺陷、加工引入缺陷

**↓**

**② 微观机制**  
氢键与局域结构变化 → 缺陷能级/局域态 → 应变与位错 → 局域吸收/散射

**↓**

**③ 宏观后果**  
弱吸收增强、光学均匀性下降、热积累、应力集中、裂纹萌生、多光子电离与激光损伤

**↓**

**④ 检测与控制**  
DFT/MD/有限元 + 光谱/光热/显微/XRD/LIDT → 生长控制、净化、抛光、刻蚀、清洗与缺陷抑制
""")

    if "年份" in work.columns and len(work):
        trend = work[work["年份"]>0].groupby("年份").size().reset_index(name="数量")
        fig = px.line(trend, x="年份", y="数量", markers=True, title="研究活跃度趋势")
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("专题自动调研")
    topic = st.selectbox("选择专题", [
        "氢空位与质子缺失",
        "金属杂质与吸收前驱体",
        "包裹体、位错与生长缺陷",
        "晶体开裂与热应力",
        "表面/亚表面加工损伤",
        "第一性原理与缺陷电子结构",
        "弱吸收与光热检测",
        "激光损伤阈值与损伤机制",
    ])
    result = topic_summary(work, topic, top_k=30)
    st.write(f"命中 **{len(result)} 篇** 代表性候选文献。")
    if not result.empty:
        show = [c for c in ["题名","年份","期刊","详细二级分类","研究方法","综合重要度","优先级","自动主要结论","DOI"] if c in result.columns]
        st.dataframe(result[show], use_container_width=True, hide_index=True, height=520)
        if st.button("让AI生成该专题的集中调研", type="primary"):
            if "DEEPSEEK_API_KEY" not in st.secrets:
                st.warning("尚未配置 DeepSeek API Key。部署后可在 Streamlit Cloud 的 Secrets 中添加。")
            else:
                prompt = f"""请基于检索到的文献，为专题“{topic}”生成一份面向硕博研究生的KDP/DKDP集中型文献调研。
必须按：研究问题→主要方法→共同结论→分歧/争议→关键代表文献→研究空白→可执行研究方向 的顺序组织。
不要把分类和统计分散罗列。"""
                answer, sources = ask_agent(prompt, result)
                st.markdown(answer)
                st.markdown("#### 依据文献")
                for s in sources:
                    st.markdown(f"- {s}")

with tabs[2]:
    st.subheader("文献库")
    query = st.text_input("检索题名、摘要、关键词、分类", key="library_q")
    if query:
        results = search_papers(work, query, top_k=200)
    else:
        sort_cols = [c for c in ["综合重要度","被引次数"] if c in work.columns]
        results = work.sort_values(sort_cols, ascending=False).head(200) if sort_cols else work.head(200)
    show = [c for c in ["题名","作者","年份","期刊","分类代码","详细二级分类","研究方法","综合重要度","优先级","DOI"] if c in results.columns]
    st.dataframe(results[show], use_container_width=True, hide_index=True, height=600)

with tabs[3]:
    st.subheader("AI科研助手")
    st.caption("先从文献库检索证据，再让模型综合回答。")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    question = st.chat_input("例如：KDP中哪类氢空位最可能引起额外光吸收？")
    if question:
        st.session_state.chat_history.append({"role":"user","content":question})
        with st.chat_message("user"):
            st.markdown(question)

        evidence = search_papers(work, question, top_k=12)
        with st.chat_message("assistant"):
            if evidence.empty:
                answer = "当前文献库未检索到足够相关的证据。建议修改关键词或扩大年份范围。"
                st.markdown(answer)
            elif "DEEPSEEK_API_KEY" not in st.secrets:
                st.warning("智能体已能检索文献，但尚未配置 DeepSeek API Key。")
                for _,r in evidence.head(8).iterrows():
                    st.markdown(f"- **{r.get('题名','')}**（{r.get('年份','')}） DOI: {r.get('DOI','')}")
                answer = "已检索到文献证据；配置DeepSeek API Key后即可生成综合回答。"
            else:
                answer, sources = ask_agent(question, evidence)
                st.markdown(answer)
                st.markdown("#### 依据文献")
                for s in sources:
                    st.markdown(f"- {s}")
        st.session_state.chat_history.append({"role":"assistant","content":answer})
