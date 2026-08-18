from __future__ import annotations

import pandas as pd
import streamlit as st

from theory_knowledge import CHAPTERS, GLOSSARY, LEARNING_PATH, QUIZ, REFERENCES
from ui import page_header, section_title, soft_note


def _chapter_map():
    return {x["title"]: x for x in CHAPTERS}


def _jump_to(title: str):
    st.session_state["theory_selected_chapter"] = title
    st.session_state["theory_view"] = "章节学习"


def _start_here():
    st.markdown("### 零基础先从这里开始")
    st.markdown(
        "你不需要一次学完所有固体物理。对现在的大尺寸 KDP 课题，先把下面这条链真正弄懂：**晶体是什么 → 怎么从水溶液长出来 → 为什么尺寸变大会改变局部环境 → 缺陷怎么形成 → 为什么会产生热应力和开裂。**"
    )
    st.markdown("#### 四个学习阶段")
    for i, stage in enumerate(LEARNING_PATH,1):
        with st.expander(f"第 {i} 阶段｜{stage['stage']}", expanded=i==1):
            st.write(stage["goal"])
            st.markdown("**要学的章节**")
            for x in stage["chapters"]:
                st.markdown(f"- {x}")
            st.caption("学完检查："+stage["checkpoint"])
    first=LEARNING_PATH[0]["chapters"][0]
    if st.button("从第 1 章开始学",type="primary",key="start_theory_first"):
        _jump_to(first)
        st.rerun()
    soft_note("建议学习方式：每次只学一章。学完后用本页的‘基础自测’检查概念，再去看对应文献或做实验。")


def _render_chapter(ch):
    st.markdown(f"## {ch['title']}")
    st.caption(ch["subtitle"])
    with st.container(border=True):
        st.markdown("**这一章学完，你至少要记住：**")
        for item in ch["remember"]:
            st.markdown(f"- {item}")

    for idx, sec in enumerate(ch["sections"],1):
        st.markdown(f"### {idx}. {sec['heading']}")
        st.markdown(sec["body"])

    if ch["equations"]:
        section_title("公式怎么理解", "先知道公式在描述什么，再记符号")
        for eq in ch["equations"]:
            with st.expander(eq["name"], expanded=True):
                st.latex(eq["latex"])
                st.markdown(eq["explain"])
                st.info("**在你的 KDP 研究里用来做什么：** " + eq["use"])

    c1,c2=st.columns(2,gap="large")
    with c1:
        st.markdown("### 最容易搞错的地方")
        for x in ch["pitfalls"]: st.markdown(f"- {x}")
    with c2:
        st.markdown("### 和现在课题怎么连接")
        st.markdown(ch["research_link"])
        st.caption("关键词："+" · ".join(ch["keywords"]))

    if ch["refs"]:
        with st.expander("本章核心原始文献（需要时再打开）",expanded=False):
            for rid in ch["refs"]:
                ref=REFERENCES.get(rid)
                if ref:
                    st.markdown(f"**{ref['title']}**")
                    st.caption(f"{ref['journal']}｜{ref['why']}")
                    st.link_button("打开原始来源",ref["url"],key=f"theory_ref_{ch['id']}_{rid}")


def _chapter_directory():
    st.markdown("### 课程目录")
    st.caption("点击‘学习这一章’才会进入正文，不再让你面对一个不知道怎么选的长下拉框。")
    cmap=_chapter_map()
    titles=list(cmap)
    for i in range(0,len(titles),3):
        cols=st.columns(3,gap="medium")
        for col,title in zip(cols,titles[i:i+3]):
            ch=cmap[title]
            with col:
                with st.container(border=True):
                    st.caption(f"第 {titles.index(title)+1:02d} 章")
                    st.markdown(f"**{title}**")
                    st.write(ch["subtitle"])
                    if st.button("学习这一章",key=f"learn_{ch['id']}",use_container_width=True):
                        _jump_to(title)
                        st.rerun()


def _chapter_learning():
    cmap=_chapter_map()
    selected=st.session_state.get("theory_selected_chapter",list(cmap)[0])
    titles=list(cmap)
    if selected not in cmap: selected=titles[0]
    idx=titles.index(selected)
    cprev,cmid,cnext=st.columns([1,3,1])
    with cprev:
        if idx>0 and st.button("← 上一章",use_container_width=True):
            st.session_state["theory_selected_chapter"]=titles[idx-1]; st.rerun()
    with cmid:
        selected=st.selectbox("当前章节",titles,index=idx,key="theory_chapter_select")
        st.session_state["theory_selected_chapter"]=selected
    with cnext:
        if idx<len(titles)-1 and st.button("下一章 →",use_container_width=True):
            st.session_state["theory_selected_chapter"]=titles[idx+1]; st.rerun()
    _render_chapter(cmap[selected])


def _glossary():
    st.markdown("### 术语词典")
    term=st.text_input("输入你不懂的词",placeholder="例如：白纹、串丝、[110]、(200)、Re、LFA、断裂韧性")
    rows=GLOSSARY
    if term.strip():
        key=term.lower().strip(); rows=[(a,b) for a,b in GLOSSARY if key in (a+" "+b).lower()]
    if rows:
        for a,b in rows[:80]:
            with st.expander(a,expanded=False): st.write(b)
    else:
        st.warning("没有找到直接匹配。可以换一个更基础的关键词。")


def _quiz():
    st.markdown("### 基础自测")
    st.caption("不是考试，只检查最容易混淆的概念。")
    answers=[]
    for i,item in enumerate(QUIZ):
        answers.append(st.radio(f"{i+1}. {item['q']}",item["options"],index=None,key=f"kdp_q_{i}"))
    if st.button("检查答案",type="primary"):
        score=0
        for i,(item,ans) in enumerate(zip(QUIZ,answers)):
            correct=item["options"][item["answer"]]
            if ans==correct:
                score+=1; st.success(f"第 {i+1} 题正确。{item['explain']}")
            else:
                st.error(f"第 {i+1} 题：正确答案是“{correct}”。{item['explain']}")
        st.metric("本次得分",f"{score}/{len(QUIZ)}")


def theory_learning_page():
    page_header(
        "KDP 理论基础学习｜从零开始",
        "把你真正会遇到的晶体学、水溶液生长、过饱和度、流场传质、白纹、串丝、热应力、物性测试和多尺度计算按学习顺序讲清楚。",
        "KDP FUNDAMENTALS",
    )
    if "theory_view" not in st.session_state: st.session_state["theory_view"]="从零开始"
    choices=["从零开始","课程目录","章节学习","术语词典","基础自测"]
    current=st.session_state.get("theory_view","从零开始")
    if current not in choices: current="从零开始"
    view=st.radio("学习方式",choices,index=choices.index(current),horizontal=True,key="theory_view_radio")
    st.session_state["theory_view"]=view
    st.divider()
    if view=="从零开始": _start_here()
    elif view=="课程目录": _chapter_directory()
    elif view=="章节学习": _chapter_learning()
    elif view=="术语词典": _glossary()
    else: _quiz()
