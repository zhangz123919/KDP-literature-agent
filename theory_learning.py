from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from theory_knowledge import CHAPTERS, GLOSSARY, LEARNING_PATH, QUIZ, REFERENCES
from ui import COLORS, page_header, section_title, soft_note


def _chapter_map():
    return {x["title"]: x for x in CHAPTERS}


def _render_path():
    st.markdown(
        """
<style>
.learn-path{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 20px}.learn-stage{background:#fff;border-top:3px solid #1359A6;border-bottom:1px solid #DCE5EC;padding:16px 15px;min-height:185px}.learn-stage-no{font-size:9px;letter-spacing:.14em;font-weight:900;color:#7A8D9C}.learn-stage-title{font-size:14px;font-weight:850;color:#173A55;margin:7px 0 6px}.learn-stage-goal{font-size:11px;line-height:1.65;color:#687C8D}.learn-stage-check{margin-top:11px;padding-top:9px;border-top:1px solid #E7EDF2;font-size:10px;line-height:1.55;color:#16877F;font-weight:650}
.concept-line{display:grid;grid-template-columns:repeat(7,1fr);border-top:1px solid #DCE5EC;border-bottom:1px solid #DCE5EC;background:#F8FAFB;margin:8px 0 18px}.concept-cell{padding:13px 10px;border-right:1px solid #E3E9EE;text-align:center}.concept-cell:last-child{border-right:none}.concept-k{font-size:9px;color:#8A99A6}.concept-v{font-size:11px;font-weight:800;color:#244A65;margin-top:4px}.learn-note{border-left:3px solid #0E9AA7;background:#F5FAFA;padding:12px 14px;font-size:11px;line-height:1.7;color:#47677A;margin:10px 0 16px}
@media(max-width:1150px){.learn-path{grid-template-columns:repeat(2,1fr)}.concept-line{grid-template-columns:repeat(2,1fr)}}
</style>
        """,
        unsafe_allow_html=True,
    )
    cards = []
    for idx, stage in enumerate(LEARNING_PATH, 1):
        cards.append(
            f'<div class="learn-stage"><div class="learn-stage-no">0{idx}</div>'
            f'<div class="learn-stage-title">{stage["stage"]}</div>'
            f'<div class="learn-stage-goal">{stage["goal"]}<br><br><b>章节：</b>{" / ".join(stage["chapters"])}</div>'
            f'<div class="learn-stage-check">学完能做到：{stage["checkpoint"]}</div></div>'
        )
    st.markdown('<div class="learn-path">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="concept-line">
  <div class="concept-cell"><div class="concept-k">工艺</div><div class="concept-v">温度 / 过饱和度 / 旋转</div></div>
  <div class="concept-cell"><div class="concept-k">尺度</div><div class="concept-v">小 → 中 → 大</div></div>
  <div class="concept-cell"><div class="concept-k">局部场</div><div class="concept-v">流场 / 传质 / 温度场</div></div>
  <div class="concept-cell"><div class="concept-k">界面</div><div class="concept-v">台阶 / 位错 / 成核</div></div>
  <div class="concept-cell"><div class="concept-k">缺陷</div><div class="concept-v">白纹 / 串丝 / 包裹体</div></div>
  <div class="concept-cell"><div class="concept-k">力学</div><div class="concept-v">热应变 / 应力集中</div></div>
  <div class="concept-cell"><div class="concept-k">结果</div><div class="concept-v">开裂 / 工艺优化</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_chapter(ch):
    st.markdown(f"### {ch['title']}")
    st.caption(ch["subtitle"])

    with st.container(border=True):
        st.markdown("**这一章先记住**")
        for item in ch["remember"]:
            st.markdown(f"- {item}")

    for sec in ch["sections"]:
        st.markdown(f"#### {sec['heading']}")
        st.markdown(sec["body"])

    if ch["equations"]:
        section_title("核心公式", "先理解每个符号对应的物理过程，再进入数值计算")
        for eq in ch["equations"]:
            with st.container(border=True):
                st.markdown(f"**{eq['name']}**")
                st.latex(eq["latex"])
                st.markdown(eq["explain"])
                st.caption("在当前课题中的用途：" + eq["use"])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### 容易犯的错误")
        for x in ch["pitfalls"]:
            st.markdown(f"- {x}")
    with c2:
        st.markdown("#### 与当前大尺寸KDP研究的连接")
        st.markdown(ch["research_link"])
        st.caption("关键词：" + " · ".join(ch["keywords"]))

    if ch["refs"]:
        with st.expander("本章核心原始文献", expanded=False):
            for rid in ch["refs"]:
                ref = REFERENCES.get(rid)
                if not ref:
                    continue
                st.markdown(f"**{ref['title']}**")
                st.caption(f"{ref['journal']}｜{ref['why']}")
                st.link_button("打开原始来源", ref["url"], key=f"ref_{ch['id']}_{rid}")


def _search_view(term: str):
    term = term.strip().lower()
    if not term:
        return []
    out = []
    for ch in CHAPTERS:
        blob = " ".join([
            ch["title"], ch["subtitle"], " ".join(ch["remember"]),
            " ".join(x["heading"] + " " + x["body"] for x in ch["sections"]),
            " ".join(ch["keywords"]),
        ]).lower()
        if term in blob:
            out.append(ch)
    return out


def _glossary():
    term = st.text_input("搜索术语", placeholder="例如：白纹、Re、(200)、断裂韧性、表面过饱和度")
    rows = GLOSSARY
    if term.strip():
        key = term.lower().strip()
        rows = [(a, b) for a, b in GLOSSARY if key in (a + " " + b).lower()]
    st.dataframe(pd.DataFrame(rows, columns=["术语", "初学者解释"]), width="stretch", hide_index=True, height=560)


def _quiz():
    st.markdown("这一组题不是考试，而是检查你是否已经把几个最容易混淆的概念分开。")
    answers = []
    for i, item in enumerate(QUIZ):
        ans = st.radio(
            f"{i+1}. {item['q']}",
            item["options"],
            key=f"kdp_quiz_{i}",
            index=None,
        )
        answers.append(ans)
    if st.button("检查答案", type="primary", key="kdp_quiz_check"):
        score = 0
        for i, (item, ans) in enumerate(zip(QUIZ, answers)):
            correct = item["options"][item["answer"]]
            if ans == correct:
                score += 1
                st.success(f"第 {i+1} 题正确：{item['explain']}")
            else:
                st.error(f"第 {i+1} 题需要再看：正确答案是“{correct}”。{item['explain']}")
        st.metric("本次自测", f"{score}/{len(QUIZ)}")


def theory_learning_page():
    page_header(
        "KDP理论基础学习",
        "面向零基础建立完整知识骨架：晶体学 → 水溶液生长 → 流场/传质 → 尺度效应 → 白纹/串丝/包裹体 → 热力学与开裂 → 物性测试 → 多尺度计算。",
        "KDP THEORY LEARNING",
    )

    st.markdown(
        '<div class="learn-note"><b>学习原则：</b>这里不按传统教材从抽象公式一路讲，而按你做大尺寸KDP实验真正会遇到的问题组织。每一章都回答“这是什么—为什么重要—怎么测/怎么算—和白纹、串丝、开裂有什么关系”。</div>',
        unsafe_allow_html=True,
    )

    mode = st.segmented_control(
        "学习模式",
        ["学习路线", "按章节学习", "术语词典", "基础自测"],
        default="学习路线",
        key="kdp_learning_mode",
    )

    if mode == "学习路线":
        _render_path()
        section_title("建议顺序", "先把语言和机制链建立起来，再进具体实验和模拟")
        for idx, stage in enumerate(LEARNING_PATH, 1):
            with st.expander(stage["stage"], expanded=idx == 1):
                st.markdown(stage["goal"])
                for x in stage["chapters"]:
                    st.markdown(f"- {x}")
                st.caption("检查点：" + stage["checkpoint"])
        soft_note("完成四个阶段后，你再去看大尺寸 KDP 生长论文，重点不再是记单个术语，而是能把‘工艺参数—局部场—界面—缺陷—应力—结果’连成一条机制链。")
        return

    if mode == "术语词典":
        _glossary()
        return

    if mode == "基础自测":
        _quiz()
        return

    search = st.text_input("在全部理论章节中检索", placeholder="例如：串丝 / 表面过饱和度 / [110] / LFA / COMSOL")
    cmap = _chapter_map()
    candidates = list(cmap)
    if search.strip():
        hits = _search_view(search)
        candidates = [x["title"] for x in hits]
        if not candidates:
            st.warning("没有找到直接匹配章节。可以换一个更基础的关键词，或到术语词典检索。")
            return

    chosen = st.selectbox("选择章节", candidates, key="kdp_theory_chapter")
    _render_chapter(cmap[chosen])
