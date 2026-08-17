
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


INTENT_RULES={
"氢空位":{
"triggers":["氢空位","质子空位","质子缺失","hydrogen vacancy","proton vacancy","h vacancy"],
"must":["氢空位","质子空位","质子缺失","hydrogen vacancy","proton vacancy","h vacancy","hydrogen defect"],
"boost":["extra absorption","optical absorption","absorption","defect level","defect state","density of states","electronic structure","localized state","额外吸收","光吸收","缺陷能级","缺陷态","态密度","电子结构","局域态"]},
"晶体开裂":{
"triggers":["开裂","裂纹","断裂","crack","cracking","fracture","microcrack"],
"must":["crack","cracking","fracture","microcrack","开裂","裂纹","断裂"],
"boost":["thermal stress","residual stress","stress concentration","inclusion","dislocation","seed crystal","热应力","残余应力","应力集中","包裹体","位错","籽晶"]},
"包裹体":{
"triggers":["包裹体","夹杂","散射中心","inclusion","scattering center"],
"must":["inclusion","solution inclusion","particle inclusion","scattering center","包裹体","夹杂","散射中心"],
"boost":["stress","strain","crack","laser damage","growth defect","应力","应变","裂纹","激光损伤","生长缺陷"]},
"第一性原理":{
"triggers":["第一性原理","dft","first principles","density functional theory","形成能","态密度"],
"must":["first principles","first-principles","density functional theory","dft","formation energy","density of states","第一性原理","形成能","态密度"],
"boost":["defect","vacancy","electronic structure","optical absorption","缺陷","空位","电子结构","吸收"]},
"激光损伤":{
"triggers":["激光损伤","损伤阈值","lidt","laser damage","damage threshold"],
"must":["laser damage","laser-induced damage","lidt","damage threshold","breakdown","激光损伤","损伤阈值"],
"boost":["defect","absorption","inclusion","impurity","vacancy","缺陷","吸收","包裹体","杂质","空位"]},
"亚表面损伤":{
"triggers":["亚表面","加工损伤","subsurface damage","sub-surface damage","polishing"],
"must":["subsurface damage","sub-surface damage","surface damage","polishing","grinding","diamond turning","fly cutting","亚表面损伤","表面损伤","抛光","研磨","飞切"],
"boost":["crack","microcrack","residual stress","laser damage","裂纹","残余应力","激光损伤"]},
"杂质":{
"triggers":["杂质","掺杂","impurity","dopant","doping"],
"must":["impurity","dopant","doping","metal ion","transition metal","杂质","掺杂","金属离子"],
"boost":["absorption","defect","laser damage","growth","吸收","缺陷","激光损伤","生长"]}
}

def _pattern(term):
    term=str(term).lower().strip()
    if re.fullmatch(r"[a-z0-9+\-]+",term):
        return rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.escape(term)

def _series_hit(series,terms):
    s=series.fillna("").astype(str).str.lower()
    hit=pd.Series(False,index=s.index)
    for term in terms:
        hit |= s.str.contains(_pattern(term),regex=True)
    return hit

def _series_count(series,terms):
    s=series.fillna("").astype(str).str.lower()
    out=pd.Series(0.0,index=s.index)
    for term in terms:
        out += s.str.contains(_pattern(term),regex=True).astype(float)
    return out

def _detect_intent(q):
    q=str(q or "").lower()
    for name,rule in INTENT_RULES.items():
        if any(str(t).lower() in q for t in rule["triggers"]):
            return name,rule
    return None,None

def _tokens(q):
    q=str(q or "").lower()
    terms=re.findall(r"[a-z0-9+\-]{2,}|[\u4e00-\u9fff]{2,}",q)
    stop={"为什么","如何","可能","请基于","文献库","给出","证据","研究","分析","比较","the","and","why","how","based"}
    return [x for x in dict.fromkeys(terms) if x not in stop]

def search_papers(df,q,top_k=100,scope="相关池"):
    w=df.copy()
    if scope=="相关池":
        w=w[w["V5相关池"]=="KDP/DKDP相关池"]
    elif scope=="S+A":
        w=w[w["V5推荐等级"].isin(["S 核心 50","A 重点 150"])]
    if w.empty:
        return w
    if not str(q or "").strip():
        out=w.sort_values(["V5科研优先分","被引次数"],ascending=False).head(top_k).copy()
        out["_证据层级"]="背景/间接证据"
        return out

    title=w["题名"].fillna("").astype(str)
    keywords=(w["作者关键词"].fillna("").astype(str)+" "+w["Keywords Plus"].fillna("").astype(str)+" "+w["详细二级分类"].fillna("").astype(str))
    abstract=w["摘要"].fillna("").astype(str)
    conclusion=w["自动主要结论"].fillna("").astype(str)+" "+w["自动研究问题"].fillna("").astype(str)
    all_text=title+" "+keywords+" "+abstract+" "+conclusion

    score=w["V5科研优先分"].fillna(0)/40.0
    for t in _tokens(q):
        score += _series_hit(title,[t]).astype(float)*9
        score += _series_hit(keywords,[t]).astype(float)*6
        score += _series_hit(conclusion,[t]).astype(float)*3.5
        score += _series_hit(abstract,[t]).astype(float)*1.5

    ql=str(q).lower()
    kdp_hit=_series_hit(all_text,["kdp","kh2po4","potassium dihydrogen phosphate"])
    dkdp_hit=_series_hit(all_text,["dkdp","kd2po4","deuterated potassium dihydrogen phosphate"])
    adp_hit=_series_hit(all_text,["adp","ammonium dihydrogen phosphate"])
    if "kdp" in ql and "dkdp" not in ql:
        score += kdp_hit.astype(float)*12
        score += dkdp_hit.astype(float)*2
        score += adp_hit.astype(float)*1.5

    _,rule=_detect_intent(q)
    evidence=pd.Series("背景/间接证据",index=w.index,dtype="object")
    candidate=score>0
    if rule is not None:
        mt=_series_count(title,rule["must"])
        mk=_series_count(keywords,rule["must"])
        ma=_series_count(abstract,rule["must"])
        mc=_series_count(conclusion,rule["must"])
        direct=(mt>0)|(mk>0)|(ma>0)|(mc>0)
        score += direct.astype(float)*32 + mt*18 + mk*10 + mc*6 + ma*3
        score += _series_count(title,rule["boost"])*5 + _series_count(keywords,rule["boost"])*3 + _series_count(abstract,rule["boost"])
        strong=(direct & kdp_hit) if ("kdp" in ql and "dkdp" not in ql) else direct
        score += strong.astype(float)*25
        evidence.loc[direct]="直接主题证据"
        evidence.loc[strong]="强直接证据"
        if int(strong.sum())>=3:
            candidate=strong|direct
        elif int(direct.sum())>=3:
            candidate=direct

    out=w.copy()
    out["_检索得分"]=score
    out["_证据层级"]=evidence
    out=out[candidate].copy()
    if out.empty:
        out=w.copy(); out["_检索得分"]=score; out["_证据层级"]="背景/间接证据"
    rank={"强直接证据":3,"直接主题证据":2,"背景/间接证据":1}
    out["_证据排序"]=out["_证据层级"].map(rank).fillna(0)
    out=out.sort_values(["_证据排序","_检索得分","V5科研优先分","被引次数"],ascending=[False,False,False,False])
    return out.head(top_k).drop(columns=["_证据排序"])

def topic_search(df,topic,top_k=100,scope="相关池"):
    return search_papers(df," ".join(TOPICS.get(topic,[topic])),top_k,scope)

def topic_stats(df):
    r=df[df["V5相关池"]=="KDP/DKDP相关池"]
    maxy=int(r["年份"].max()) if len(r) else 2026
    rows=[]
    for t in TOPICS:
        d=topic_search(r,t,len(r),"全部")
        rows.append({"专题":t,"总文献":len(d),"近5年":int((d["年份"]>=maxy-4).sum()) if len(d) else 0,"S/A":int(d["V5推荐等级"].isin(["S 核心 50","A 重点 150"]).sum()) if len(d) else 0,"DFT":int(d["_方法标签"].str.contains("DFT/第一性原理",regex=False).sum()) if len(d) else 0})
    return pd.DataFrame(rows)

def compact_context(df,maxp=15):
    blocks=[];src=[]
    for i,(_,r) in enumerate(df.head(maxp).iterrows(),1):
        blocks.append(f"[P{i}] 题名:{_t(r['题名'])}\n年份:{r['年份']}\n期刊:{_t(r['期刊'])}\nDOI:{_t(r['DOI'])}\n等级:{r['V5推荐等级']}\n证据层级:{r.get('_证据层级','未标记')}\n方法:{r['_方法标签']}\n摘要:{_t(r['摘要'])[:2200]}\n结论:{_t(r['自动主要结论'])[:900]}")
        src.append({"编号":f"P{i}","题名":_t(r["题名"]),"年份":r["年份"],"期刊":_t(r["期刊"]),"DOI":_t(r["DOI"])})
    return "\n\n".join(blocks),src

def offline_summary(df,topic=""):
    if df.empty:
        return "没有检索到匹配文献。"
    ev=df["_证据层级"].value_counts().to_dict() if "_证据层级" in df.columns else {}
    return f"### {topic or '当前结果'}：离线证据概览\n- 文献数：**{len(df)}**\n- 证据层级：{ev}\n- 主要来源：{df['缺陷/应力来源'].value_counts().head(3).to_dict()}\n- 主要机制：{df['作用机制'].value_counts().head(3).to_dict()}\n- 主要结果：{df['宏观结果'].value_counts().head(3).to_dict()}\n\n> 正式科研结论仍应核对论文全文。"
