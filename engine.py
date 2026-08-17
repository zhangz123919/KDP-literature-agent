
from pathlib import Path
from collections import Counter
import re
import numpy as np
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parent
DATA_PATH=ROOT/"data"/"KDP_全自动详细文献调研.xlsx"

TOPICS={
"晶体开裂":["crack","fracture","microcrack","thermal stress","residual stress","开裂","裂纹","热应力"],
"氢空位/质子缺失":["hydrogen vacancy","proton vacancy","hydrogen defect","氢空位","质子缺失"],
"钾/氧/磷酸根点缺陷":["potassium vacancy","oxygen vacancy","phosphate defect","interstitial","钾空位","氧空位","磷酸根缺陷"],
"杂质与掺杂":["impurity","dopant","doping","transition metal","杂质","掺杂"],
"包裹体与散射中心":["inclusion","scattering center","包裹体","散射中心"],
"位错与晶格应变":["dislocation","lattice strain","growth striation","位错","晶格应变"],
"生长缺陷/快速生长":["growth defect","rapid growth","supersaturation","growth sector","生长缺陷","快速生长","过饱和度"],
"DKDP氘化与同位素":["dkdp","deuteration","deuterium concentration","isotope effect","氘化","同位素"],
"表面/亚表面加工损伤":["subsurface damage","surface damage","polishing","grinding","diamond turning","fly cutting","亚表面损伤","抛光","研磨"],
"激光损伤/LIDT":["laser damage","laser-induced damage","lidt","damage threshold","breakdown","激光损伤","损伤阈值"],
"弱吸收/光热检测":["weak absorption","photothermal","thermal lens","pci","localized absorption","弱吸收","光热"],
"第一性原理/DFT":["first principles","density functional theory","dft","formation energy","density of states","第一性原理","形成能","态密度"],
"分子动力学/原子模拟":["molecular dynamics","md simulation","atomistic simulation","分子动力学"],
"有限元/热应力模拟":["finite element","multiphysics","thermal model","stress field","有限元","多物理场"],
"光谱与显微表征":["raman","ftir","xrd","afm","sem","tem","spectroscopy","microscopy","拉曼","显微"],
}
SOURCE={
"本征点缺陷":["vacancy","interstitial","antisite","point defect","氢空位","钾空位","氧空位"],
"杂质/掺杂":["impurity","dopant","doping","杂质","掺杂"],
"晶体生长缺陷":["inclusion","dislocation","growth defect","supersaturation","包裹体","位错","生长缺陷"],
"加工引入缺陷":["subsurface","polishing","grinding","diamond turning","machining","亚表面","抛光","研磨"],
"籽晶/固定/宏观约束":["seed crystal","seed orientation","holder","fixation","籽晶","固定方式"],
}
MECH={
"电子结构/缺陷态":["electronic structure","defect level","density of states","band gap","电子结构","缺陷能级","态密度"],
"氢键/局域结构":["hydrogen bond","proton transfer","local structure","lattice distortion","氢键","质子转移","晶格畸变"],
"热-力应力/裂纹":["thermal stress","residual stress","fracture","crack","热应力","残余应力","裂纹"],
"包裹体/散射":["inclusion","scattering center","light scattering","包裹体","散射中心"],
"强场电离/载流子":["multiphoton","photoionization","avalanche","plasma","多光子","光电离","雪崩"],
"生长动力学/界面":["growth kinetics","interface","mass transfer","supersaturation","生长动力学","界面","过饱和度"],
}
OUT={
"开裂/断裂":["crack","fracture","microcrack","开裂","裂纹","断裂"],
"激光损伤/LIDT":["laser damage","lidt","damage threshold","breakdown","激光损伤","损伤阈值"],
"吸收/光学响应":["absorption","optical property","transmission","dielectric","吸收","光学性质"],
"散射/光学均匀性":["scattering","optical homogeneity","散射","光学均匀性"],
"力学/热学":["mechanical","elastic","hardness","thermal conductivity","力学","弹性","硬度"],
"生长质量":["crystal quality","perfection","growth rate","purity","晶体质量","生长速率"],
}
METHOD={
"DFT/第一性原理":["dft","density functional theory","first principles","hybrid functional"],
"分子动力学":["molecular dynamics","md simulation"],
"有限元/连续介质":["finite element","multiphysics","stress field"],
"晶体生长实验":["crystal growth","rapid growth","supersaturation"],
"激光损伤实验":["laser damage","lidt","damage threshold"],
"光谱":["raman","ftir","spectroscopy"],
"光热/弱吸收":["photothermal","weak absorption","pci"],
"显微/形貌":["afm","sem","tem","microscopy"],
"XRD/拓扑":["xrd","x-ray diffraction","x-ray topography"],
"加工实验":["polishing","grinding","diamond turning","machining"],
}

def _t(x): return "" if pd.isna(x) else re.sub(r"\s+"," ",str(x)).strip()
def _has(text,term):
    text,term=str(text).lower(),str(term).lower()
    if re.fullmatch(r"[a-z0-9]+",term) and len(term)<=5:
        return re.search(rf"\b{re.escape(term)}\b",text) is not None
    return term in text
def _first(text,rules,default):
    for k,v in rules.items():
        if any(_has(text,x) for x in v): return k
    return default
def _methods(text):
    out=[k for k,v in METHOD.items() if any(_has(text,x) for x in v)]
    return "；".join(out) if out else "未明确"

@st.cache_data
def _raw():
    if not DATA_PATH.exists(): return pd.DataFrame()
    xls=pd.ExcelFile(DATA_PATH)
    for s in ["全部详细分类","全部去重","KDP相关全部"]:
        if s in xls.sheet_names: return pd.read_excel(DATA_PATH,sheet_name=s)
    return pd.read_excel(DATA_PATH,sheet_name=xls.sheet_names[0])

@st.cache_data
def load_data():
    df=_raw()
    if df.empty:return df
    defaults={"题名":"","作者":"","期刊":"","年份":0,"DOI":"","摘要":"","作者关键词":"","Keywords Plus":"","详细二级分类":"","研究方法":"","自动研究问题":"","自动主要结论":"","综合重要度":0,"被引次数":0,"材料相关性":""}
    for c,v in defaults.items():
        if c not in df.columns: df[c]=v
    for c in defaults:
        if c not in ["年份","综合重要度","被引次数"]: df[c]=df[c].fillna("").astype(str)
    df["年份"]=pd.to_numeric(df["年份"],errors="coerce").fillna(0).astype(int)
    df["综合重要度"]=pd.to_numeric(df["综合重要度"],errors="coerce").fillna(0)
    df["被引次数"]=pd.to_numeric(df["被引次数"],errors="coerce").fillna(0)
    cols=["题名","摘要","作者关键词","Keywords Plus","详细二级分类","研究方法","自动研究问题","自动主要结论"]
    df["_text"]=df[cols].fillna("").astype(str).agg(" ".join,axis=1).str.lower()
    df["缺陷/应力来源"]=[_first(x,SOURCE,"基础物性/其他") for x in df["_text"]]
    df["作用机制"]=[_first(x,MECH,"机制未明确") for x in df["_text"]]
    df["宏观结果"]=[_first(x,OUT,"结果未明确") for x in df["_text"]]
    df["_方法标签"]=[_methods(x) for x in df["_text"]]
    if (df["材料相关性"]=="KDP/DKDP相关").any():
        rel=df["材料相关性"].eq("KDP/DKDP相关")
    else:
        rel=df["_text"].str.contains(r"\bkdp\b|\bdkdp\b|potassium dihydrogen phosphate",regex=True)
    df["V5相关池"]=np.where(rel,"KDP/DKDP相关池","非核心/待核")
    score=df["综合重要度"]*.7+np.log1p(df["被引次数"])/np.log(201)*12+df["_text"].str.contains("defect|vacancy|crack|laser damage|subsurface|缺陷|空位|开裂|激光损伤",regex=True).astype(float)*12
    df["V5科研优先分"]=score.clip(0,100).round(1)
    tier=pd.Series("C 扩展/背景",index=df.index,dtype="object")
    ranked=df[rel].sort_values(["V5科研优先分","被引次数"],ascending=False)
    tier.loc[ranked.index[:50]]="S 核心 50"
    tier.loc[ranked.index[50:200]]="A 重点 150"
    tier.loc[ranked.index[200:1000]]="B 扩展 800"
    tier.loc[df.index[~rel]]="D 非核心/待核"
    df["V5推荐等级"]=tier
    return df

# =========================
# V5 科研检索引擎
# 主题识别 → 强约束召回 → 同义词扩展 → 二次排序
# =========================

INTENT_RULES = {
    "氢空位": {
        "triggers": [
            "氢空位", "质子空位", "质子缺失",
            "hydrogen vacancy", "proton vacancy", "h vacancy"
        ],
        "must": [
            "氢空位", "质子空位", "质子缺失",
            "hydrogen vacancy", "proton vacancy", "h vacancy",
            "hydrogen defect"
        ],
        "boost": [
            "extra absorption", "optical absorption", "absorption",
            "defect level", "defect state", "density of states",
            "electronic structure", "localized state",
            "charged vacancy", "positive vacancy",
            "额外吸收", "光吸收", "缺陷能级", "缺陷态",
            "态密度", "电子结构", "局域态", "带正电"
        ],
    },

    "晶体开裂": {
        "triggers": [
            "开裂", "裂纹", "断裂",
            "crack", "cracking", "fracture", "microcrack"
        ],
        "must": [
            "crack", "cracking", "fracture", "microcrack",
            "开裂", "裂纹", "断裂"
        ],
        "boost": [
            "thermal stress", "residual stress", "stress concentration",
            "inclusion", "dislocation", "seed crystal",
            "热应力", "残余应力", "应力集中",
            "包裹体", "位错", "籽晶"
        ],
    },

    "包裹体": {
        "triggers": [
            "包裹体", "夹杂", "散射中心",
            "inclusion", "scattering center"
        ],
        "must": [
            "inclusion", "solution inclusion", "particle inclusion",
            "scattering center", "包裹体", "夹杂", "散射中心"
        ],
        "boost": [
            "stress", "strain", "crack", "laser damage",
            "growth defect", "scattering",
            "应力", "应变", "裂纹", "激光损伤", "生长缺陷"
        ],
    },

    "过饱和度": {
        "triggers": [
            "过饱和度", "supersaturation", "快速生长", "rapid growth"
        ],
        "must": [
            "supersaturation", "rapid growth", "fast growth",
            "growth rate", "过饱和度", "快速生长", "生长速率"
        ],
        "boost": [
            "interface", "inclusion", "dislocation",
            "growth sector", "growth defect",
            "界面", "包裹体", "位错", "生长扇区", "生长缺陷"
        ],
    },

    "籽晶/固定": {
        "triggers": [
            "籽晶", "固定方式", "取向", "夹持",
            "seed crystal", "seed orientation", "fixation"
        ],
        "must": [
            "seed crystal", "seed orientation", "seed",
            "holder", "fixation", "mounting",
            "籽晶", "取向", "固定", "夹持"
        ],
        "boost": [
            "crack", "stress", "growth",
            "裂纹", "应力", "生长"
        ],
    },

    "亚表面损伤": {
        "triggers": [
            "亚表面", "加工损伤", "subsurface damage",
            "sub-surface damage", "polishing"
        ],
        "must": [
            "subsurface damage", "sub-surface damage",
            "surface damage", "polishing", "grinding",
            "diamond turning", "fly cutting",
            "亚表面损伤", "表面损伤", "抛光", "研磨", "飞切"
        ],
        "boost": [
            "crack", "microcrack", "residual stress",
            "laser damage", "裂纹", "残余应力", "激光损伤"
        ],
    },

    "激光损伤": {
        "triggers": [
            "激光损伤", "损伤阈值", "lidt",
            "laser damage", "damage threshold"
        ],
        "must": [
            "laser damage", "laser-induced damage",
            "lidt", "damage threshold", "breakdown",
            "激光损伤", "损伤阈值", "击穿"
        ],
        "boost": [
            "defect", "absorption", "inclusion", "impurity",
            "vacancy", "缺陷", "吸收", "包裹体", "杂质", "空位"
        ],
    },

    "第一性原理": {
        "triggers": [
            "第一性原理", "dft", "first principles",
            "density functional theory", "形成能", "态密度"
        ],
        "must": [
            "first principles", "first-principles",
            "density functional theory", "dft",
            "formation energy", "density of states",
            "第一性原理", "形成能", "态密度"
        ],
        "boost": [
            "defect", "vacancy", "electronic structure",
            "optical absorption", "缺陷", "空位", "电子结构", "吸收"
        ],
    },

    "杂质": {
        "triggers": [
            "杂质", "掺杂", "impurity", "dopant", "doping"
        ],
        "must": [
            "impurity", "dopant", "doping",
            "metal ion", "transition metal",
            "杂质", "掺杂", "金属离子"
        ],
        "boost": [
            "absorption", "defect", "laser damage",
            "growth", "吸收", "缺陷", "激光损伤", "生长"
        ],
    },
}


DOMAIN_TERMS = [
    "氢空位", "质子空位", "质子缺失",
    "钾空位", "氧空位", "包裹体", "散射中心",
    "位错", "开裂", "裂纹", "热应力",
    "过饱和度", "快速生长", "籽晶", "固定方式",
    "亚表面损伤", "激光损伤", "损伤阈值",
    "弱吸收", "第一性原理", "形成能", "态密度",
    "电子结构", "杂质", "掺杂", "氘化"
]


def _term_pattern(term):
    """
    英文短词使用边界匹配。
    例如 KDP 不再错误匹配 DKDP。
    """
    term = str(term).lower().strip()

    if re.fullmatch(r"[a-z0-9+\-]+", term):
        return rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"

    return re.escape(term)


def _series_hit(series, terms):
    s = series.fillna("").astype(str).str.lower()
    result = pd.Series(False, index=s.index)

    for term in terms:
        result |= s.str.contains(
            _term_pattern(term),
            regex=True
        )

    return result


def _series_count(series, terms):
    s = series.fillna("").astype(str).str.lower()
    result = pd.Series(0.0, index=s.index)

    for term in terms:
        result += s.str.contains(
            _term_pattern(term),
            regex=True
        ).astype(float)

    return result


def _detect_intent(query):
    q = str(query or "").lower()

    for intent, rule in INTENT_RULES.items():
        for trigger in rule["triggers"]:
            if trigger.lower() in q:
                return intent, rule

    return None, None


def _generic_terms(query):
    q = str(query or "").lower()

    terms = re.findall(
        r"[a-z][a-z0-9+\-]{1,}",
        q
    )

    for term in DOMAIN_TERMS:
        if term in query:
            terms.append(term)

    stop_words = {
        "为什么", "可能", "如何", "请基于",
        "文献库", "给出", "证据",
        "研究", "分析", "比较",
        "the", "and", "why", "how",
        "based", "paper", "papers"
    }

    terms = [
        x for x in terms
        if x not in stop_words
    ]

    return list(dict.fromkeys(terms))


def search_papers(df, q, top_k=100, scope="相关池"):

    work = df.copy()

    # ---------- 检索范围 ----------
    if scope == "相关池":
        work = work[
            work["V5相关池"] == "KDP/DKDP相关池"
        ]

    elif scope == "S+A":
        work = work[
            work["V5推荐等级"].isin(
                ["S 核心 50", "A 重点 150"]
            )
        ]

    if work.empty:
        return work


    # ---------- 没输入问题 ----------
    if not q:
        return work.sort_values(
            ["V5科研优先分", "被引次数"],
            ascending=False
        ).head(top_k)


    # ---------- 准备字段 ----------
    title = work["题名"].fillna("").astype(str)

    keywords = (
        work["作者关键词"].fillna("").astype(str)
        + " "
        + work["Keywords Plus"].fillna("").astype(str)
        + " "
        + work["详细二级分类"].fillna("").astype(str)
    )

    abstract = work["摘要"].fillna("").astype(str)

    conclusion = (
        work["自动主要结论"].fillna("").astype(str)
        + " "
        + work["自动研究问题"].fillna("").astype(str)
    )

    all_text = (
        title + " "
        + keywords + " "
        + abstract + " "
        + conclusion
    )


    # ---------- 基础分 ----------
    score = (
        work["V5科研优先分"].fillna(0)
        / 40.0
    )


    # ---------- 普通关键词得分 ----------
    generic_terms = _generic_terms(q)

    for term in generic_terms:

        score += (
            _series_hit(title, [term]).astype(float)
            * 9.0
        )

        score += (
            _series_hit(keywords, [term]).astype(float)
            * 6.0
        )

        score += (
            _series_hit(conclusion, [term]).astype(float)
            * 3.5
        )

        score += (
            _series_hit(abstract, [term]).astype(float)
            * 1.5
        )


    # ==================================
    # 材料体系约束
    # ==================================

    q_lower = str(q).lower()

    kdp_terms = [
        "kdp",
        "kh2po4",
        "potassium dihydrogen phosphate"
    ]

    dkdp_terms = [
        "dkdp",
        "kd2po4",
        "deuterated potassium dihydrogen phosphate"
    ]

    adp_terms = [
        "adp",
        "ammonium dihydrogen phosphate"
    ]

    kdp_hit = _series_hit(all_text, kdp_terms)
    dkdp_hit = _series_hit(all_text, dkdp_terms)
    adp_hit = _series_hit(all_text, adp_terms)


    # 用户明确问 KDP 时
    if "kdp" in q_lower and "dkdp" not in q_lower:

        score += (
            kdp_hit.astype(float)
            * 12.0
        )

        # DKDP/ADP可作为比较背景，但不能压过KDP
        score += (
            dkdp_hit.astype(float)
            * 2.0
        )

        score += (
            adp_hit.astype(float)
            * 1.5
        )


    # ==================================
    # 科研主题识别
    # ==================================

    intent_name, rule = _detect_intent(q)

    evidence_level = pd.Series(
        "背景/间接证据",
        index=work.index
    )

    if rule is not None:

        must_title = _series_count(
            title,
            rule["must"]
        )

        must_keywords = _series_count(
            keywords,
            rule["must"]
        )

        must_abstract = _series_count(
            abstract,
            rule["must"]
        )

        must_conclusion = _series_count(
            conclusion,
            rule["must"]
        )


        # 任何位置直接命中核心科研对象
        direct_mask = (
            (must_title > 0)
            | (must_keywords > 0)
            | (must_abstract > 0)
            | (must_conclusion > 0)
        )


        # 直接文献额外强加分
        score += (
            direct_mask.astype(float)
            * 32.0
        )


        # 题名命中权重最高
        score += must_title * 18.0

        score += must_keywords * 10.0

        score += must_conclusion * 6.0

        score += must_abstract * 3.0


        # 目标性质/机理加分
        boost_count = (
            _series_count(title, rule["boost"])
            * 5.0
            +
            _series_count(keywords, rule["boost"])
            * 3.0
            +
            _series_count(abstract, rule["boost"])
            * 1.0
        )

        score += boost_count


        # ==================================
        # “强直接证据”
        # ==================================

        if "kdp" in q_lower and "dkdp" not in q_lower:

            strong_direct = (
                direct_mask
                & kdp_hit
            )

        else:

            strong_direct = direct_mask


        score += (
            strong_direct.astype(float)
            * 25.0
        )


        evidence_level.loc[
            direct_mask
        ] = "直接主题证据"

        evidence_level.loc[
            strong_direct
        ] = "强直接证据"


        # ==================================
        # 质量门
        # ==================================

        strong_n = int(
            strong_direct.sum()
        )

        direct_n = int(
            direct_mask.sum()
        )


        # 有足够强直接证据时，
        # 禁止泛背景论文占据前排
        if strong_n >= 3:

            candidate_mask = (
                strong_direct
                | direct_mask
            )

        # 强证据少，但主题直接文献至少3篇
        elif direct_n >= 3:

            candidate_mask = direct_mask

        # 文献库确实很少时才允许背景论文补充
        else:

            candidate_mask = (
                score > 0
            )

    else:

        candidate_mask = (
            score > 0
        )


    # ---------- 最终结果 ----------
    out = work.copy()

    out["_检索得分"] = score

    out["_证据层级"] = evidence_level


    out = out[
        candidate_mask
    ].copy()


    if out.empty:

        out = work.copy()

        out["_检索得分"] = score

        out["_证据层级"] = (
            "背景/间接证据"
        )


    evidence_rank = {
        "强直接证据": 3,
        "直接主题证据": 2,
        "背景/间接证据": 1
    }

    out["_证据排序"] = (
        out["_证据层级"]
        .map(evidence_rank)
        .fillna(0)
    )


    out = out.sort_values(
        [
            "_证据排序",
            "_检索得分",
            "V5科研优先分",
            "被引次数"
        ],
        ascending=[
            False,
            False,
            False,
            False
        ]
    )


    return (
        out.head(top_k)
        .drop(
            columns=[
                "_证据排序"
            ]
        )
    )def topic_search(df,topic,top_k=100,scope="相关池"):return search_papers(df," ".join(TOPICS.get(topic,[topic])),top_k,scope)
def topic_stats(df):
    r=df[df["V5相关池"]=="KDP/DKDP相关池"];maxy=int(r["年份"].max()) if len(r) else 2026;rows=[]
    for t in TOPICS:
        d=topic_search(r,t,len(r),"全部")
        rows.append({"专题":t,"总文献":len(d),"近5年":int((d["年份"]>=maxy-4).sum()),"S/A":int(d["V5推荐等级"].isin(["S 核心 50","A 重点 150"]).sum()),"DFT":int(d["_方法标签"].str.contains("DFT/第一性原理",regex=False).sum())})
    return pd.DataFrame(rows)
def compact_context(df,maxp=15):
    blocks=[];src=[]
    for i,(_,r) in enumerate(df.head(maxp).iterrows(),1):
        blocks.append(f"[P{i}] 题名:{_t(r['题名'])}\n年份:{r['年份']}\n期刊:{_t(r['期刊'])}\nDOI:{_t(r['DOI'])}\n等级:{r['V5推荐等级']}\n方法:{r['_方法标签']}\n摘要:{_t(r['摘要'])[:2200]}\n结论:{_t(r['自动主要结论'])[:900]}")
        src.append({"编号":f"P{i}","题名":_t(r["题名"]),"年份":r["年份"],"期刊":_t(r["期刊"]),"DOI":_t(r["DOI"])})
    return "\n\n".join(blocks),src
def offline_summary(df,topic=""):
    if df.empty:return "没有检索到匹配文献。"
    return f"### {topic or '当前结果'}：离线证据概览\n- 文献数：**{len(df)}**\n- 主要来源：{df['缺陷/应力来源'].value_counts().head(3).to_dict()}\n- 主要机制：{df['作用机制'].value_counts().head(3).to_dict()}\n- 主要结果：{df['宏观结果'].value_counts().head(3).to_dict()}\n\n> 正式科研结论仍应核对论文全文。"
