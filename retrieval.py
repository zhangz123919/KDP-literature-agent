
from pathlib import Path
import re
import pandas as pd
import streamlit as st

@st.cache_data(show_spinner="正在读取文献数据库……")
def load_literature(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    preferred = ["全部详细分类","KDP相关全部"]
    sheet = next((s for s in preferred if s in xls.sheet_names), xls.sheet_names[0])
    df = pd.read_excel(path, sheet_name=sheet)
    for c in ["题名","摘要","作者关键词","Keywords Plus","详细二级分类","研究方法","自动主要结论","DOI","期刊","作者"]:
        if c not in df.columns:
            df[c] = ""
    return df

def _tokens(q: str):
    q = str(q or "").lower().strip()
    return list(dict.fromkeys(re.findall(r"[a-z0-9+\-]{2,}|[\u4e00-\u9fff]{2,}", q)))

def search_papers(df: pd.DataFrame, query: str, top_k: int = 50) -> pd.DataFrame:
    if not query:
        return df.head(top_k).copy()
    toks = _tokens(query)
    if not toks:
        return df.head(top_k).copy()
    weights = {"题名":6.0,"详细二级分类":5.0,"作者关键词":4.0,"Keywords Plus":3.0,"自动主要结论":2.0,"摘要":1.0,"研究方法":2.0}
    score = pd.Series(0.0, index=df.index)
    for col,w in weights.items():
        text = df[col].fillna("").astype(str).str.lower()
        for t in toks:
            score += text.str.contains(t, regex=False).astype(float) * w
    if "综合重要度" in df.columns:
        score += pd.to_numeric(df["综合重要度"], errors="coerce").fillna(0) / 100.0
    out = df.copy()
    out["_检索得分"] = score
    out = out[out["_检索得分"] > 0].sort_values("_检索得分", ascending=False)
    return out.head(top_k).drop(columns=["_检索得分"])

TOPIC_QUERIES = {
    "氢空位与质子缺失": "hydrogen vacancy proton vacancy 氢空位 质子缺失 hydrogen defect",
    "金属杂质与吸收前驱体": "metal impurity transition metal absorbing precursor defect absorption 金属杂质 吸收前驱体",
    "包裹体、位错与生长缺陷": "inclusion dislocation growth defect supersaturation 包裹体 位错 生长缺陷",
    "晶体开裂与热应力": "crack fracture thermal stress thermoelastic microcrack 开裂 裂纹 热应力",
    "表面/亚表面加工损伤": "subsurface damage polishing machining diamond turning 表面 亚表面 加工损伤",
    "第一性原理与缺陷电子结构": "first principles dft electronic structure density of states formation energy 第一性原理 电子结构",
    "弱吸收与光热检测": "photothermal weak absorption pci 光热 弱吸收",
    "激光损伤阈值与损伤机制": "laser damage lidt damage threshold breakdown laser induced damage 激光损伤 阈值",
}
def topic_summary(df: pd.DataFrame, topic: str, top_k: int = 30) -> pd.DataFrame:
    return search_papers(df, TOPIC_QUERIES.get(topic, topic), top_k=top_k)
