
import streamlit as st
from engine import load_data, search_papers, topic_search, topic_stats, offline_summary
from diagnosis import VARIABLES, diagnose, experiment_matrix
from agent import api_status, run_agent
from reports import excel_bytes, docx_bytes
import plotly.express as px

st.set_page_config(page_title="KDP/DKDP科研智能体", page_icon="🔬", layout="wide")
st.markdown("""
<style>
html,body,[class*="css"]{font-family:"Microsoft YaHei","微软雅黑",Arial,sans-serif}
.block-container{padding-top:1rem;max-width:1580px}
[data-testid="stMetric"]{border:1px solid rgba(120,120,120,.18);border-radius:12px;padding:.8rem}
.chain{border-left:4px solid #4f46e5;padding:10px 14px;margin:8px 0}
</style>
""", unsafe_allow_html=True)

df = load_data()
if df.empty:
    st.error("缺少 data/KDP_全自动详细文献调研.xlsx")
    st.stop()

with st.sidebar:
    st.markdown("## 🔬 KDP/DKDP科研智能体")
    page = st.radio("模块",[
        "🏠 科研驾驶舱","📚 文献中心","🗺️ 知识图谱","🧭 专题调研",
        "⚖️ 多文献比较","🧪 开裂诊断","🧫 对照实验设计","🧮 理论计算助手",
        "🕳️ 研究空白","🤖 AI科研智能体","📝 报告中心","🩺 数据审计"
    ], label_visibility="collapsed")
    ok, model = api_status()
st.divider()

if ok:
    st.success(f"AI已连接：{model}")
else:
    st.warning("AI未连接：离线功能仍可用")

st.caption("S/A/B只是优先级，不会删除文献。")

def sources_block(src):
    if src:
        with st.expander("依据文献"):
            for x in src:
                st.write(f"[{x['编号']}] {x['题名']} ({x['年份']}) DOI: {x['DOI']}")

if page=="🏠 科研驾驶舱":
    st.title("🏠 科研驾驶舱")
    total=len(df); rel=(df["V5相关池"]=="KDP/DKDP相关池").sum()
    c=st.columns(5)
    c[0].metric("全库去重文献",f"{total:,}")
    c[1].metric("KDP/DKDP相关池",f"{rel:,}")
    c[2].metric("S核心",int((df["V5推荐等级"]=="S 核心 50").sum()))
    c[3].metric("A重点",int((df["V5推荐等级"]=="A 重点 150").sum()))
    c[4].metric("B扩展",int((df["V5推荐等级"]=="B 扩展 800").sum()))
    st.info("完整文献库始终保留；S/A/B只是阅读优先级。")
    st.markdown("""
<div class="chain"><b>① 缺陷/应力来源</b><br>点缺陷｜杂质｜包裹体｜位错｜快速生长｜籽晶｜加工｜固定约束</div>
<div class="chain"><b>② 局部机制</b><br>氢键/晶格畸变｜缺陷态｜生长界面｜热-力应力</div>
<div class="chain"><b>③ 宏观后果</b><br>吸收/散射｜裂纹萌生｜LIDT下降｜激光损伤</div>
<div class="chain"><b>④ 证据与控制</b><br>DFT/MD/FEA + Raman/FTIR/XRD/AFM/光热/LIDT + 单变量对照</div>
""", unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        s=topic_stats(df).sort_values("总文献")
        st.plotly_chart(px.bar(s,x="总文献",y="专题",orientation="h",title="专题证据规模"),use_container_width=True)
    with right:
        r=df[df["V5相关池"]=="KDP/DKDP相关池"]
        trend=r[r["年份"]>0].groupby("年份").size().reset_index(name="文献数")
        st.plotly_chart(px.line(trend,x="年份",y="文献数",markers=True,title="研究趋势"),use_container_width=True)
    st.subheader("S核心50")
    top=df[df["V5推荐等级"]=="S 核心 50"].sort_values("V5科研优先分",ascending=False)
    st.dataframe(top[["题名","年份","期刊","缺陷/应力来源","作用机制","宏观结果","_方法标签","V5科研优先分","DOI"]],use_container_width=True,hide_index=True,height=420)

elif page=="📚 文献中心":
    st.title("📚 文献中心")
    c1,c2,c3=st.columns(3)
    scope=c1.selectbox("范围",["全库","相关池","S+A"],index=1)
    limit=c2.selectbox("显示上限",[50,100,200,500,1000],index=2)
    tiers=c3.multiselect("等级",["S 核心 50","A 重点 150","B 扩展 800","C 扩展/背景","D 非核心/待核"])
    q=st.text_input("科研检索",placeholder="氢空位 额外吸收；包裹体 开裂；subsurface damage；DFT")
    work=df[df["V5推荐等级"].isin(tiers)] if tiers else df
    r=search_papers(work,q,limit,scope)
    cols=["题名","作者","年份","期刊","V5推荐等级","V5科研优先分","缺陷/应力来源","作用机制","宏观结果","_方法标签","被引次数","DOI"]
    st.success(f"当前显示 {len(r):,} 篇")
    st.dataframe(r[cols],use_container_width=True,hide_index=True,height=600)
    st.download_button("下载Excel",excel_bytes(r[cols],"文献检索"),"KDP_DKDP_文献检索.xlsx")

elif page=="🗺️ 知识图谱":
    st.title("🗺️ 知识图谱与分类")
    scope=st.radio("范围",["相关池","S+A","全库"],horizontal=True)
    w=df if scope=="全库" else df[df["V5相关池"]=="KDP/DKDP相关池"] if scope=="相关池" else df[df["V5推荐等级"].isin(["S 核心 50","A 重点 150"])]
    chain=w.groupby(["缺陷/应力来源","作用机制","宏观结果"]).size().reset_index(name="文献数")
    st.plotly_chart(px.sunburst(chain,path=["缺陷/应力来源","作用机制","宏观结果"],values="文献数"),use_container_width=True)
    raw=w["详细二级分类"].replace("","未命中").value_counts().head(40).rename_axis("原始详细分类").reset_index(name="文献数")
    st.dataframe(raw,use_container_width=True,hide_index=True)

elif page=="🧭 专题调研":
    st.title("🧭 专题自动调研")
    from engine import TOPICS
    topic=st.selectbox("专题",list(TOPICS))
    n=st.slider("代表文献数",8,40,20)
    papers=topic_search(df,topic,n,"相关池")
    st.dataframe(papers[["题名","年份","期刊","V5推荐等级","_方法标签","DOI"]],use_container_width=True,hide_index=True)
    st.markdown(offline_summary(papers,topic))
    if st.button("AI生成完整专题调研",type="primary"):
        ok,_=api_status()
        if not ok: st.warning("未配置DeepSeek API Key。")
        else:
            a,s=run_agent(f"围绕“{topic}”生成系统专题调研。",papers,"专题调研")
            st.markdown(a); sources_block(s)
            st.download_button("下载Word",docx_bytes(topic+"专题调研",a,s),topic+"_专题调研.docx")

elif page=="⚖️ 多文献比较":
    st.title("⚖️ 多文献比较")
    q=st.text_input("检索候选论文")
    cand=search_papers(df,q,60,"相关池") if q else search_papers(df,"",60,"S+A")
    mp={f"{r['题名']}｜{r['年份']}":i for i,r in cand.iterrows()}
    sel=st.multiselect("选择2–6篇",list(mp),max_selections=6)
    if len(sel)>=2:
        chosen=df.loc[[mp[x] for x in sel]]
        st.dataframe(chosen[["题名","年份","详细二级分类","_方法标签","自动研究问题","自动主要结论","DOI"]],use_container_width=True,hide_index=True)
        if st.button("AI深度比较",type="primary"):
            ok,_=api_status()
            if not ok: st.warning("未配置DeepSeek。")
            else:
                a,s=run_agent("比较这些论文的研究对象、方法、结论、差异和借鉴价值。",chosen,"多文献比较")
                st.markdown(a); sources_block(s)
    else:
        st.info("至少选择2篇论文。")

elif page=="🧪 开裂诊断":
    st.title("🧪 开裂与缺陷诊断")
    phenomenon=st.text_area("本次开裂/缺陷现象",height=110)
    opts=["未知","明显异常","偏高/偏快/强约束","可疑","一般/不确定","较好/稳定","偏低/偏慢/低约束"]
    states={}; cols=st.columns(2)
    for i,v in enumerate(VARIABLES): states[v]=cols[i%2].selectbox(v,opts,key=v)
    if st.button("执行根因诊断",type="primary"):
        r=diagnose(states)
        st.dataframe(r,use_container_width=True,hide_index=True,height=500)
        ev=search_papers(df,phenomenon+" crack thermal stress inclusion dislocation supersaturation",15,"相关池")
        st.subheader("关联文献证据")
        st.dataframe(ev[["题名","年份","V5推荐等级","详细二级分类","_方法标签","DOI"]],use_container_width=True,hide_index=True)
        ok,_=api_status()
        if ok:
            extra="\n".join(f"{x['变量']}={x['当前状态']}，风险={x['风险']}" for _,x in r.iterrows())
            a,s=run_agent(phenomenon or "诊断KDP/DKDP开裂原因",ev,"实验诊断",extra)
            st.markdown(a); sources_block(s)

elif page=="🧫 对照实验设计":
    st.title("🧫 对照实验设计")
    selected=st.multiselect("变量",list(VARIABLES),default=["降温速率","籽晶固定方式","过饱和度"])
    baseline=st.text_area("当前标准流程/基线")
    if selected:
        m=experiment_matrix(selected,baseline)
        st.dataframe(m,use_container_width=True,hide_index=True)
        st.download_button("下载实验矩阵Excel",excel_bytes(m,"对照实验"),"KDP_DKDP_对照实验设计.xlsx")

elif page=="🧮 理论计算助手":
    st.title("🧮 理论计算助手")
    c1,c2=st.columns(2)
    method=c1.selectbox("计算类型",["DFT/第一性原理","分子动力学 MD","有限元 FEA"])
    target=c1.selectbox("对象",["氢空位","钾空位","氧/磷酸根缺陷","杂质/掺杂","缺陷复合体","包裹体附近应力","加工亚表面损伤","裂纹萌生","热应力场","籽晶/固定约束","DKDP同位素效应"])
    software=c2.multiselect("软件",["Materials Studio","Quantum ESPRESSO","VASP","Gaussian","LAMMPS","COMSOL","ANSYS","Python"])
    goal=c2.text_area("研究目标")
    ev=search_papers(df,f"{method} {target} {goal}",18,"相关池")
    st.dataframe(ev[["题名","年份","V5推荐等级","_方法标签","DOI"]],use_container_width=True,hide_index=True)
    skeleton={
        "DFT/第一性原理":"结构验证 → 超胞/k点/截断能收敛 → 缺陷/电荷态 → 优化 → 形成能 → TDOS/PDOS/电荷密度 → 光学性质 → 实验验证",
        "分子动力学 MD":"势函数验证 → 完整晶体基准 → 缺陷/热/加工工况 → 位错/裂纹演化 → 原子应力/能量 → 实验比较",
        "有限元 FEA":"各向异性参数 → 温度/浓度/夹持边界 → 网格收敛 → 主应力/应变能 → 危险区 → 裂纹位置验证",
    }
    st.info(skeleton[method])
    if st.button("AI生成完整计算方案",type="primary"):
        ok,_=api_status()
        if not ok: st.warning("未配置DeepSeek。")
        else:
            a,s=run_agent(f"{method}; {target}; 软件={software}; 目标={goal}",ev,"理论方案")
            st.markdown(a); sources_block(s)

elif page=="🕳️ 研究空白":
    st.title("🕳️ 研究空白")
    from engine import TOPICS
    s=topic_stats(df)
    st.dataframe(s,use_container_width=True,hide_index=True)
    st.plotly_chart(px.scatter(s,x="总文献",y="近5年",size="S/A",color="DFT",hover_name="专题"),use_container_width=True)
    topic=st.selectbox("深入分析",list(TOPICS))
    ev=topic_search(df,topic,25,"相关池")
    if st.button("AI识别可验证空白",type="primary"):
        ok,_=api_status()
        if not ok: st.warning("未配置DeepSeek。")
        else:
            a,sr=run_agent(f"围绕{topic}识别3–6个可验证研究空白，每个给出验证方案。",ev,"研究空白")
            st.markdown(a); sources_block(sr)

elif page=="🤖 AI科研智能体":
    st.title("🤖 AI科研智能体")
    task=st.selectbox("任务",["自动判断","文献问答","多文献比较","专题调研","研究空白","实验诊断","理论方案","报告生成"])
    q=st.text_area("科研问题",height=130)
    scope=st.selectbox("证据范围",["相关池","S+A","全库"])
    n=st.slider("证据文献数",6,20,12)
    if st.button("执行科研任务",type="primary"):
        if not q.strip(): st.warning("请输入问题。")
        else:
            ev=search_papers(df,q,n,scope)
            st.dataframe(ev[["题名","年份","V5推荐等级","详细二级分类","_方法标签","DOI"]],use_container_width=True,hide_index=True)
            ok,_=api_status()
            if not ok:
                st.warning("未配置DeepSeek，先显示离线证据概览。")
                st.markdown(offline_summary(ev,q))
            else:
                a,s=run_agent(q,ev,task)
                st.markdown(a); sources_block(s)
                st.download_button("下载回答Word",docx_bytes("科研智能体回答",a,s),"科研智能体回答.docx")

elif page=="📝 报告中心":
    st.title("📝 报告中心")
    from engine import TOPICS
    kind=st.selectbox("类型",["组会专题汇报","专题文献调研","开题方向论证","理论计算方案总结","开裂诊断报告"])
    topic=st.selectbox("主题",list(TOPICS))
    extra=st.text_area("额外要求")
    ev=topic_search(df,topic,20,"相关池")
    if st.button("生成报告",type="primary"):
        ok,_=api_status()
        if not ok:
            st.markdown(offline_summary(ev,topic))
        else:
            a,s=run_agent(f"生成{kind}，主题={topic}。要求：{extra}",ev,"报告生成")
            st.markdown(a); sources_block(s)
            st.download_button("下载Word",docx_bytes(topic+"-"+kind,a,s),topic+"_"+kind+".docx")

elif page=="🩺 数据审计":
    st.title("🩺 数据审计")
    c=st.columns(4)
    c[0].metric("当前加载总记录",f"{len(df):,}")
    c[1].metric("相关池",f"{(df['V5相关池']=='KDP/DKDP相关池').sum():,}")
    c[2].metric("无摘要",int((df["摘要"].str.strip()=="").sum()))
    c[3].metric("无DOI",int((df["DOI"].str.strip()=="").sum()))
    st.dataframe(df["V5推荐等级"].value_counts().rename_axis("等级").reset_index(name="文献数"),use_container_width=True,hide_index=True)
    st.markdown("""
- `当前加载总记录`：优先读取 Excel 的 `全部详细分类` / `全部去重`，代表完整去重库。
- `相关池`：只是标签，不删除其他记录。
- `S核心50 / A重点150 / B扩展800`：只是阅读优先级。
- 剩余相关文献仍在 `C 扩展/背景` 中，可继续检索。
""")
