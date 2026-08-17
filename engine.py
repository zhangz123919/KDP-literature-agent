
from pathlib import Path
from collections import Counter
import re

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "KDP_全自动详细文献调研.xlsx"

TOPICS = {
    "晶体开裂": ["crack","cracking","fracture","microcrack","thermal stress","residual stress","开裂","裂纹","热应力","残余应力"],
    "氢空位/质子缺失": ["hydrogen vacancy","proton vacancy","h vacancy","hydrogen defect","氢空位","质子空位","质子缺失"],
    "钾/氧/磷酸根点缺陷": ["potassium vacancy","oxygen vacancy","phosphate defect","interstitial","钾空位","氧空位","磷酸根缺陷"],
    "杂质与掺杂": ["impurity","dopant","doping","transition metal","杂质","掺杂","金属离子"],
    "包裹体与散射中心": ["inclusion","solution inclusion","particle inclusion","scattering center","包裹体","夹杂","散射中心"],
    "位错与晶格应变": ["dislocation","lattice strain","growth striation","位错","晶格应变","生长条纹"],
    "生长缺陷/快速生长": ["growth defect","rapid growth","fast growth","supersaturation","growth sector","生长缺陷","快速生长","过饱和度"],
    "DKDP氘化与同位素": ["dkdp","deuteration","deuterium concentration","isotope effect","氘化","同位素"],
    "表面/亚表面加工损伤": ["subsurface damage","sub-surface damage","surface damage","polishing","grinding","diamond turning","fly cutting","亚表面损伤","表面损伤","抛光","研磨","飞切"],
    "激光损伤/LIDT": ["laser damage","laser-induced damage","lidt","damage threshold","breakdown","激光损伤","损伤阈值"],
    "弱吸收/光热检测": ["weak absorption","photothermal","thermal lens","pci","localized absorption","弱吸收","光热","局域吸收"],
    "第一性原理/DFT": ["first principles","first-principles","density functional theory","dft","formation energy","density of states","electronic structure","第一性原理","形成能","态密度","电子结构"],
    "分子动力学/原子模拟": ["molecular dynamics","md simulation","atomistic simulation","分子动力学"],
    "有限元/热应力模拟": ["finite element","multiphysics","thermal model","stress field","有限元","多物理场"],
    "光谱与显微表征": ["raman","ftir","xrd","afm","sem","tem","spectroscopy","microscopy","拉曼","红外","显微","x射线"],
}

INTENT_RULES = {
    "氢空位": {
        "triggers": ["氢空位","质子空位","质子缺失","hydrogen vacancy","proton vacancy","h vacancy"],
        "must": ["氢空位","质子空位","质子缺失","hydrogen vacancy","proton vacancy","h vacancy","hydrogen defect"],
        "boost": ["extra absorption","optical absorption","absorption","defect level","defect state","density of states","electronic structure","localized state","额外吸收","光吸收","缺陷能级","缺陷态","态密度","电子结构","局域态"],
    },
    "晶体开裂": {
        "triggers": ["开裂","裂纹","断裂","crack","cracking","fracture","microcrack"],
        "must": ["crack","cracking","fracture","microcrack","开裂","裂纹","断裂"],
        "boost": ["thermal stress","residual stress","stress concentration","inclusion","dislocation","seed crystal","热应力","残余应力","应力集中","包裹体","位错","籽晶"],
    },
    "包裹体": {
        "triggers": ["包裹体","夹杂","散射中心","inclusion","scattering center"],
        "must": ["inclusion","solution inclusion","particle inclusion","scattering center","包裹体","夹杂","散射中心"],
        "boost": ["stress","strain","crack","laser damage","growth defect","scattering","应力","应变","裂纹","激光损伤","生长缺陷"],
    },
    "激光损伤": {
        "triggers": ["激光损伤","损伤阈值","lidt","laser damage","damage threshold"],
        "must": ["laser damage","laser-induced damage","lidt","damage threshold","breakdown","激光损伤","损伤阈值","击穿"],
        "boost": ["defect","absorption","inclusion","impurity","vacancy","缺陷","吸收","包裹体","杂质","空位"],
    },
    "第一性原理": {
        "triggers": ["第一性原理","dft","first principles","density functional theory","形成能","态密度"],
        "must": ["first principles","first-principles","density functional theory","dft","formation energy","density of states","第一性原理","形成能","态密度"],
        "boost": ["defect","vacancy","electronic structure","optical absorption","缺陷","空位","电子结构","吸收"],
    },
}

def _clean(x):
    return "" if pd.isna(x) else re.sub(r"\s+"," ",str(x)).strip()

def _pattern(term):
    term = str(term).lower().strip()
    if re.fullmatch(r"[a-z0-9+\-]+", term):
        return rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.escape(term)

def _series_hit(series, terms):
    s = series.fillna("").astype(str).str.lower()
    out = pd.Series(False, index=s.index)
    for term in terms:
        out |= s.str.contains(_pattern(term), regex=True)
    return out

def _series_count(series, terms):
    s = series.fillna("").astype(str).str.lower()
    out = pd.Series(0.0, index=s.index)
    for term in terms:
        out += s.str.contains(_pattern(term), regex=True).astype(float)
    return out

def _detect_intent(query):
    q = str(query or "").lower()
    for name, rule in INTENT_RULES.items():
        if any(str(t).lower() in q for t in rule["triggers"]):
            return name, rule
    return None, None

@st.cache_data(show_spinner="正在读取文献数据库……")
def load_data():
    if not DATA_PATH.exists():
        return pd.DataFrame()

    xls = pd.ExcelFile(DATA_PATH)
    sheet = next((s for s in ["全部详细分类","全部去重","KDP相关全部"] if s in xls.sheet_names), xls.sheet_names[0])
    df = pd.read_excel(DATA_PATH, sheet_name=sheet)

    defaults = {
        "题名":"","作者":"","期刊":"","年份":0,"DOI":"","摘要":"",
        "作者关键词":"","Keywords Plus":"","详细二级分类":"","研究方法":"",
        "自动研究问题":"","自动主要结论":"","综合重要度":0,"被引次数":0,
        "材料相关性":""
    }
    for c,v in defaults.items():
        if c not in df.columns:
            df[c] = v

    for c in defaults:
        if c not in {"年份","综合重要度","被引次数"}:
            df[c] = df[c].fillna("").astype(str)

    df["年份"] = pd.to_numeric(df["年份"], errors="coerce").fillna(0).astype(int)
    df["综合重要度"] = pd.to_numeric(df["综合重要度"], errors="coerce").fillna(0.0)
    df["被引次数"] = pd.to_numeric(df["被引次数"], errors="coerce").fillna(0).astype(int)

    text_cols = ["题名","摘要","作者关键词","Keywords Plus","详细二级分类","研究方法","自动研究问题","自动主要结论"]
    df["_text"] = df[text_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()

    # 兼容现有页面需要的字段
    df["缺陷/应力来源"] = np.select(
        [
            df["_text"].str.contains("vacancy|point defect|氢空位|钾空位|氧空位", regex=True),
            df["_text"].str.contains("impurity|dopant|doping|杂质|掺杂", regex=True),
            df["_text"].str.contains("inclusion|dislocation|growth defect|supersaturation|包裹体|位错|生长缺陷|过饱和度", regex=True),
            df["_text"].str.contains("subsurface|polishing|grinding|machining|亚表面|抛光|研磨|加工", regex=True),
        ],
        ["本征点缺陷","杂质/掺杂","晶体生长缺陷","加工引入缺陷"],
        default="基础物性/其他"
    )
    df["作用机制"] = np.select(
        [
            df["_text"].str.contains("electronic structure|defect level|density of states|电子结构|缺陷能级|态密度", regex=True),
            df["_text"].str.contains("hydrogen bond|proton transfer|lattice distortion|氢键|质子转移|晶格畸变", regex=True),
            df["_text"].str.contains("thermal stress|residual stress|fracture|crack|热应力|残余应力|裂纹", regex=True),
            df["_text"].str.contains("inclusion|scattering center|包裹体|散射中心", regex=True),
        ],
        ["电子结构/缺陷态","氢键/局域结构","热-力应力/裂纹","包裹体/散射"],
        default="机制未明确"
    )
    df["宏观结果"] = np.select(
        [
            df["_text"].str.contains("crack|fracture|microcrack|开裂|裂纹|断裂", regex=True),
            df["_text"].str.contains("laser damage|lidt|damage threshold|激光损伤|损伤阈值", regex=True),
            df["_text"].str.contains("absorption|optical property|transmission|吸收|光学性质|透过率", regex=True),
            df["_text"].str.contains("scattering|optical homogeneity|散射|光学均匀性", regex=True),
        ],
        ["开裂/断裂","激光损伤/LIDT","吸收/光学响应","散射/光学均匀性"],
        default="结果未明确"
    )
    df["_方法标签"] = np.select(
        [
            df["_text"].str.contains("density functional theory|first principles|first-principles|\\bdft\\b", regex=True),
            df["_text"].str.contains("molecular dynamics|md simulation", regex=True),
            df["_text"].str.contains("finite element|multiphysics", regex=True),
            df["_text"].str.contains("photothermal|weak absorption|\\bpci\\b", regex=True),
            df["_text"].str.contains("raman|ftir|xrd|afm|sem|tem|spectroscopy|microscopy", regex=True),
        ],
        ["DFT/第一性原理","分子动力学","有限元/连续介质","光热/弱吸收","光谱/显微表征"],
        default="未明确"
    )

    if (df["材料相关性"] == "KDP/DKDP相关").any():
        related = df["材料相关性"].eq("KDP/DKDP相关")
    else:
        related = (
            _series_hit(df["_text"], ["kdp","kh2po4","potassium dihydrogen phosphate"])
            | _series_hit(df["_text"], ["dkdp","kd2po4","deuterated potassium dihydrogen phosphate"])
        )

    df["V5相关池"] = np.where(related, "KDP/DKDP相关池", "非核心/待核")

    score = (
        df["综合重要度"].clip(0,100) * 0.70
        + np.log1p(df["被引次数"].clip(lower=0)) / np.log(201) * 12
        + df["_text"].str.contains(
            "defect|vacancy|crack|laser damage|subsurface|缺陷|空位|开裂|激光损伤",
            regex=True
        ).astype(float) * 12
    )
    df["V5科研优先分"] = score.clip(0,100).round(1)

    tier = pd.Series("C 扩展/背景", index=df.index, dtype="object")
    ranked = df[related].sort_values(["V5科研优先分","被引次数","年份"], ascending=False)
    tier.loc[ranked.index[:50]] = "S 核心 50"
    tier.loc[ranked.index[50:200]] = "A 重点 150"
    tier.loc[ranked.index[200:1000]] = "B 扩展 800"
    tier.loc[df.index[~related]] = "D 非核心/待核"
    df["V5推荐等级"] = tier
    return df

def search_papers(df, q, top_k=100, scope="相关池"):
    work = df.copy()
    if scope == "相关池":
        work = work[work["V5相关池"] == "KDP/DKDP相关池"]
    elif scope == "S+A":
        work = work[work["V5推荐等级"].isin(["S 核心 50","A 重点 150"])]

    if work.empty:
        return work

    if not str(q or "").strip():
        out = work.sort_values(["V5科研优先分","被引次数"], ascending=False).head(top_k).copy()
        out["_证据层级"] = "背景/间接证据"
        return out

    title = work["题名"].astype(str)
    keywords = work["作者关键词"].astype(str) + " " + work["Keywords Plus"].astype(str) + " " + work["详细二级分类"].astype(str)
    abstract = work["摘要"].astype(str)
    conclusion = work["自动主要结论"].astype(str) + " " + work["自动研究问题"].astype(str)
    all_text = title + " " + keywords + " " + abstract + " " + conclusion

    score = work["V5科研优先分"].fillna(0) / 40.0

    # 普通关键词
    tokens = re.findall(r"[a-z][a-z0-9+\-]{1,}|[\u4e00-\u9fff]{2,}", str(q).lower())
    stop = {"为什么","如何","可能","请基于","文献库","给出","证据","研究","分析","比较","the","and","why","how"}
    tokens = [t for t in dict.fromkeys(tokens) if t not in stop]
    for term in tokens:
        score += _series_hit(title,[term]).astype(float) * 9
        score += _series_hit(keywords,[term]).astype(float) * 6
        score += _series_hit(conclusion,[term]).astype(float) * 3
        score += _series_hit(abstract,[term]).astype(float) * 1.5

    # KDP 和 DKDP 严格区分
    q_lower = str(q).lower()
    kdp_hit = _series_hit(all_text, ["kdp","kh2po4","potassium dihydrogen phosphate"])
    dkdp_hit = _series_hit(all_text, ["dkdp","kd2po4","deuterated potassium dihydrogen phosphate"])
    if "kdp" in q_lower and "dkdp" not in q_lower:
        score += kdp_hit.astype(float) * 12
        score += dkdp_hit.astype(float) * 2

    _, rule = _detect_intent(q)
    evidence = pd.Series("背景/间接证据", index=work.index)
    candidate = score > 0

    if rule:
        must_title = _series_count(title, rule["must"])
        must_keywords = _series_count(keywords, rule["must"])
        must_abstract = _series_count(abstract, rule["must"])
        must_conclusion = _series_count(conclusion, rule["must"])

        direct = (must_title > 0) | (must_keywords > 0) | (must_abstract > 0) | (must_conclusion > 0)

        score += direct.astype(float) * 32
        score += must_title * 18 + must_keywords * 10 + must_conclusion * 6 + must_abstract * 3
        score += (
            _series_count(title, rule["boost"]) * 5
            + _series_count(keywords, rule["boost"]) * 3
            + _series_count(abstract, rule["boost"]) * 1
        )

        strong = direct & kdp_hit if ("kdp" in q_lower and "dkdp" not in q_lower) else direct
        score += strong.astype(float) * 25

        evidence.loc[direct] = "直接主题证据"
        evidence.loc[strong] = "强直接证据"

        if int(strong.sum()) >= 3:
            candidate = strong | direct
        elif int(direct.sum()) >= 3:
            candidate = direct

    out = work.copy()
    out["_检索得分"] = score
    out["_证据层级"] = evidence
    out = out[candidate].copy()

    if out.empty:
        out = work.copy()
        out["_检索得分"] = score
        out["_证据层级"] = "背景/间接证据"

    rank = {"强直接证据":3,"直接主题证据":2,"背景/间接证据":1}
    out["_证据排序"] = out["_证据层级"].map(rank).fillna(0)
    out = out.sort_values(
        ["_证据排序","_检索得分","V5科研优先分","被引次数"],
        ascending=[False,False,False,False]
    )
    return out.head(top_k).drop(columns=["_证据排序"])

def topic_search(df, topic, top_k=100, scope="相关池"):
    return search_papers(df, " ".join(TOPICS.get(topic,[topic])), top_k, scope)

def topic_stats(df):
    rel = df[df["V5相关池"] == "KDP/DKDP相关池"]
    max_year = int(rel["年份"].max()) if len(rel) else 2026
    rows = []
    for topic in TOPICS:
        d = topic_search(rel, topic, len(rel), "全部")
        rows.append({
            "专题":topic,
            "总文献":len(d),
            "近5年":int((d["年份"] >= max_year-4).sum()) if len(d) else 0,
            "S/A":int(d["V5推荐等级"].isin(["S 核心 50","A 重点 150"]).sum()) if len(d) else 0,
            "DFT":int(d["_方法标签"].str.contains("DFT/第一性原理", regex=False).sum()) if len(d) else 0,
        })
    return pd.DataFrame(rows)

def compact_context(df, maxp=15):
    blocks = []
    sources = []
    for i,(_,r) in enumerate(df.head(maxp).iterrows(),1):
        blocks.append(
            f"[P{i}]\n题名：{_clean(r.get('题名',''))}\n年份：{r.get('年份','')}\n"
            f"期刊：{_clean(r.get('期刊',''))}\nDOI：{_clean(r.get('DOI',''))}\n"
            f"等级：{r.get('V5推荐等级','')}\n证据层级：{r.get('_证据层级','未标记')}\n"
            f"方法：{r.get('_方法标签','')}\n摘要：{_clean(r.get('摘要',''))[:2200]}\n"
            f"结论：{_clean(r.get('自动主要结论',''))[:900]}"
        )
        sources.append({
            "编号":f"P{i}",
            "题名":_clean(r.get("题名","")),
            "年份":r.get("年份",""),
            "期刊":_clean(r.get("期刊","")),
            "DOI":_clean(r.get("DOI","")),
        })
    return "\n\n".join(blocks), sources

def offline_summary(df, topic=""):
    if df.empty:
        return "没有检索到匹配文献。"
    evidence = df["_证据层级"].value_counts().to_dict() if "_证据层级" in df.columns else {}
    return (
        f"### {topic or '当前结果'}：离线证据概览\n"
        f"- 文献数：**{len(df)}**\n"
        f"- 证据层级：{evidence}\n"
        f"- 主要来源：{df['缺陷/应力来源'].value_counts().head(3).to_dict()}\n"
        f"- 主要机制：{df['作用机制'].value_counts().head(3).to_dict()}\n"
        f"- 主要结果：{df['宏观结果'].value_counts().head(3).to_dict()}\n\n"
        "> 正式科研结论仍应核对论文全文。"
    )
