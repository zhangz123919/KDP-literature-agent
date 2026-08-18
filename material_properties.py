from __future__ import annotations

import pandas as pd
import streamlit as st

from research_memory import add_item
from ui import page_header, soft_note


PARAM_INFO = {
    "热膨胀系数": {"symbol":"α(T)", "why":"晶体降温时每个方向要收缩多少。KDP 各方向收缩不一致时，会产生热应变不协调。", "method":"TMA / 推杆式热膨胀仪", "sample":"定向长条；优先 [001] 与 [100]，必要时 [110] 验证", "output":"α(T)，单位通常 1/K", "model":"进入热应变 εth = αΔT"},
    "热扩散率": {"symbol":"a(T)", "why":"温度变化在晶体内部传播有多快。大晶体导热慢时，内外温差更容易保留下来。", "method":"LFA 激光闪射", "sample":"薄片/圆片；分别让热流沿 [001] 与 [100]", "output":"a(T)，常用 mm²/s 或 m²/s", "model":"与密度、比热一起得到热导率"},
    "热导率": {"symbol":"k(T)", "why":"决定温度梯度能否快速消失，是大尺寸取晶/冷却温度场的核心参数。", "method":"LFA + ρ + Cp 换算，或合适的直接导热法", "sample":"至少比较 [001] 与 [100] 热流方向", "output":"k(T)，W/(m·K)", "model":"进入热传导方程"},
    "比热": {"symbol":"Cp(T)", "why":"决定升高或降低 1 ℃ 需要多少热量，影响瞬态冷却速度。", "method":"DSC 差示扫描量热", "sample":"小块样品；记录样品批次和含水/表面状态", "output":"Cp(T)，J/(kg·K)", "model":"进入瞬态热传导方程"},
    "密度": {"symbol":"ρ", "why":"与 Cp、k 一起决定热响应，也是由 LFA 计算 k 时需要的基础量。", "method":"精密质量 + 几何体积；或适合水溶性晶体的密度方法", "sample":"规则样品；避免直接采用会溶解/腐蚀 KDP 的液体方法", "output":"ρ，kg/m³", "model":"进入瞬态热传导方程"},
    "弹性常数": {"symbol":"Cij(T)", "why":"KDP 是各向异性单晶。完整热应力模型最好使用刚度矩阵，而不是随便给一个 E 和 ν。", "method":"RUS 共振超声谱 / 超声反演", "sample":"定向、规则、尺寸精确的单晶样块", "output":"C11、C12、C13、C33、C44、C66 等", "model":"进入各向异性固体力学本构"},
    "弹性模量": {"symbol":"E[uvw]", "why":"同样的应变在不同方向会产生多大应力。", "method":"定向拉压/弯曲 + 应变；也可由完整 Cij 计算", "sample":"建议 [001]、[100]、[110]", "output":"E，GPa", "model":"早期简化模型或方向比较"},
    "泊松比": {"symbol":"ν", "why":"一个方向被拉长/压缩时，横向会收缩/膨胀多少。", "method":"应变片 / DIC；或由 Cij 换算", "sample":"必须同时写明载荷方向与横向测量方向", "output":"ν，无量纲", "model":"简化弹性模型"},
    "破坏强度": {"symbol":"σf", "why":"告诉你样品在实际缺陷和表面状态下大概多大应力会断。脆性材料必须做重复样。", "method":"三点弯曲优先作为起步；也可按目的做拉伸/压缩", "sample":"[001]、[100]、[110]；每方向多根重复", "output":"强度分布，MPa；建议后续做 Weibull 统计", "model":"与最大主拉应力等失效指标比较"},
    "断裂韧性": {"symbol":"KIC", "why":"如果晶体里已经有微裂纹/缺陷，它决定裂纹继续失稳扩展有多困难。", "method":"SENB 等断裂力学方法", "sample":"必须明确裂纹面和裂纹扩展方向，不能只写‘110样品’", "output":"KIC，MPa·m^0.5", "model":"裂纹失稳判据"},
}


def _why_page():
    st.markdown("### 为什么这些参数都要测？")
    st.markdown("你可以把大尺寸晶体冷却开裂理解成三步：**先产生温度差 → 再产生热应变/应力 → 最后判断会不会断。**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**第 1 步｜温度场**\n\n需要：密度 ρ、比热 Cp、热导率 k。\n\n回答：晶体内部哪里冷得快、哪里冷得慢？")
    with c2:
        st.info("**第 2 步｜应力场**\n\n需要：热膨胀 α、弹性常数 Cij（或简化 E、ν）。\n\n回答：温差会产生多大热应力？")
    with c3:
        st.info("**第 3 步｜是否开裂**\n\n需要：破坏强度 σf、断裂韧性 KIC。\n\n回答：这个应力是否已经危险？")
    st.markdown("#### 推荐测试顺序")
    st.markdown("**晶体定向 → 热膨胀 → 比热 → 热扩散/热导 → 弹性常数 → 三点弯曲强度 → 断裂韧性 → COMSOL 热—力耦合。**")
    soft_note("第一阶段不需要把所有参数一次测到完美。先建立可靠的 [001]/[100] 热物性与主要力学参数，就能启动第一版大尺寸冷却模型；后续再补完整 Cij、温度依赖和断裂统计。")


def _single_param():
    st.markdown("### 我想知道一个参数怎么测")
    name = st.selectbox("选择参数", list(PARAM_INFO), key="single_property")
    p = PARAM_INFO[name]
    st.markdown(f"## {name}  ·  {p['symbol']}")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**为什么测**")
        st.write(p["why"])
        st.markdown("**用什么设备/方法**")
        st.write(p["method"])
        st.markdown("**样品怎么准备**")
        st.write(p["sample"])
    with c2:
        st.markdown("**最后得到什么**")
        st.write(p["output"])
        st.markdown("**以后用到哪里**")
        st.write(p["model"])
        st.markdown("**实验记录必须带什么**")
        st.write("晶向/晶面、温度、样品批次、样品尺寸、测试方法、重复次数、不确定度/离散、原始数据文件编号。")


def _orientation():
    st.markdown("### 晶向、晶面、‘对角线切’先分清楚")
    st.warning("做物性测试前必须先定向。以后实验记录里不要只写‘200样品’或‘002样品’。")
    st.markdown(
        """
- **[uvw] 是晶向**：例如 `[100]`、`[001]`、`[110]`。
- **(hkl) 是晶面**：例如 `(200)`、`(002)`。
- `[200]` 与 `[100]` 是同一方向；`[002]` 与 `[001]` 是同一方向，通常归一化写 `[100]`、`[001]`。
- 如果说“样品表面是 (200)”，还要另外写清楚“热流/载荷沿哪个方向”。
- 在 `(001)` 基面内，从 `[100]` 与 `[010]` 两条边构成的几何对角方向是 `[110]`。
        """
    )
    st.markdown("#### 对当前课题的最简取样建议")
    st.dataframe(pd.DataFrame([
        ["热膨胀", "[001] + [100]", "先抓住 c 轴与基面内差异"],
        ["热扩散/热导", "热流沿 [001] + [100]", "用于温度场"],
        ["弹性/强度", "[001] + [100] + [110]", "增加面内对角方向比较"],
        ["断裂韧性", "写明裂纹面 + 扩展方向", "方向定义比单独一个 [110] 更重要"],
    ], columns=["项目", "第一阶段建议", "原因"]), width="stretch", hide_index=True)


def _plan():
    st.markdown("### 生成一份可拿去联系测试平台的计划")
    directions = st.multiselect("计划比较的方向", ["[001]", "[100]", "[110]"], default=["[001]", "[100]", "[110]"])
    tests = st.multiselect("需要测试的参数", list(PARAM_INFO), default=["热膨胀系数", "热扩散率", "比热", "密度", "弹性常数", "破坏强度", "断裂韧性"])
    temperature = st.text_input("测试温区", "室温 + 实际取晶/冷却涉及温区（最终按设备能力分段）")
    repeats = st.number_input("强度/断裂类每个方向计划重复样数", min_value=3, max_value=30, value=5)
    rows=[]
    for test in tests:
        p=PARAM_INFO[test]
        if test in ["比热","密度"]:
            rows.append([test,"总体/按样品状态",p["method"],"≥3或按仪器标准",temperature])
        else:
            for d in directions:
                rows.append([test,d,p["method"],repeats if test in ["破坏强度","断裂韧性"] else "≥2–3",temperature])
    df=pd.DataFrame(rows,columns=["项目","方向","方法/设备","重复建议","温区"])
    st.dataframe(df,width="stretch",hide_index=True,height=460)
    st.download_button("下载测试计划 CSV",df.to_csv(index=False).encode("utf-8-sig"),"KDP_物性测试计划.csv","text/csv")
    if st.button("保存测试计划到当前项目",type="primary"):
        add_item("experiment_plan","KDP物性测试计划",f"方向：{', '.join(directions)}；温区：{temperature}",{"rows":df.to_dict("records")},"物性参数与测试","待执行")
        st.success("已保存到当前研究项目。")


def _template():
    st.markdown("### 参数数据库模板")
    st.caption("以后无论是自己实测还是从文献摘录，都必须把方向、温度和来源一起保存。")
    df=pd.DataFrame([
        {"参数":"热膨胀系数","晶向/晶面":"[001]","温度(℃)":"","数值":"","单位":"1/K","方法":"TMA","样品批次":"","重复/不确定度":"","来源":"实测/文献","DOI/文件编号":"","备注":""},
        {"参数":"热导率","晶向/晶面":"热流沿[100]","温度(℃)":"","数值":"","单位":"W/(m·K)","方法":"LFA+ρ+Cp","样品批次":"","重复/不确定度":"","来源":"实测/文献","DOI/文件编号":"","备注":""},
        {"参数":"断裂韧性","晶向/晶面":"裂纹面+扩展方向","温度(℃)":"","数值":"","单位":"MPa·m^0.5","方法":"SENB","样品批次":"","重复/不确定度":"","来源":"实测/文献","DOI/文件编号":"","备注":""},
    ])
    edited=st.data_editor(df,num_rows="dynamic",width="stretch",hide_index=True)
    st.download_button("下载参数记录模板 CSV",edited.to_csv(index=False).encode("utf-8-sig"),"KDP_物性参数记录模板.csv","text/csv")
    st.warning("真实未公开实验值仍建议存入受保护的‘实验记录与数据积累’模块；这里主要负责测试规划和参数结构。")


def _testing_library_link():
    page = (st.session_state.get("_kdp_nav_pages") or {}).get("testing")
    if page is not None:
        st.info("如果你现在不是只想测热-力参数，而是想知道白纹、串丝、包裹体、位错、杂质和光学质量分别该用什么技术，请进入完整测试技术库。")
        st.page_link(page, label="进入：KDP测试技术与仪器库", icon=":material/manage_search:", width="stretch")


def material_properties_page():
    page_header(
        "KDP 物性参数：为什么测、在哪里测、怎么测",
        "不再先给一张参数大表。按‘开裂模型需要什么 → 单个参数怎么测 → 晶向怎么切 → 生成测试计划’一步一步看。",
        "KDP PROPERTY TESTING",
    )
    tabs=st.tabs(["先理解为什么测", "逐个参数学习", "晶向与切样", "生成测试计划", "参数记录模板"])
    with tabs[0]: _why_page()
    with tabs[1]: _single_param()
    with tabs[2]: _orientation()
    with tabs[3]: _plan()
    with tabs[4]: _template()
    st.divider()
    _testing_library_link()
