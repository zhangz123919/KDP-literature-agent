from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import streamlit as st


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def private_mode_enabled() -> bool:
    """
    Persistent research storage is deliberately opt-in.
    BOTH conditions are required so it is difficult to accidentally enable
    private experiment storage on a public Streamlit deployment.
    """
    return _truthy(_secret("PRIVATE_RESEARCH_MODE", False)) and str(
        _secret("PRIVATE_STORAGE_ACK", "")
    ).strip() == "LOCAL_ONLY"


def allow_private_external_ai() -> bool:
    """Highest-confidentiality data must NOT leave the private environment by default."""
    return private_mode_enabled() and _truthy(
        _secret("ALLOW_PRIVATE_DATA_EXTERNAL_AI", False)
    )


def allow_experiment_external_ai() -> bool:
    """Even in demo/session mode, experiment-like records are excluded from external AI by default."""
    if private_mode_enabled():
        return allow_private_external_ai()
    return _truthy(_secret("ALLOW_EXPERIMENT_DATA_EXTERNAL_AI", False))


def storage_mode_label() -> str:
    if private_mode_enabled():
        return "本地私密持久化"
    return "会话临时记忆（不落盘）"


def storage_security_note() -> str:
    if private_mode_enabled():
        ai = "允许" if allow_private_external_ai() else "默认禁止"
        return (
            f"当前启用本地私密持久化；外部AI读取私密项目数据：{ai}。"
            "仍需由本机/内网负责磁盘加密、账户权限、备份和物理安全。"
        )
    return (
        "项目记忆：会话模式 ｜ 实验数据：独立加密保险库 ｜ 外部AI：默认不读取实验原始数据"
    )


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def new_experiment_id() -> str:
    return "EXP-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def _db_path() -> Path:
    raw = str(_secret("PRIVATE_RESEARCH_DB_PATH", "~/.kdp_private/kdp_research.db"))
    p = Path(raw).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _attachment_root() -> Path:
    raw = str(_secret("PRIVATE_ATTACHMENT_DIR", "~/.kdp_private/attachments"))
    p = Path(raw).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            question TEXT DEFAULT '',
            goal TEXT DEFAULT '',
            status TEXT DEFAULT '进行中',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            payload_json TEXT DEFAULT '{}',
            source_module TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            item_id TEXT,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    return conn


def _session_init():
    st.session_state.setdefault("_kdp_memory_projects", {})
    st.session_state.setdefault("_kdp_memory_items", [])
    st.session_state.setdefault("_kdp_active_project_id", None)


def _as_project(row) -> Dict[str, Any]:
    return dict(row) if row is not None else {}


def list_projects() -> List[Dict[str, Any]]:
    if private_mode_enabled():
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    _session_init()
    rows = list(st.session_state["_kdp_memory_projects"].values())
    return sorted(rows, key=lambda x: x.get("updated_at", ""), reverse=True)


def create_project(
    name: str,
    question: str = "",
    goal: str = "",
    status: str = "进行中",
) -> Dict[str, Any]:
    name = str(name or "").strip() or "未命名KDP研究项目"
    ts = _now()
    project = {
        "id": _new_id("PRJ"),
        "name": name,
        "question": str(question or "").strip(),
        "goal": str(goal or "").strip(),
        "status": status,
        "created_at": ts,
        "updated_at": ts,
    }

    if private_mode_enabled():
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO projects(id,name,question,goal,status,created_at,updated_at)
                VALUES(:id,:name,:question,:goal,:status,:created_at,:updated_at)
                """,
                project,
            )
            conn.commit()
    else:
        _session_init()
        st.session_state["_kdp_memory_projects"][project["id"]] = project

    st.session_state["_kdp_active_project_id"] = project["id"]
    return project


def ensure_default_project() -> Dict[str, Any]:
    projects = list_projects()
    active = st.session_state.get("_kdp_active_project_id")

    if projects:
        ids = {p["id"] for p in projects}
        if active not in ids:
            st.session_state["_kdp_active_project_id"] = projects[0]["id"]
        return get_active_project()

    return create_project(
        "KDP研究主项目",
        question="围绕KDP晶体缺陷、开裂及其形成机制开展研究",
        goal="形成可验证的科学问题、实验路线与理论计算路线",
    )


def set_active_project(project_id: str):
    ids = {p["id"] for p in list_projects()}
    if project_id in ids:
        st.session_state["_kdp_active_project_id"] = project_id


def get_active_project() -> Dict[str, Any]:
    projects = list_projects()
    if not projects:
        return {}

    active = st.session_state.get("_kdp_active_project_id")
    for p in projects:
        if p["id"] == active:
            return p
    st.session_state["_kdp_active_project_id"] = projects[0]["id"]
    return projects[0]


def update_project(project_id: str, **fields) -> Dict[str, Any]:
    allowed = {"name", "question", "goal", "status"}
    updates = {k: str(v or "").strip() for k, v in fields.items() if k in allowed}
    if not updates:
        return get_active_project()
    updates["updated_at"] = _now()

    if private_mode_enabled():
        cols = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [project_id]
        with _connect() as conn:
            conn.execute(f"UPDATE projects SET {cols} WHERE id = ?", vals)
            conn.commit()
    else:
        _session_init()
        p = st.session_state["_kdp_memory_projects"].get(project_id)
        if p:
            p.update(updates)

    return get_active_project()


def add_item(
    item_type: str,
    title: str,
    summary: str = "",
    payload: Optional[Dict[str, Any]] = None,
    source_module: str = "",
    status: str = "active",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    project = get_active_project()
    pid = project_id or project.get("id")
    if not pid:
        project = ensure_default_project()
        pid = project["id"]

    ts = _now()
    item = {
        "id": _new_id("MEM"),
        "project_id": pid,
        "item_type": str(item_type),
        "title": str(title or "未命名记录").strip(),
        "summary": str(summary or "").strip(),
        "payload": payload or {},
        "source_module": str(source_module or ""),
        "status": str(status or "active"),
        "created_at": ts,
        "updated_at": ts,
    }

    if private_mode_enabled():
        row = dict(item)
        row["payload_json"] = json.dumps(item["payload"], ensure_ascii=False, default=str)
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO items(
                    id,project_id,item_type,title,summary,payload_json,
                    source_module,status,created_at,updated_at
                ) VALUES(
                    :id,:project_id,:item_type,:title,:summary,:payload_json,
                    :source_module,:status,:created_at,:updated_at
                )
                """,
                row,
            )
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (ts, pid),
            )
            conn.commit()
    else:
        _session_init()
        st.session_state["_kdp_memory_items"].append(item)
        p = st.session_state["_kdp_memory_projects"].get(pid)
        if p:
            p["updated_at"] = ts

    return item



def update_item(
    item_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """更新普通项目记忆中的非机密索引/记录。"""
    ts = _now()

    if private_mode_enabled():
        sets = ["updated_at = ?"]
        vals: List[Any] = [ts]

        if title is not None:
            sets.append("title = ?")
            vals.append(str(title))
        if summary is not None:
            sets.append("summary = ?")
            vals.append(str(summary))
        if payload is not None:
            sets.append("payload_json = ?")
            vals.append(json.dumps(payload, ensure_ascii=False, default=str))
        if status is not None:
            sets.append("status = ?")
            vals.append(str(status))

        vals.append(item_id)
        with _connect() as conn:
            conn.execute(
                f"UPDATE items SET {', '.join(sets)} WHERE id = ?",
                vals,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
        return _decode_db_item(row) if row else None

    _session_init()
    for x in st.session_state["_kdp_memory_items"]:
        if x.get("id") == item_id:
            if title is not None:
                x["title"] = str(title)
            if summary is not None:
                x["summary"] = str(summary)
            if payload is not None:
                x["payload"] = payload
            if status is not None:
                x["status"] = str(status)
            x["updated_at"] = ts
            return x
    return None


def _decode_db_item(row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["payload"] = json.loads(d.pop("payload_json", "{}") or "{}")
    except Exception:
        d["payload"] = {}
    return d


def list_items(
    item_type: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    project = get_active_project()
    pid = project_id or project.get("id")
    if not pid:
        return []

    if private_mode_enabled():
        sql = "SELECT * FROM items WHERE project_id = ?"
        params: List[Any] = [pid]
        if item_type:
            sql += " AND item_type = ?"
            params.append(item_type)
        sql += " ORDER BY created_at DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(int(limit))
        with _connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_decode_db_item(r) for r in rows]

    _session_init()
    rows = [
        x for x in st.session_state["_kdp_memory_items"]
        if x.get("project_id") == pid and (not item_type or x.get("item_type") == item_type)
    ]
    rows = sorted(rows, key=lambda x: x.get("created_at", ""), reverse=True)
    return rows[:limit] if limit else rows


def item_counts(project_id: Optional[str] = None) -> Dict[str, int]:
    rows = list_items(project_id=project_id)
    counts: Dict[str, int] = {}
    for x in rows:
        k = x.get("item_type", "other")
        counts[k] = counts.get(k, 0) + 1
    return counts


def item_dataframe(item_type: Optional[str] = None) -> pd.DataFrame:
    rows = list_items(item_type=item_type)
    if not rows:
        return pd.DataFrame()
    simple = []
    for x in rows:
        simple.append(
            {
                "记录ID": x.get("id"),
                "类型": x.get("item_type"),
                "标题": x.get("title"),
                "摘要": x.get("summary"),
                "来源模块": x.get("source_module"),
                "状态": x.get("status"),
                "时间": x.get("created_at"),
            }
        )
    return pd.DataFrame(simple)


def save_attachment(uploaded_file, item_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    if uploaded_file is None:
        return {"ok": False, "message": "没有文件"}
    if not private_mode_enabled():
        return {
            "ok": False,
            "message": "当前不是本地私密持久化模式，附件不会落盘。",
        }

    project = get_active_project()
    pid = project_id or project.get("id")
    if not pid:
        return {"ok": False, "message": "没有活动项目"}

    raw = uploaded_file.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    original = str(uploaded_file.name or "attachment.bin")
    suffix = Path(original).suffix[:12]
    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "_", Path(original).stem)[:60] or "file"

    folder = _attachment_root() / pid / item_id
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{safe_stem}_{digest[:12]}{suffix}"
    stored.write_bytes(raw)

    row = {
        "id": _new_id("ATT"),
        "project_id": pid,
        "item_id": item_id,
        "original_name": original,
        "stored_path": str(stored.resolve()),
        "sha256": digest,
        "size_bytes": len(raw),
        "created_at": _now(),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO attachments(
                id,project_id,item_id,original_name,stored_path,sha256,size_bytes,created_at
            ) VALUES(
                :id,:project_id,:item_id,:original_name,:stored_path,:sha256,:size_bytes,:created_at
            )
            """,
            row,
        )
        conn.commit()
    return {"ok": True, "message": "已保存到本地私密附件目录", **row}


def build_project_context(for_external_ai: bool = False, max_chars: int = 6500) -> str:
    project = get_active_project()
    if not project:
        return ""

    if for_external_ai and private_mode_enabled() and not allow_private_external_ai():
        return (
            "【项目记忆】当前项目启用了私密模式；为保护机密数据，实验/项目记忆未发送给外部AI。"
        )

    items = list_items(limit=40)

    # Experiment conditions, diagnosis details and solver results may contain confidential know-how.
    # They are not silently sent to an external model.
    if for_external_ai and not allow_experiment_external_ai():
        sensitive_types = {
            "experiment", "experiment_plan", "diagnosis", "theory_result"
        }
        items = [x for x in items if x.get("item_type") not in sensitive_types]

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for x in items:
        grouped.setdefault(x.get("item_type", "other"), []).append(x)

    labels = {
        "hypothesis": "科学假设",
        "evidence": "已保存证据",
        "experiment": "受保护实验索引",
        "experiment_plan": "实验方案",
        "diagnosis": "诊断记录",
        "theory_task": "理论计算任务",
        "theory_result": "理论计算结果",
        "direction_decision": "方向决策",
        "ai_note": "AI分析记录",
        "report": "报告/总结",
        "note": "科研备注",
    }

    lines = [
        "【当前研究项目记忆】",
        f"项目：{project.get('name','')}",
        f"研究问题：{project.get('question','') or '待补充'}",
        f"阶段目标：{project.get('goal','') or '待补充'}",
        f"状态：{project.get('status','进行中')}",
    ]

    for key in [
        "hypothesis", "direction_decision", "experiment", "diagnosis",
        "experiment_plan", "theory_task", "theory_result", "evidence", "note",
    ]:
        rows = grouped.get(key, [])[:6]
        if not rows:
            continue
        lines.append(f"\n{labels.get(key,key)}：")
        for x in rows:
            summary = (x.get("summary") or "").replace("\n", " ").strip()
            if len(summary) > 420:
                summary = summary[:420] + "…"
            lines.append(f"- {x.get('title','')}｜{summary}")

    text = "\n".join(lines)
    return text[:max_chars]


def sidebar_project_switcher():
    project = ensure_default_project()
    projects = list_projects()
    if not projects:
        return

    st.sidebar.markdown("---")
    st.sidebar.caption("当前科研项目")

    names = {f"{p['name']} · {p.get('status','进行中')}": p["id"] for p in projects}
    active = project.get("id")
    labels = list(names)
    index = 0
    for i, label in enumerate(labels):
        if names[label] == active:
            index = i
            break

    chosen = st.sidebar.selectbox(
        "项目",
        labels,
        index=index,
        label_visibility="collapsed",
        key="_sidebar_project_choice",
    )
    chosen_id = names.get(chosen)
    if chosen_id and chosen_id != active:
        set_active_project(chosen_id)
        st.rerun()

    counts = item_counts(chosen_id)
    st.sidebar.caption(
        f"记忆 {sum(counts.values())} 条 · {storage_mode_label()}"
    )
    if private_mode_enabled() and not allow_private_external_ai():
        st.sidebar.caption("私密项目记忆 → 外部AI：关闭")
    elif not private_mode_enabled() and not allow_experiment_external_ai():
        st.sidebar.caption("实验/诊断记录 → 外部AI：默认不发送")


def project_context_strip(show_security: bool = False):
    project = ensure_default_project()
    counts = item_counts(project.get("id"))
    st.caption(
        f"当前项目：**{project.get('name','')}** ｜ "
        f"状态：{project.get('status','进行中')} ｜ "
        f"已沉淀记录：{sum(counts.values())} 条"
    )
    if show_security:
        if private_mode_enabled():
            st.info(storage_security_note())
        else:
            st.warning(storage_security_note())
