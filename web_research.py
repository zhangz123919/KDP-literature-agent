
from __future__ import annotations

import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

import requests
import streamlit as st


CROSSREF_URL = "https://api.crossref.org/works"

QUERY_HINTS = {
    "氢空位": "KDP potassium dihydrogen phosphate hydrogen vacancy proton vacancy optical absorption defect electronic structure",
    "质子空位": "KDP potassium dihydrogen phosphate proton vacancy hydrogen vacancy defect",
    "开裂": "KDP potassium dihydrogen phosphate cooling crack fracture thermal stress temperature gradient residual stress",
    "裂纹": "KDP potassium dihydrogen phosphate crack fracture thermal stress temperature gradient",
    "降温": "KDP potassium dihydrogen phosphate cooling thermal stress temperature gradient crack fracture",
    "热应力": "KDP potassium dihydrogen phosphate thermal stress thermal expansion crack fracture",
    "包裹体": "KDP DKDP crystal inclusion solution inclusion scattering center defect crack",
    "位错": "KDP DKDP crystal dislocation lattice strain crack defect",
    "过饱和度": "KDP DKDP crystal supersaturation rapid growth growth defect inclusion",
    "快速生长": "KDP DKDP crystal rapid growth supersaturation growth defect",
    "籽晶": "KDP seed crystal temperature nonuniformity orientation fixation stress crack growth",
    "固定方式": "KDP seed fixation mounting constraint thermal stress cracking",
    "亚表面损伤": "KDP crystal subsurface damage polishing grinding machining laser damage",
    "激光损伤": "KDP DKDP crystal laser damage LIDT defect absorption",
    "损伤阈值": "KDP DKDP laser induced damage threshold LIDT defect",
    "弱吸收": "KDP DKDP weak absorption photothermal localized absorption defect",
    "第一性原理": "KDP DKDP first principles DFT defect electronic structure",
    "DFT": "KDP DKDP density functional theory DFT defect electronic structure",
    "杂质": "KDP DKDP impurity doping defect optical absorption growth",
    "掺杂": "KDP DKDP doping impurity defect optical properties",
    "Materials Studio": "KDP crystal Materials Studio defect modeling first principles",
    "Quantum ESPRESSO": "KDP crystal Quantum ESPRESSO DFT defect calculation",
    "VASP": "KDP crystal VASP DFT defect calculation",
}


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _strip(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _year(item: dict):
    for key in ("published-print", "published-online", "published", "issued", "created"):
        block = item.get(key) or {}
        parts = block.get("date-parts")
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except Exception:
                pass
    return ""


def _title_key(title: str) -> str:
    return re.sub(r"\W+", "", str(title or "").lower())[:220]


def _compact_title(title: str, limit: int = 220) -> str:
    """
    防止搜索引擎把整页正文误塞进 title。
    """
    title = _strip(title)
    if len(title) <= limit:
        return title

    # 优先在常见分隔符处截断
    head = re.split(r"(?:\s+[|–—]\s+|\s+Abstract[:：]\s+|\s+Authors?[:：]\s+)", title, maxsplit=1)[0]
    head = head.strip()

    if 20 <= len(head) <= limit:
        return head

    return title[:limit].rstrip(" ,;:-—–") + "…"


MATERIAL_ANCHORS = [
    r"\bKDP\b",
    r"\bDKDP\b",
    r"\bKH2PO4\b",
    r"\bKD2PO4\b",
    r"potassium\s+dihydrogen\s+phosphate",
    r"potassium\s+dideuterium\s+phosphate",
    r"deuterated\s+potassium\s+dihydrogen\s+phosphate",
]


def _has_material_anchor(text: str) -> bool:
    text = _strip(text)
    return any(re.search(p, text, flags=re.I) for p in MATERIAL_ANCHORS)


def _topic_terms(question: str) -> List[str]:
    """
    从本次问题里提取少量主题词，用于外部结果二次排序。
    """
    terms = []
    q = str(question or "")
    for trigger, expansion in QUERY_HINTS.items():
        if trigger.lower() in q.lower():
            for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", expansion.lower()):
                if w not in {
                    "kdp", "dkdp", "crystal", "potassium", "dihydrogen",
                    "phosphate", "defect", "growth"
                }:
                    terms.append(w)
    return list(dict.fromkeys(terms))[:18]


def _quality_score(item: Dict, question: str) -> float:
    text = " ".join([
        str(item.get("title") or ""),
        str(item.get("journal") or ""),
        str(item.get("snippet") or ""),
    ]).lower()

    score = 0.0

    # KDP/DKDP材料锚点是硬要求，同时也作为最主要的加分项。
    if _has_material_anchor(text):
        score += 10.0

    title = str(item.get("title") or "")
    if _has_material_anchor(title):
        score += 4.0

    source_type = str(item.get("source_type") or "")
    if source_type in {"学术元数据", "学术检索"}:
        score += 2.0

    if item.get("has_abstract"):
        score += 2.0

    if item.get("doi"):
        score += 1.0

    topic_hits = 0
    for term in _topic_terms(question):
        if term.lower() in text:
            topic_hits += 1
    score += min(topic_hits, 6) * 0.7

    # 搜索引擎把正文当标题时通常异常冗长，强烈降权。
    if len(title) > 300:
        score -= 8.0

    return score


def _filter_and_rank(items: List[Dict], question: str, limit: int = 8) -> List[Dict]:
    """
    外部检索质量闸门：
    1. 必须明确涉及KDP/DKDP/KH2PO4/KD2PO4；
    2. 拒绝“标题被整页正文污染”的结果；
    3. 学术来源、摘要、DOI和主题命中优先；
    4. 最终只保留少量高相关来源。
    """
    clean = []

    for raw in items:
        item = dict(raw)

        original_title = _strip(item.get("title") or "")
        snippet = _strip(item.get("snippet") or "")

        combined = " ".join([
            original_title,
            str(item.get("journal") or ""),
            snippet,
        ])

        if not _has_material_anchor(combined):
            continue

        # 极长网页标题通常是搜索引擎把正文/目录一起抓进来了。
        if item.get("source_type") == "网页资料" and len(original_title) > 420:
            continue

        item["title"] = _compact_title(original_title, 220)
        item["snippet"] = snippet[:650]
        item["_score"] = _quality_score(item, question)
        clean.append(item)

    clean = _dedupe(clean)
    clean.sort(
        key=lambda x: (
            x.get("_score", 0),
            int(x.get("year") or 0) if str(x.get("year") or "").isdigit() else 0,
        ),
        reverse=True,
    )

    for x in clean:
        x.pop("_score", None)

    return clean[:limit]


def build_query(question: str) -> str:
    q = str(question or "").strip()
    chunks = []
    for trigger, expansion in QUERY_HINTS.items():
        if trigger.lower() in q.lower():
            chunks.append(expansion)

    eng = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{1,}", q)
    if eng:
        chunks.append(" ".join(eng[:20]))

    if not chunks:
        chunks.append("KDP DKDP crystal " + q)

    return " ".join(dict.fromkeys(" ".join(chunks).split()))[:650]


def search_crossref(question: str, max_results: int = 6) -> List[Dict]:
    response = requests.get(
        CROSSREF_URL,
        params={
            "query.bibliographic": build_query(question),
            "rows": max_results,
            "select": "DOI,title,author,published,published-print,published-online,issued,created,container-title,URL,abstract,type",
        },
        headers={"User-Agent": "KDP-DKDP-Research-Agent/1.1"},
        timeout=5,
    )
    response.raise_for_status()

    out = []
    for item in response.json().get("message", {}).get("items", []):
        titles = item.get("title") or []
        title = _strip(titles[0] if titles else "")
        if not title:
            continue

        container = item.get("container-title") or []
        abstract = _strip(item.get("abstract") or "")

        out.append({
            "source_type": "学术元数据",
            "title": title,
            "year": _year(item),
            "journal": _strip(container[0] if container else ""),
            "doi": str(item.get("DOI") or "").strip(),
            "url": str(item.get("URL") or "").strip(),
            "snippet": abstract[:1600] if abstract else (
                "仅返回书目信息；可用于定位论文，不能单独证明具体机理或精确数值。"
            ),
            "has_abstract": bool(abstract),
        })
    return out


def search_openalex_optional(question: str, max_results: int = 5) -> List[Dict]:
    api_key = _secret("OPENALEX_API_KEY")
    if not api_key:
        return []

    response = requests.get(
        "https://api.openalex.org/works",
        params={
            "search": build_query(question),
            "per_page": max_results,
            "api_key": api_key,
            "select": "id,doi,title,publication_year,primary_location,abstract_inverted_index",
        },
        timeout=5,
    )
    response.raise_for_status()

    out = []
    for item in response.json().get("results", []):
        title = _strip(item.get("title") or "")
        if not title:
            continue

        inv = item.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            positions = []
            for word, idxs in inv.items():
                for idx in idxs:
                    positions.append((idx, word))
            positions.sort()
            abstract = " ".join(word for _, word in positions)

        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}

        out.append({
            "source_type": "学术检索",
            "title": title,
            "year": item.get("publication_year") or "",
            "journal": str(source.get("display_name") or ""),
            "doi": str(item.get("doi") or "").replace("https://doi.org/", ""),
            "url": str(item.get("id") or ""),
            "snippet": abstract[:1600] if abstract else "仅返回书目信息。",
            "has_abstract": bool(abstract),
        })
    return out


def search_web(question: str, max_results: int = 4) -> List[Dict]:
    from ddgs import DDGS

    raw = DDGS(timeout=4).text(
        build_query(question),
        region="wt-wt",
        safesearch="moderate",
        max_results=max_results,
        backend="auto",
    )

    out = []
    for item in raw or []:
        title = _strip(item.get("title") or "")
        url = str(item.get("href") or item.get("url") or "").strip()
        body = _strip(item.get("body") or "")
        if title and url:
            out.append({
                "source_type": "网页资料",
                "title": _compact_title(title, 220),
                "year": "",
                "journal": "",
                "doi": "",
                "url": url,
                "snippet": body[:650],
                "has_abstract": False,
            })
    return out


def _dedupe(items: List[Dict]) -> List[Dict]:
    seen_doi, seen_title, seen_url = set(), set(), set()
    out = []
    for x in items:
        doi = str(x.get("doi") or "").lower().strip()
        title = _title_key(x.get("title") or "")
        url = str(x.get("url") or "").lower().strip()

        if (doi and doi in seen_doi) or (title and title in seen_title) or (url and url in seen_url):
            continue

        if doi:
            seen_doi.add(doi)
        if title:
            seen_title.add(title)
        if url:
            seen_url.add(url)
        out.append(x)
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def research_web(question: str) -> Tuple[str, List[Dict], Dict]:
    """
    三路检索并行执行，结果缓存1小时。
    同一问题再次提问时几乎不再等待外部搜索。
    """
    jobs = {
        "crossref": lambda: search_crossref(question, 6),
        "openalex": lambda: search_openalex_optional(question, 5),
        "web": lambda: search_web(question, 4),
    }

    status = {}
    results = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                rows = future.result()
                results.extend(rows)
                status[name] = f"成功 {len(rows)}" if rows else "无结果/未配置"
            except Exception as exc:
                status[name] = f"失败 {type(exc).__name__}"

    # 外部检索必须先经过KDP/DKDP材料相关性闸门。
    # 这一步会过滤掉“石墨烯 vacancy”“其他有机二氢磷酸盐”
    # 以及搜索引擎误抓取的植物学/目录页等结果。
    results = _filter_and_rank(results, question, limit=8)

    blocks = []
    for i, item in enumerate(results, 1):
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

    return "\n\n".join(blocks), results, status


def source_links_markdown(sources: List[Dict]) -> str:
    if not sources:
        return ""

    lines = ["", "---", "### 补充来源"]
    for item in sources:
        no = item.get("编号", "W?")
        title = _compact_title(str(item.get("title") or "来源"), 180).replace("[", "\\[").replace("]", "\\]")
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
