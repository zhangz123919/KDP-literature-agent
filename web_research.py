
from __future__ import annotations

import html
import re
from typing import Dict, List, Tuple

import requests
import streamlit as st


CROSSREF_URL = "https://api.crossref.org/works"


QUERY_HINTS = {
    "氢空位": "KDP potassium dihydrogen phosphate hydrogen vacancy proton vacancy optical absorption defect electronic structure",
    "质子空位": "KDP potassium dihydrogen phosphate proton vacancy hydrogen vacancy defect",
    "开裂": "KDP DKDP crystal cracking fracture thermal stress residual stress defect",
    "裂纹": "KDP DKDP crystal crack fracture thermal stress defect",
    "包裹体": "KDP DKDP crystal inclusion solution inclusion scattering center defect",
    "位错": "KDP DKDP crystal dislocation lattice strain defect",
    "过饱和度": "KDP DKDP crystal supersaturation rapid growth growth defect inclusion",
    "快速生长": "KDP DKDP crystal rapid growth supersaturation growth defect",
    "籽晶": "KDP DKDP seed crystal orientation fixation stress crack growth",
    "固定方式": "KDP DKDP seed fixation mounting constraint stress cracking",
    "亚表面损伤": "KDP crystal subsurface damage polishing grinding machining laser damage",
    "激光损伤": "KDP DKDP crystal laser damage LIDT defect absorption",
    "损伤阈值": "KDP DKDP laser induced damage threshold LIDT defect",
    "弱吸收": "KDP DKDP weak absorption photothermal localized absorption defect",
    "第一性原理": "KDP DKDP first principles DFT defect electronic structure",
    "DFT": "KDP DKDP density functional theory DFT defect electronic structure",
    "杂质": "KDP DKDP impurity doping defect optical absorption growth",
    "掺杂": "KDP DKDP doping impurity defect optical properties",
    "DKDP": "DKDP deuterated potassium dihydrogen phosphate crystal defect growth laser damage",
    "KDP": "KDP potassium dihydrogen phosphate crystal defect growth laser damage",
    "Materials Studio": "KDP crystal Materials Studio defect modeling first principles",
    "Quantum ESPRESSO": "KDP crystal Quantum ESPRESSO DFT defect calculation",
    "VASP": "KDP crystal VASP DFT defect calculation",
}


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _year_from_crossref(item: dict):
    for key in ("published-print", "published-online", "published", "issued", "created"):
        block = item.get(key) or {}
        parts = block.get("date-parts")
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except Exception:
                pass
    return ""


def _normalize_title(title: str) -> str:
    title = re.sub(r"\W+", "", str(title or "").lower())
    return title[:200]


def build_search_query(question: str) -> str:
    q = str(question or "").strip()
    hints = []

    for trigger, expansion in QUERY_HINTS.items():
        if trigger.lower() in q.lower():
            hints.append(expansion)

    # 保留用户问题中的英文词，中文问题则由上面的科研词典转成更适合学术检索的英文查询。
    english_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{1,}", q)
    if english_tokens:
        hints.append(" ".join(english_tokens[:20]))

    if not hints:
        hints.append("KDP DKDP crystal " + q)

    merged = " ".join(dict.fromkeys(" ".join(hints).split()))
    return merged[:700]


def search_crossref(question: str, max_results: int = 8) -> List[Dict]:
    query = build_search_query(question)

    headers = {
        "User-Agent": "KDP-DKDP-Research-Agent/1.0 (scholarly metadata search)"
    }

    params = {
        "query.bibliographic": query,
        "rows": max_results,
        "select": "DOI,title,author,published,published-print,published-online,issued,created,container-title,URL,abstract,type",
    }

    # Crossref 支持无需 Key 的公开 REST API；超时或服务异常时直接降级，不影响本地知识库问答。
    response = requests.get(
        CROSSREF_URL,
        params=params,
        headers=headers,
        timeout=12,
    )
    response.raise_for_status()

    items = response.json().get("message", {}).get("items", [])
    results = []

    for item in items:
        titles = item.get("title") or []
        title = _strip_tags(titles[0] if titles else "")
        if not title:
            continue

        container = item.get("container-title") or []
        journal = _strip_tags(container[0] if container else "")
        doi = str(item.get("DOI") or "").strip()
        url = str(item.get("URL") or "").strip()
        abstract = _strip_tags(item.get("abstract") or "")

        authors = []
        for a in (item.get("author") or [])[:6]:
            name = " ".join(
                x for x in [str(a.get("given") or "").strip(), str(a.get("family") or "").strip()]
                if x
            )
            if name:
                authors.append(name)

        results.append({
            "source_type": "学术元数据",
            "title": title,
            "year": _year_from_crossref(item),
            "journal": journal,
            "authors": "; ".join(authors),
            "doi": doi,
            "url": url,
            "snippet": abstract[:1800] if abstract else (
                "Crossref检索到该论文的书目信息；当前未返回摘要。"
                "这条记录可用于发现和定位论文，但不能单独作为具体机理或数值的直接证据。"
            ),
            "has_abstract": bool(abstract),
        })

    return results


def search_openalex_optional(question: str, max_results: int = 6) -> List[Dict]:
    """
    如果以后用户在 Streamlit Secrets 中加入 OPENALEX_API_KEY，
    会自动增加 OpenAlex 学术检索；没加 Key 时完全忽略，不影响网站。
    """
    api_key = _secret("OPENALEX_API_KEY")
    if not api_key:
        return []

    query = build_search_query(question)

    params = {
        "search": query,
        "per_page": max_results,
        "api_key": api_key,
        "select": "id,doi,title,publication_year,authorships,primary_location,abstract_inverted_index,cited_by_count",
    }

    response = requests.get(
        "https://api.openalex.org/works",
        params=params,
        timeout=12,
    )
    response.raise_for_status()

    results = []

    for item in response.json().get("results", []):
        title = _strip_tags(item.get("title") or "")
        if not title:
            continue

        abstract_index = item.get("abstract_inverted_index") or {}
        abstract = ""

        if abstract_index:
            positions = []
            for word, idxs in abstract_index.items():
                for idx in idxs:
                    positions.append((idx, word))
            positions.sort(key=lambda x: x[0])
            abstract = " ".join(word for _, word in positions)

        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        journal = str(source.get("display_name") or "")

        authors = []
        for authorship in (item.get("authorships") or [])[:6]:
            author = authorship.get("author") or {}
            name = str(author.get("display_name") or "").strip()
            if name:
                authors.append(name)

        doi = str(item.get("doi") or "").replace("https://doi.org/", "")
        url = str(item.get("id") or "")

        results.append({
            "source_type": "学术检索",
            "title": title,
            "year": item.get("publication_year") or "",
            "journal": journal,
            "authors": "; ".join(authors),
            "doi": doi,
            "url": url,
            "snippet": abstract[:1800] if abstract else "OpenAlex返回书目信息，当前没有可用摘要。",
            "has_abstract": bool(abstract),
        })

    return results


def search_general_web(question: str, max_results: int = 6) -> List[Dict]:
    """
    无需额外 API Key 的通用网页检索。
    如果搜索服务临时不可用，会自动降级，不阻塞科研智能体。
    """
    from ddgs import DDGS

    query = build_search_query(question)

    ddgs = DDGS(timeout=8)

    raw = ddgs.text(
        query,
        region="wt-wt",
        safesearch="moderate",
        max_results=max_results,
        backend="auto",
    )

    results = []

    for item in raw or []:
        title = _strip_tags(item.get("title") or "")
        url = str(item.get("href") or item.get("url") or "").strip()
        body = _strip_tags(item.get("body") or "")

        if not title or not url:
            continue

        results.append({
            "source_type": "网页资料",
            "title": title,
            "year": "",
            "journal": "",
            "authors": "",
            "doi": "",
            "url": url,
            "snippet": body[:1600],
            "has_abstract": False,
        })

    return results


def _deduplicate(results: List[Dict]) -> List[Dict]:
    seen_doi = set()
    seen_title = set()
    seen_url = set()
    output = []

    for item in results:
        doi = str(item.get("doi") or "").lower().strip()
        title_key = _normalize_title(item.get("title") or "")
        url = str(item.get("url") or "").lower().strip()

        duplicate = False

        if doi and doi in seen_doi:
            duplicate = True
        elif title_key and title_key in seen_title:
            duplicate = True
        elif url and url in seen_url:
            duplicate = True

        if duplicate:
            continue

        if doi:
            seen_doi.add(doi)
        if title_key:
            seen_title.add(title_key)
        if url:
            seen_url.add(url)

        output.append(item)

    return output


def research_web(question: str) -> Tuple[str, List[Dict], Dict]:
    """
    默认自动补充最新资料。
    返回：
      context: 给 DeepSeek 的检索上下文
      sources: 用于最终展示链接
      status: 各检索渠道状态
    """
    sources = []
    status = {
        "crossref": "未运行",
        "openalex": "未运行",
        "web": "未运行",
    }

    try:
        cr = search_crossref(question, max_results=8)
        sources.extend(cr)
        status["crossref"] = f"成功 {len(cr)}"
    except Exception as exc:
        status["crossref"] = f"失败 {type(exc).__name__}"

    try:
        oa = search_openalex_optional(question, max_results=6)
        sources.extend(oa)
        status["openalex"] = f"成功 {len(oa)}" if oa else "未配置/无结果"
    except Exception as exc:
        status["openalex"] = f"失败 {type(exc).__name__}"

    try:
        web = search_general_web(question, max_results=6)
        sources.extend(web)
        status["web"] = f"成功 {len(web)}"
    except Exception as exc:
        status["web"] = f"失败 {type(exc).__name__}"

    sources = _deduplicate(sources)[:16]

    blocks = []

    for i, item in enumerate(sources, 1):
        item["编号"] = f"W{i}"

        blocks.append(
            f"[W{i}]\n"
            f"来源类型：{item.get('source_type','')}\n"
            f"题名/页面：{item.get('title','')}\n"
            f"年份：{item.get('year','')}\n"
            f"期刊/来源：{item.get('journal','')}\n"
            f"DOI：{item.get('doi','')}\n"
            f"URL：{item.get('url','')}\n"
            f"摘要/搜索摘要：{item.get('snippet','')}"
        )

    context = "\n\n".join(blocks)

    return context, sources, status


def source_links_markdown(sources: List[Dict]) -> str:
    if not sources:
        return ""

    lines = [
        "",
        "---",
        "### 补充来源",
    ]

    for item in sources:
        no = item.get("编号", "W?")
        title = str(item.get("title") or "来源").replace("[", "\\[").replace("]", "\\]")
        url = str(item.get("url") or "").strip()
        doi = str(item.get("doi") or "").strip()
        source_type = item.get("source_type", "")

        extra = []
        if item.get("year"):
            extra.append(str(item["year"]))
        if item.get("journal"):
            extra.append(str(item["journal"]))
        if doi:
            extra.append(f"DOI: {doi}")

        suffix = f"（{'；'.join(extra)}）" if extra else ""

        if url:
            lines.append(f"- **[{no}]** [{title}]({url}) — {source_type}{suffix}")
        else:
            lines.append(f"- **[{no}]** {title} — {source_type}{suffix}")

    return "\n".join(lines)
