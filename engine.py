
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

CORE_TOPICS = {
    k: v for k, v in TOPICS.items()
    if k != "DKDP氘化与同位素"
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

@st.cache_resource(show_spinner="首次载入文献库……")
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

    # ------------------------------------------------------------------
    # 文献证据解析 V2
    # 不再把“程序没识别出来”和“论文没有研究”都混成“未明确”。
    # 当前层级基于题名、摘要、关键词、研究方法、自动研究问题和自动主要结论。
    # ------------------------------------------------------------------
    evidence_text = df["_text"]
    abstract_len = df["摘要"].fillna("").astype(str).str.len()
    conclusion_len = df["自动主要结论"].fillna("").astype(str).str.len()
    question_len = df["自动研究问题"].fillna("").astype(str).str.len()
    method_raw_len = df["研究方法"].fillna("").astype(str).str.len()

    has_abstract_evidence = (abstract_len >= 120) | (conclusion_len >= 80) | (question_len >= 60)
    has_min_evidence = (abstract_len >= 50) | (conclusion_len >= 35) | (question_len >= 30)

    # 1. 缺陷 / 应力来源：尽量把“基础物性/其他”缩到真正的基础支撑文献。
    df["缺陷/应力来源"] = np.select(
        [
            _series_hit(evidence_text, [
                "hydrogen vacancy","proton vacancy","potassium vacancy","oxygen vacancy",
                "point defect","vacancy defect","interstitial defect",
                "氢空位","质子空位","钾空位","氧空位","点缺陷","间隙缺陷",
            ]),
            _series_hit(evidence_text, [
                "impurity","dopant","doping","foreign ion","metal ion",
                "杂质","掺杂","外来离子","金属离子",
            ]),
            _series_hit(evidence_text, [
                "solution inclusion","particle inclusion","inclusion","scattering center",
                "包裹体","夹杂","散射中心",
            ]),
            _series_hit(evidence_text, [
                "dislocation","growth striation","lattice strain","residual strain",
                "位错","生长条纹","晶格应变","残余应变",
            ]),
            _series_hit(evidence_text, [
                "seed crystal","seed orientation","seed holder","constraint",
                "籽晶","籽晶取向","固定方式","机械约束",
            ]),
            _series_hit(evidence_text, [
                "supersaturation","growth sector","growth interface","rapid growth",
                "fast growth","growth defect","solution growth","crystal growth",
                "过饱和度","生长界面","生长扇区","快速生长","生长缺陷","溶液生长",
            ]),
            _series_hit(evidence_text, [
                "subsurface damage","sub-surface damage","surface damage","polishing",
                "grinding","diamond turning","fly cutting","machining",
                "亚表面损伤","表面损伤","抛光","研磨","金刚石车削","飞切","加工损伤",
            ]),
            _series_hit(evidence_text, [
                "thermal stress","residual stress","concentration gradient","thermal gradient",
                "cooling rate","temperature gradient",
                "热应力","残余应力","浓度梯度","温度梯度","降温速率",
            ]),
        ],
        [
            "本征点缺陷",
            "杂质/掺杂",
            "包裹体/散射中心",
            "位错/晶格应变",
            "籽晶/固定约束",
            "晶体生长条件/界面",
            "加工引入缺陷",
            "热/浓度应力",
        ],
        default="基础物性/其他",
    )

    # 2. 作用机制：扩展机制词典，降低“机制未明确”比例。
    mechanism_masks = [
        _series_hit(evidence_text, [
            "localized absorption","local absorption","absorption precursor","energy deposition",
            "photoionization","multiphoton","avalanche ionization",
            "局域吸收","吸收前驱体","能量沉积","光电离","多光子","雪崩电离",
        ]),
        _series_hit(evidence_text, [
            "electronic structure","defect level","defect state","density of states",
            "band gap","localized state","charge density",
            "电子结构","缺陷能级","缺陷态","态密度","带隙","局域态","电荷密度",
        ]),
        _series_hit(evidence_text, [
            "thermal stress","residual stress","stress concentration","stress field",
            "fracture mechanics","crack propagation","crack initiation",
            "热应力","残余应力","应力集中","应力场","断裂力学","裂纹扩展","裂纹萌生",
        ]),
        _series_hit(evidence_text, [
            "lattice distortion","lattice relaxation","local strain","elastic distortion",
            "晶格畸变","晶格弛豫","局域应变","弹性畸变",
        ]),
        _series_hit(evidence_text, [
            "hydrogen bond","proton transfer","proton dynamics","hydrogen-bond network",
            "氢键","质子转移","质子动力学","氢键网络",
        ]),
        _series_hit(evidence_text, [
            "scattering mechanism","rayleigh scattering","mie scattering","refractive index mismatch",
            "inclusion scattering","散射机制","瑞利散射","米氏散射","折射率失配","包裹体散射",
        ]),
        _series_hit(evidence_text, [
            "growth interface","interface instability","mass transfer","mass transport",
            "solute transport","convection","boundary layer",
            "生长界面","界面失稳","传质","溶质输运","对流","边界层",
        ]),
        _series_hit(evidence_text, [
            "subsurface damage evolution","damage evolution","plastic deformation",
            "brittle fracture","microcrack formation",
            "亚表面损伤演化","损伤演化","塑性变形","脆性断裂","微裂纹形成",
        ]),
        _series_hit(evidence_text, [
            "inclusion","solution inclusion","particle inclusion","scattering center",
            "包裹体","夹杂","散射中心",
        ]),
    ]

    mechanism_values = [
        "局域吸收/能量沉积",
        "电子结构/缺陷态",
        "热-力应力/裂纹",
        "晶格畸变/局域应变",
        "氢键/质子动力学",
        "散射/折射率失配",
        "生长界面/传质",
        "加工损伤演化",
        "包裹体/散射",
    ]

    df["作用机制"] = np.select(
        mechanism_masks,
        mechanism_values,
        default="",
    )

    fundamental_mask = _series_hit(evidence_text, [
        "electronic band","band structure","optical property","elastic constant",
        "dielectric","refractive index","phase transition","crystal structure",
        "nonlinear optical","electro-optic",
        "能带结构","光学性质","弹性常数","介电","折射率","相变","晶体结构",
        "非线性光学","电光",
    ])

    df.loc[df["作用机制"].eq("") & fundamental_mask, "作用机制"] = "未讨论机制/基础性质"
    df.loc[df["作用机制"].eq("") & has_abstract_evidence, "作用机制"] = "待核验（摘要未明确）"
    df.loc[df["作用机制"].eq("") & ~has_abstract_evidence, "作用机制"] = "摘要证据不足"

    # 3. 研究结果 / 宏观后果：允许“基础物性（非失效）”，避免把不适用误写成不知道。
    result_masks = [
        _series_hit(evidence_text, [
            "crack initiation","crack propagation","crack","fracture","microcrack",
            "开裂","裂纹","断裂","微裂纹",
        ]),
        _series_hit(evidence_text, [
            "laser-induced damage","laser damage","lidt","damage threshold","breakdown threshold",
            "激光损伤","损伤阈值","击穿阈值",
        ]),
        _series_hit(evidence_text, [
            "weak absorption","optical absorption","absorption coefficient","transmission",
            "optical response","localized absorption",
            "弱吸收","光学吸收","吸收系数","透过率","光学响应","局域吸收",
        ]),
        _series_hit(evidence_text, [
            "scattering","optical homogeneity","optical uniformity","scattering particle",
            "散射","光学均匀性","光学均一性","散射颗粒",
        ]),
        _series_hit(evidence_text, [
            "growth quality","crystal quality","defect density","growth rate","morphology",
            "晶体质量","缺陷密度","生长速率","生长质量","形貌",
        ]),
        _series_hit(evidence_text, [
            "subsurface damage","surface damage","surface roughness","machining damage",
            "亚表面损伤","表面损伤","表面粗糙度","加工损伤",
        ]),
        _series_hit(evidence_text, [
            "mechanical property","fracture toughness","elastic modulus","stress distribution",
            "机械性能","断裂韧性","弹性模量","应力分布",
        ]),
    ]

    result_values = [
        "开裂/断裂",
        "激光损伤/LIDT",
        "吸收/光学响应",
        "散射/光学均匀性",
        "生长质量/缺陷密度",
        "表面/亚表面损伤",
        "力学/应力响应",
    ]

    df["宏观结果"] = np.select(result_masks, result_values, default="")
    df.loc[df["宏观结果"].eq("") & fundamental_mask, "宏观结果"] = "基础物性（非失效）"
    df.loc[df["宏观结果"].eq("") & has_abstract_evidence, "宏观结果"] = "待核验（摘要未明确）"
    df.loc[df["宏观结果"].eq("") & ~has_abstract_evidence, "宏观结果"] = "摘要证据不足"

    # 4. 方法允许多标签；避免一篇同时有“实验+DFT”却只显示一个。
    method_rules = [
        ("DFT/第一性原理", [
            "density functional theory","first principles","first-principles"," dft ",
            "formation energy","density of states","band structure",
            "第一性原理","形成能","态密度","能带结构",
        ]),
        ("分子动力学", [
            "molecular dynamics","md simulation","atomistic simulation",
            "分子动力学","原子模拟",
        ]),
        ("有限元/连续介质", [
            "finite element","fem","multiphysics","continuum mechanics",
            "有限元","多物理场","连续介质",
        ]),
        ("晶体生长实验", [
            "solution growth","crystal growth","rapid growth","fast growth",
            "growth experiment","seed crystal",
            "溶液生长","晶体生长","快速生长","籽晶",
        ]),
        ("激光损伤测试", [
            "laser damage test","lidt measurement","damage threshold measurement",
            "laser-induced damage test","激光损伤测试","损伤阈值测试",
        ]),
        ("光热/弱吸收", [
            "photothermal","thermal lens","photothermal common-path interferometry",
            "weak absorption","pci",
            "光热","热透镜","弱吸收",
        ]),
        ("光谱/显微表征", [
            "raman","ftir","infrared spectroscopy","spectroscopy","afm","sem","tem",
            "microscopy","xrd","x-ray diffraction","x-ray topography",
            "拉曼","红外","光谱","显微","原子力显微","扫描电镜","透射电镜",
            "x射线衍射","x射线形貌",
        ]),
        ("光学性能表征", [
            "uv-vis","transmission spectrum","absorption spectrum","refractive index",
            "optical measurement","透过光谱","吸收光谱","折射率","光学测试",
        ]),
        ("力学/应力表征", [
            "mechanical test","fracture toughness","elastic modulus","residual stress measurement",
            "力学测试","断裂韧性","弹性模量","残余应力测量",
        ]),
    ]

    method_labels = pd.Series("", index=df.index, dtype="object")
    for label, terms in method_rules:
        hit = _series_hit(evidence_text, terms)
        first = hit & method_labels.eq("")
        more = hit & ~method_labels.eq("")
        method_labels.loc[first] = label
        method_labels.loc[more] = method_labels.loc[more] + " + " + label

    # 最多保留3个主方法，避免表格一格过长。
    method_labels = method_labels.map(
        lambda x: " + ".join(str(x).split(" + ")[:3]) if x else ""
    )

    method_labels.loc[
        method_labels.eq("") & (method_raw_len > 8)
    ] = "实验/方法待细分"
    method_labels.loc[
        method_labels.eq("") & has_abstract_evidence
    ] = "待核验（摘要未明确）"
    method_labels.loc[
        method_labels.eq("") & ~has_abstract_evidence
    ] = "摘要证据不足"

    df["_方法标签"] = method_labels


    if (df["材料相关性"] == "KDP/DKDP相关").any():
        related = df["材料相关性"].eq("KDP/DKDP相关")
    else:
        related = (
            _series_hit(df["_text"], ["kdp","kh2po4","potassium dihydrogen phosphate"])
            | _series_hit(df["_text"], ["dkdp","kd2po4","deuterated potassium dihydrogen phosphate"])
        )

    # 材料层级：默认以 KDP 为核心研究对象。
    # DKDP 仅作为同位素对照/扩展证据，不再与 KDP 并列占据主研究层级。
    kdp_hit = _series_hit(
        df["_text"],
        ["kdp", "kh2po4", "potassium dihydrogen phosphate"],
    )
    dkdp_hit = _series_hit(
        df["_text"],
        [
            "dkdp",
            "kd2po4",
            "potassium dideuterium phosphate",
            "deuterated potassium dihydrogen phosphate",
        ],
    )

    comparison = related & kdp_hit & dkdp_hit
    dkdp_only = related & dkdp_hit & ~kdp_hit
    kdp_primary = related & ~dkdp_only

    df["_KDP命中"] = kdp_hit
    df["_DKDP命中"] = dkdp_hit
    df["_KDP主研究"] = kdp_primary
    df["材料层级"] = np.select(
        [comparison, dkdp_only, kdp_primary],
        ["KDP-DKDP对照", "DKDP扩展", "KDP主线"],
        default="非核心/待核",
    )

    # 保留旧字段值以兼容既有页面/缓存；新的页面通过 material_scope() 控制材料范围。
    df["V5相关池"] = np.where(related, "KDP/DKDP相关池", "非核心/待核")

    # ------------------------------------------------------------------
    # 证据完整度与可信度审计
    # “科研价值高”与“当前证据解析完整”分开计分。
    # ------------------------------------------------------------------
    kdp_direct_text = (
        df["题名"].fillna("").astype(str)
        + " " + df["摘要"].fillna("").astype(str)
        + " " + df["作者关键词"].fillna("").astype(str)
        + " " + df["Keywords Plus"].fillna("").astype(str)
    )

    kdp_direct = _series_hit(
        kdp_direct_text,
        ["kdp", "kh2po4", "potassium dihydrogen phosphate"],
    )

    df["研究对象确认"] = np.select(
        [
            kdp_direct & ~dkdp_only,
            comparison,
            kdp_primary & ~kdp_direct,
            dkdp_only,
        ],
        [
            "KDP直接研究",
            "KDP-DKDP对照",
            "KDP相关支撑/待核",
            "DKDP扩展",
        ],
        default="非核心/待核",
    )

    mechanism_explicit = ~df["作用机制"].isin([
        "待核验（摘要未明确）",
        "摘要证据不足",
    ])
    result_explicit = ~df["宏观结果"].isin([
        "待核验（摘要未明确）",
        "摘要证据不足",
    ])
    method_explicit = ~df["_方法标签"].isin([
        "待核验（摘要未明确）",
        "摘要证据不足",
        "实验/方法待细分",
    ])

    # “未讨论机制/基础性质”“基础物性（非失效）”属于明确的不适用，而不是缺失。
    completeness = (
        kdp_direct.astype(float) * 15
        + has_abstract_evidence.astype(float) * 15
        + (question_len >= 30).astype(float) * 10
        + method_explicit.astype(float) * 15
        + mechanism_explicit.astype(float) * 20
        + result_explicit.astype(float) * 15
        + (conclusion_len >= 35).astype(float) * 5
        + df["DOI"].fillna("").astype(str).str.len().gt(5).astype(float) * 5
    )
    df["证据完整度分"] = completeness.clip(0, 100).round(0).astype(int)

    df["证据完整度状态"] = pd.cut(
        df["证据完整度分"],
        bins=[-1, 54, 69, 84, 100],
        labels=["需全文核验", "摘要级", "较完整", "完整"],
    ).astype(str)

    direct_problem = _series_hit(
        evidence_text,
        [
            "defect","vacancy","impurity","dopant","inclusion","dislocation",
            "crack","fracture","thermal stress","laser damage","lidt",
            "subsurface damage","growth defect","supersaturation",
            "缺陷","空位","杂质","掺杂","包裹体","位错","开裂","裂纹",
            "热应力","激光损伤","损伤阈值","亚表面损伤","生长缺陷","过饱和度",
        ],
    )

    foundation_support = fundamental_mask | _series_hit(
        evidence_text,
        [
            "elastic constant","thermal expansion","thermal conductivity",
            "electronic structure","hydrogen bond","optical property",
            "弹性常数","热膨胀","热导率","电子结构","氢键","基础光学性质",
        ],
    )

    df["证据角色"] = np.select(
        [
            kdp_primary & direct_problem & (df["证据完整度分"] >= 70),
            kdp_primary & foundation_support & (df["证据完整度分"] >= 65),
            kdp_primary & direct_problem,
            kdp_primary,
        ],
        [
            "直接核心证据",
            "基础支撑证据",
            "直接主题/待核验",
            "扩展/待核证据",
        ],
        default="非核心",
    )

    # 科研价值分：仍保留原有综合重要度、被引与主题价值。
    value_score = (
        df["综合重要度"].clip(0, 100) * 0.66
        + np.log1p(df["被引次数"].clip(lower=0)) / np.log(201) * 11
        + direct_problem.astype(float) * 13
        + kdp_direct.astype(float) * 7
    )
    df["V5科研优先分"] = value_score.clip(0, 100).round(1)

    role_bonus = df["证据角色"].map({
        "直接核心证据": 8.0,
        "基础支撑证据": 5.0,
        "直接主题/待核验": 2.0,
        "扩展/待核证据": 0.0,
        "非核心": -5.0,
    }).fillna(0.0)

    core_rank = (
        df["V5科研优先分"] * 0.68
        + df["证据完整度分"] * 0.27
        + role_bonus
    )
    df["V5核心排序分"] = core_rank.clip(0, 100).round(1)

    # ------------------------------------------------------------------
    # 分级：S 层新增“证据完整度 >= 70”硬门槛。
    # 不再因为期刊、被引或主题分高就自动进入核心证据库。
    # ------------------------------------------------------------------
    tier = pd.Series("C 扩展/背景", index=df.index, dtype="object")

    s_eligible = (
        kdp_primary
        & (df["证据完整度分"] >= 70)
        & df["证据角色"].isin(["直接核心证据", "基础支撑证据"])
    )
    s_ranked = df[s_eligible].sort_values(
        ["V5核心排序分", "V5科研优先分", "被引次数", "年份"],
        ascending=False,
    )
    s_idx = s_ranked.index[:50]
    tier.loc[s_idx] = "S 核心 50"

    remaining = df[kdp_primary & ~df.index.isin(s_idx)].sort_values(
        ["V5核心排序分", "V5科研优先分", "被引次数", "年份"],
        ascending=False,
    )
    a_idx = remaining.index[:150]
    b_idx = remaining.index[150:950]
    tier.loc[a_idx] = "A 重点 150"
    tier.loc[b_idx] = "B 扩展 800"

    tier.loc[df.index[dkdp_only]] = "C 扩展/背景"
    tier.loc[df.index[~related]] = "D 非核心/待核"
    df["V5推荐等级"] = tier

    # S1 / S2 不是再造一个评分，而是告诉用户“这篇核心文献扮演什么证据角色”。
    core_level = pd.Series("—", index=df.index, dtype="object")
    s1 = df.index.isin(s_idx) & df["证据角色"].eq("直接核心证据")
    s2 = df.index.isin(s_idx) & ~s1
    core_level.loc[s1] = "S1 直接核心"
    core_level.loc[s2] = "S2 基础支撑"
    core_level.loc[df.index.isin(a_idx)] = "A 重点/待精读"
    core_level.loc[
        kdp_primary
        & df["证据完整度状态"].isin(["需全文核验", "摘要级"])
    ] = "需核验"
    df["核心证据层级"] = core_level

    # --------------------------------------------------------------
    # 证据使用等级：这是“当前数据库条件下的可用性等级”，不是论文真伪评分。
    # 目的：告诉后续AI/方向决策哪些文献可以支撑重点论证，哪些只能当线索。
    # --------------------------------------------------------------
    doi_ok = df["DOI"].fillna("").astype(str).str.len().gt(5)

    use_grade = np.select(
        [
            kdp_primary
            & df["证据角色"].eq("直接核心证据")
            & (df["证据完整度分"] >= 85)
            & doi_ok,
            kdp_primary
            & df["证据角色"].isin(["直接核心证据", "基础支撑证据"])
            & (df["证据完整度分"] >= 70),
            kdp_primary
            & (df["证据完整度分"] >= 55),
        ],
        [
            "A 可用于重点论证",
            "B 可用于辅助论证",
            "C 线索/需全文核验",
        ],
        default="D 不用于强结论",
    )

    df["证据使用等级"] = use_grade

    df["证据用途说明"] = np.select(
        [
            df["证据使用等级"].eq("A 可用于重点论证"),
            df["证据使用等级"].eq("B 可用于辅助论证"),
            df["证据使用等级"].eq("C 线索/需全文核验"),
        ],
        [
            "可作为重点论证证据；关键数值仍应回查原文",
            "建议与其他独立证据交叉使用",
            "仅用于发现线索；形成结论前应核对全文",
        ],
        default="当前信息不足，不用于强结论",
    )

    return df


def material_scope(df, mode="KDP主线"):
    """
    默认研究对象为 KDP。
    - KDP主线：KDP直接文献 + 同时讨论KDP/DKDP的对照文献
    - DKDP对照：显式DKDP/氘化文献，仅在需要时调用
    - 全部相关：原KDP/DKDP相关池，用于审计和扩展检索
    - 全库：不做材料范围过滤
    """
    if df.empty:
        return df.copy()

    if mode in {"KDP主线", "相关池"}:
        if "_KDP主研究" in df.columns:
            return df[df["_KDP主研究"]].copy()
        related = df["V5相关池"].eq("KDP/DKDP相关池")
        dkdp = _series_hit(df["_text"], ["dkdp", "kd2po4", "deuterated potassium dihydrogen phosphate"])
        kdp = _series_hit(df["_text"], ["kdp", "kh2po4", "potassium dihydrogen phosphate"])
        return df[related & ~(dkdp & ~kdp)].copy()

    if mode == "DKDP对照":
        if "_DKDP命中" in df.columns:
            return df[df["_DKDP命中"] & df["V5相关池"].eq("KDP/DKDP相关池")].copy()
        return df[
            df["V5相关池"].eq("KDP/DKDP相关池")
            & _series_hit(df["_text"], ["dkdp", "kd2po4", "deuterated potassium dihydrogen phosphate"])
        ].copy()

    if mode in {"全部相关", "相关扩展"}:
        return df[df["V5相关池"] == "KDP/DKDP相关池"].copy()

    return df.copy()


def search_papers(df, q, top_k=100, scope="相关池"):
    work = df.copy()
    if scope in {"相关池", "KDP主线"}:
        work = material_scope(work, "KDP主线")
    elif scope in {"全部相关", "相关扩展"}:
        work = material_scope(work, "全部相关")
    elif scope == "DKDP对照":
        work = material_scope(work, "DKDP对照")
    elif scope == "S+A":
        work = material_scope(work, "KDP主线")
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

    score = (
        work["V5科研优先分"].fillna(0) / 45.0
        + work.get("证据完整度分", pd.Series(0, index=work.index)).fillna(0) / 55.0
    )

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
        ["_证据排序","_检索得分","V5核心排序分","V5科研优先分","被引次数"],
        ascending=[False,False,False,False,False]
    )
    return out.head(top_k).drop(columns=["_证据排序"])

def topic_search(df, topic, top_k=100, scope="相关池"):
    return search_papers(df, " ".join(TOPICS.get(topic,[topic])), top_k, scope)

@st.cache_data(show_spinner=False, ttl=3600)
def topic_stats(df, material="KDP主线"):
    """
    默认统计 KDP 主研究文献。
    DKDP 同位素主题不在默认总览中高频展示；需要对照研究时可显式切到 DKDP对照。
    """
    rel = material_scope(df, material)
    max_year = int(rel["年份"].max()) if len(rel) else 2026

    topic_map = TOPICS if material == "DKDP对照" else CORE_TOPICS

    rows = []
    for topic, terms in topic_map.items():
        hit = _series_hit(rel["_text"], terms)
        d = rel[hit].copy()

        rows.append({
            "专题": topic,
            "总文献": int(len(d)),
            "近5年": int((d["年份"] >= max_year - 4).sum()) if len(d) else 0,
            "S/A": int(d["V5推荐等级"].isin(["S 核心 50", "A 重点 150"]).sum()) if len(d) else 0,
            "DFT": int(
                d["_方法标签"].str.contains("DFT/第一性原理", regex=False).sum()
            ) if len(d) else 0,
        })

    return pd.DataFrame(rows)


def compact_context(df, maxp=15):
    blocks = []
    sources = []
    for i,(_,r) in enumerate(df.head(maxp).iterrows(),1):
        blocks.append(
            f"[P{i}]\n题名：{_clean(r.get('题名',''))}\n年份：{r.get('年份','')}\n"
            f"期刊：{_clean(r.get('期刊',''))}\nDOI：{_clean(r.get('DOI',''))}\n"
            f"等级：{r.get('V5推荐等级','')}\n核心角色：{r.get('核心证据层级','—')}\n"
            f"证据使用等级：{r.get('证据使用等级','')}\n"
            f"证据完整度：{r.get('证据完整度分','')} / 100（{r.get('证据完整度状态','')}）\n"
            f"证据层级：{r.get('_证据层级','未标记')}\n"
            f"研究对象：{r.get('研究对象确认','')}\n"
            f"来源：{r.get('缺陷/应力来源','')}\n机制：{r.get('作用机制','')}\n"
            f"结果：{r.get('宏观结果','')}\n方法：{r.get('_方法标签','')}\n"
            f"摘要：{_clean(r.get('摘要',''))[:2200]}\n"
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
        f"- 主要结果：{df['宏观结果'].value_counts().head(3).to_dict()}\n"
        f"- 证据完整度：{df['证据完整度状态'].value_counts().to_dict() if '证据完整度状态' in df.columns else {}}\n\n"
        "> “摘要级/需全文核验”只能用于线索发现，不能单独支撑强科研结论。"
    )
