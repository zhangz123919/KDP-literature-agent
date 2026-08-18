
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"KDPVAULT1\n"
PBKDF2_ROUNDS = 390_000
DEFAULT_TIMEOUT_MIN = 20
DEFAULT_MAX_FILE_MB = 8
DEFAULT_MAX_TOTAL_MB = 30


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _int_secret(name: str, default: int) -> int:
    try:
        return int(_secret(name, default))
    except Exception:
        return default


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ROUNDS,
        dklen=32,
    )


def _pack(vault: Dict[str, Any], key: bytes, salt: bytes) -> bytes:
    raw = json.dumps(
        vault,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    nonce = os.urandom(12)
    cipher = AESGCM(key).encrypt(nonce, raw, MAGIC)
    return MAGIC + salt + nonce + cipher


def _unpack(blob: bytes, password: str):
    if not blob or not blob.startswith(MAGIC):
        raise ValueError("不是有效的 KDP 实验保险库文件。")
    pos = len(MAGIC)
    salt = blob[pos:pos + 16]
    nonce = blob[pos + 16:pos + 28]
    cipher = blob[pos + 28:]
    if len(salt) != 16 or len(nonce) != 12 or not cipher:
        raise ValueError("保险库文件结构不完整。")

    key = _derive_key(password, salt)
    try:
        raw = AESGCM(key).decrypt(nonce, cipher, MAGIC)
    except Exception as exc:
        raise PermissionError("密码错误，或保险库文件已损坏。") from exc

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("保险库内容无法解析。") from exc
    return data, key, salt


def _init_state():
    st.session_state.setdefault("_exp_vault_unlocked", False)
    st.session_state.setdefault("_exp_vault_data", None)
    st.session_state.setdefault("_exp_vault_key", None)
    st.session_state.setdefault("_exp_vault_salt", None)
    st.session_state.setdefault("_exp_vault_blob", None)
    st.session_state.setdefault("_exp_vault_last_active", 0.0)
    st.session_state.setdefault("_exp_vault_fail_count", 0)
    st.session_state.setdefault("_exp_vault_lockout_until", 0.0)


def _blank_vault(project_id: str, project_name: str) -> Dict[str, Any]:
    ts = _now()
    return {
        "format": "KDP Experiment Vault",
        "version": 1,
        "project_id": str(project_id or ""),
        "project_name": str(project_name or "KDP研究项目"),
        "created_at": ts,
        "updated_at": ts,
        "records": [],
        "attachments": [],
        "audit": [
            {
                "time": ts,
                "action": "CREATE_VAULT",
                "record_id": "",
                "detail": "创建实验数据保险库",
            }
        ],
    }


def password_policy_ok(password: str):
    password = str(password or "")
    if len(password) < 10:
        return False, "密码至少 10 位。"
    if password.isdigit() or password.isalpha():
        return False, "不要只使用纯数字或纯字母。建议使用字母 + 数字 + 符号。"
    return True, ""


def create_vault(password: str, project_id: str, project_name: str):
    _init_state()
    ok, msg = password_policy_ok(password)
    if not ok:
        raise ValueError(msg)

    salt = os.urandom(16)
    key = _derive_key(password, salt)
    data = _blank_vault(project_id, project_name)

    st.session_state["_exp_vault_data"] = data
    st.session_state["_exp_vault_key"] = key
    st.session_state["_exp_vault_salt"] = salt
    st.session_state["_exp_vault_unlocked"] = True
    st.session_state["_exp_vault_last_active"] = time.time()
    st.session_state["_exp_vault_fail_count"] = 0
    _snapshot()
    return data


def has_session_vault() -> bool:
    _init_state()
    return bool(st.session_state.get("_exp_vault_blob"))


def vault_unlocked() -> bool:
    _init_state()
    if not st.session_state.get("_exp_vault_unlocked"):
        return False

    timeout_min = _int_secret("EXPERIMENT_VAULT_TIMEOUT_MINUTES", DEFAULT_TIMEOUT_MIN)
    last = float(st.session_state.get("_exp_vault_last_active", 0.0) or 0.0)
    if last and time.time() - last > max(5, timeout_min) * 60:
        lock_vault(reason="自动锁定")
        return False
    return True


def touch_vault():
    if vault_unlocked():
        st.session_state["_exp_vault_last_active"] = time.time()


def current_vault() -> Optional[Dict[str, Any]]:
    if not vault_unlocked():
        return None
    touch_vault()
    return st.session_state.get("_exp_vault_data")


def _snapshot():
    if not st.session_state.get("_exp_vault_unlocked"):
        return
    data = st.session_state.get("_exp_vault_data")
    key = st.session_state.get("_exp_vault_key")
    salt = st.session_state.get("_exp_vault_salt")
    if not data or not key or not salt:
        return
    data["updated_at"] = _now()
    st.session_state["_exp_vault_blob"] = _pack(data, key, salt)
    st.session_state["_exp_vault_last_active"] = time.time()


def export_blob() -> bytes:
    if not vault_unlocked():
        raise PermissionError("实验保险库尚未解锁。")
    _snapshot()
    return bytes(st.session_state["_exp_vault_blob"])


def lock_vault(reason: str = "手动锁定"):
    _init_state()
    if st.session_state.get("_exp_vault_unlocked"):
        try:
            _audit("LOCK", "", reason)
            _snapshot()
        except Exception:
            pass

    # 清理明文和密钥；只保留加密快照
    st.session_state["_exp_vault_data"] = None
    st.session_state["_exp_vault_key"] = None
    st.session_state["_exp_vault_salt"] = None
    st.session_state["_exp_vault_unlocked"] = False
    st.session_state["_exp_vault_last_active"] = 0.0


def _register_failure():
    _init_state()
    count = int(st.session_state.get("_exp_vault_fail_count", 0)) + 1
    st.session_state["_exp_vault_fail_count"] = count
    if count >= 5:
        st.session_state["_exp_vault_lockout_until"] = time.time() + 300
        st.session_state["_exp_vault_fail_count"] = 0


def lockout_seconds() -> int:
    _init_state()
    until = float(st.session_state.get("_exp_vault_lockout_until", 0.0) or 0.0)
    return max(0, int(until - time.time()))


def unlock_session_vault(password: str):
    _init_state()
    wait = lockout_seconds()
    if wait > 0:
        raise PermissionError(f"连续密码错误次数过多，请约 {wait} 秒后再试。")

    blob = st.session_state.get("_exp_vault_blob")
    if not blob:
        raise ValueError("当前会话没有可解锁的实验保险库。")

    try:
        data, key, salt = _unpack(blob, password)
    except Exception:
        _register_failure()
        raise

    st.session_state["_exp_vault_data"] = data
    st.session_state["_exp_vault_key"] = key
    st.session_state["_exp_vault_salt"] = salt
    st.session_state["_exp_vault_unlocked"] = True
    st.session_state["_exp_vault_last_active"] = time.time()
    st.session_state["_exp_vault_fail_count"] = 0
    _audit("UNLOCK", "", "重新解锁当前会话保险库")
    _snapshot()
    return data


def import_vault(blob: bytes, password: str, bind_project_id: str = "", bind_project_name: str = ""):
    _init_state()
    wait = lockout_seconds()
    if wait > 0:
        raise PermissionError(f"连续密码错误次数过多，请约 {wait} 秒后再试。")

    try:
        data, key, salt = _unpack(blob, password)
    except Exception:
        _register_failure()
        raise

    if bind_project_id:
        data["project_id"] = bind_project_id
    if bind_project_name:
        data["project_name"] = bind_project_name

    st.session_state["_exp_vault_data"] = data
    st.session_state["_exp_vault_key"] = key
    st.session_state["_exp_vault_salt"] = salt
    st.session_state["_exp_vault_blob"] = bytes(blob)
    st.session_state["_exp_vault_unlocked"] = True
    st.session_state["_exp_vault_last_active"] = time.time()
    st.session_state["_exp_vault_fail_count"] = 0
    _audit("IMPORT", "", "导入加密实验保险库，并绑定到当前研究项目")
    _snapshot()
    return data


def rotate_password(new_password: str):
    if not vault_unlocked():
        raise PermissionError("实验保险库尚未解锁。")
    ok, msg = password_policy_ok(new_password)
    if not ok:
        raise ValueError(msg)

    salt = os.urandom(16)
    key = _derive_key(new_password, salt)
    st.session_state["_exp_vault_key"] = key
    st.session_state["_exp_vault_salt"] = salt
    _audit("ROTATE_PASSWORD", "", "实验保险库密码已更换")
    _snapshot()


def _audit(action: str, record_id: str = "", detail: str = ""):
    data = st.session_state.get("_exp_vault_data")
    if not data:
        return
    data.setdefault("audit", []).append(
        {
            "time": _now(),
            "action": str(action),
            "record_id": str(record_id or ""),
            "detail": str(detail or "")[:240],
        }
    )
    data["audit"] = data["audit"][-300:]


def audit_log() -> List[Dict[str, Any]]:
    data = current_vault()
    if not data:
        return []
    return list(reversed(data.get("audit", [])))


def project_matches(project_id: str) -> bool:
    data = current_vault()
    if not data:
        return False
    return str(data.get("project_id", "")) == str(project_id or "")


def list_records(include_trash: bool = False) -> List[Dict[str, Any]]:
    data = current_vault()
    if not data:
        return []
    rows = data.get("records", [])
    if not include_trash:
        rows = [x for x in rows if x.get("status", "active") != "trash"]
    return sorted(rows, key=lambda x: x.get("updated_at", ""), reverse=True)


def get_record(record_id: str) -> Optional[Dict[str, Any]]:
    for row in list_records(include_trash=True):
        if row.get("id") == record_id:
            return row
    return None


def save_record(
    payload: Dict[str, Any],
    summary: str = "",
    status: str = "active",
) -> Dict[str, Any]:
    data = current_vault()
    if data is None:
        raise PermissionError("实验保险库尚未解锁。")

    ts = _now()
    rec = {
        "id": _new_id("VEXP"),
        "project_id": data.get("project_id", ""),
        "experiment_id": str(payload.get("experiment_id") or "").strip() or _new_id("EXP"),
        "summary": str(summary or "").strip(),
        "status": status,
        "revision": 1,
        "payload": deepcopy(payload),
        "versions": [],
        "created_at": ts,
        "updated_at": ts,
    }
    data.setdefault("records", []).append(rec)
    _audit("CREATE_RECORD", rec["id"], rec["experiment_id"])
    _snapshot()
    return rec


def update_record(
    record_id: str,
    payload_updates: Optional[Dict[str, Any]] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    data = current_vault()
    if data is None:
        raise PermissionError("实验保险库尚未解锁。")

    rec = get_record(record_id)
    if not rec:
        raise KeyError("找不到实验记录。")

    rec.setdefault("versions", []).append(
        {
            "revision": rec.get("revision", 1),
            "time": rec.get("updated_at", ""),
            "summary": rec.get("summary", ""),
            "payload": deepcopy(rec.get("payload", {})),
        }
    )
    rec["versions"] = rec["versions"][-20:]

    if payload_updates:
        rec.setdefault("payload", {}).update(deepcopy(payload_updates))
        if "experiment_id" in payload_updates and payload_updates["experiment_id"]:
            rec["experiment_id"] = str(payload_updates["experiment_id"])
    if summary is not None:
        rec["summary"] = str(summary)
    if status is not None:
        rec["status"] = str(status)

    rec["revision"] = int(rec.get("revision", 1)) + 1
    rec["updated_at"] = _now()
    _audit("UPDATE_RECORD", rec["id"], f"{rec['experiment_id']} · rev {rec['revision']}")
    _snapshot()
    return rec


def duplicate_record(record_id: str, new_experiment_id: str, clear_results: bool = True):
    src = get_record(record_id)
    if not src:
        raise KeyError("找不到实验记录。")

    p = deepcopy(src.get("payload", {}))
    p["experiment_id"] = str(new_experiment_id or _new_id("EXP"))
    p["date"] = datetime.now().date().isoformat()

    if clear_results:
        for key in [
            "cracked", "crack_time", "crack_latency_min", "crack_count",
            "crack_location", "crack_direction", "inclusion", "scattering",
            "final_mass_g", "final_length_mm", "final_width_mm", "final_height_mm",
            "crystal_size", "white_striation", "white_density_grade", "white_location",
            "white_direction", "white_width_mm", "white_spacing_mm", "white_first_stage", "white_notes",
            "hair_inclusion", "hair_count", "hair_length_mm", "hair_chain_density_per_mm",
            "hair_orientation_deg", "hair_location", "hair_notes",
            "microscopy_summary", "xrd_summary", "raman_summary",
            "ftir_summary", "other_characterization", "result_summary",
            "current_hypothesis", "next_step",
        ]:
            if key in {"cracked", "inclusion", "scattering", "white_striation", "white_density_grade", "hair_inclusion"}:
                p[key] = "未知"
            else:
                p[key] = None if key.endswith(("_g", "_mm", "_min")) or key == "crack_count" else ""

    rec = save_record(
        p,
        summary=f"复制自 {src.get('experiment_id','')}，作为新一轮实验基线。",
    )
    _audit("DUPLICATE_RECORD", rec["id"], f"source={record_id}")
    _snapshot()
    return rec


def trash_record(record_id: str):
    rec = get_record(record_id)
    if not rec:
        raise KeyError("找不到实验记录。")
    rec["status"] = "trash"
    rec["updated_at"] = _now()
    _audit("TRASH_RECORD", record_id, rec.get("experiment_id", ""))
    _snapshot()


def restore_record(record_id: str):
    rec = get_record(record_id)
    if not rec:
        raise KeyError("找不到实验记录。")
    rec["status"] = "active"
    rec["updated_at"] = _now()
    _audit("RESTORE_RECORD", record_id, rec.get("experiment_id", ""))
    _snapshot()


def _attachment_total_bytes(data: Dict[str, Any]) -> int:
    total = 0
    for x in data.get("attachments", []):
        total += int(x.get("size_bytes", 0) or 0)
    return total


def add_attachment(uploaded_file, record_id: str) -> Dict[str, Any]:
    data = current_vault()
    if data is None:
        raise PermissionError("实验保险库尚未解锁。")

    rec = get_record(record_id)
    if not rec:
        raise KeyError("找不到实验记录。")

    raw = uploaded_file.getvalue()
    max_file = _int_secret("EXPERIMENT_VAULT_MAX_FILE_MB", DEFAULT_MAX_FILE_MB) * 1024 * 1024
    max_total = _int_secret("EXPERIMENT_VAULT_MAX_TOTAL_MB", DEFAULT_MAX_TOTAL_MB) * 1024 * 1024

    if len(raw) > max_file:
        raise ValueError(f"单个附件超过限制（当前 {max_file // 1024 // 1024} MB）。")
    if _attachment_total_bytes(data) + len(raw) > max_total:
        raise ValueError(f"当前保险库附件总量将超过限制（{max_total // 1024 // 1024} MB）。")

    digest = hashlib.sha256(raw).hexdigest()
    att = {
        "id": _new_id("VATT"),
        "record_id": record_id,
        "experiment_id": rec.get("experiment_id", ""),
        "name": str(uploaded_file.name or "attachment.bin"),
        "mime": str(getattr(uploaded_file, "type", "") or "application/octet-stream"),
        "sha256": digest,
        "size_bytes": len(raw),
        "data_b64": base64.b64encode(raw).decode("ascii"),
        "created_at": _now(),
    }
    data.setdefault("attachments", []).append(att)
    _audit("ADD_ATTACHMENT", record_id, f"{att['name']} · {len(raw)} bytes")
    _snapshot()
    return {k: v for k, v in att.items() if k != "data_b64"}


def list_attachments(record_id: Optional[str] = None):
    data = current_vault()
    if not data:
        return []
    rows = data.get("attachments", [])
    if record_id:
        rows = [x for x in rows if x.get("record_id") == record_id]
    return [
        {k: v for k, v in x.items() if k != "data_b64"}
        for x in rows
    ]


def attachment_bytes(attachment_id: str) -> bytes:
    data = current_vault()
    if not data:
        raise PermissionError("实验保险库尚未解锁。")
    for x in data.get("attachments", []):
        if x.get("id") == attachment_id:
            return base64.b64decode(x.get("data_b64", ""))
    raise KeyError("找不到附件。")


def remove_attachment(attachment_id: str):
    data = current_vault()
    if not data:
        raise PermissionError("实验保险库尚未解锁。")
    before = len(data.get("attachments", []))
    data["attachments"] = [
        x for x in data.get("attachments", [])
        if x.get("id") != attachment_id
    ]
    if len(data["attachments"]) < before:
        _audit("REMOVE_ATTACHMENT", "", attachment_id)
        _snapshot()


def vault_stats():
    data = current_vault()
    if not data:
        return {
            "records": 0,
            "attachments": 0,
            "attachment_bytes": 0,
            "updated_at": "",
        }
    active = [x for x in data.get("records", []) if x.get("status") != "trash"]
    return {
        "records": len(active),
        "attachments": len(data.get("attachments", [])),
        "attachment_bytes": _attachment_total_bytes(data),
        "updated_at": data.get("updated_at", ""),
    }


def sanitized_summary() -> str:
    """
    只生成不含具体配方/温度/速率数值的统计摘要。
    该摘要可由用户主动保存到普通项目记忆供AI参考。
    """
    rows = list_records()
    if not rows:
        return "当前实验保险库暂无有效实验记录。"

    cracked = 0
    labelled = 0
    inclusion = 0
    scattering = 0
    white = 0
    hair = 0

    for r in rows:
        p = r.get("payload", {})
        if p.get("cracked") in {"是", "否"}:
            labelled += 1
        if p.get("cracked") == "是":
            cracked += 1
        if p.get("inclusion") == "明显":
            inclusion += 1
        if p.get("scattering") == "明显":
            scattering += 1
        if p.get("white_striation") == "有":
            white += 1
        if p.get("hair_inclusion") == "有":
            hair += 1

    return (
        f"当前项目共有 {len(rows)} 组受保护实验记录；"
        f"其中 {labelled} 组已有明确开裂标签，开裂记录 {cracked} 组；"
        f"明显包裹体记录 {inclusion} 组，明显散射记录 {scattering} 组；"
        f"白纹记录 {white} 组，串丝记录 {hair} 组。"
        "本摘要不包含原始配方、具体工艺参数、附件或精确数值。"
    )


def sidebar_vault_status():
    _init_state()
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='font-size:11px;color:#7889A1;letter-spacing:.12em;font-weight:700;'>EXPERIMENT VAULT</div>",
        unsafe_allow_html=True,
    )

    if vault_unlocked():
        stats = vault_stats()
        st.sidebar.success(f"实验保险库已解锁 · {stats['records']} 条")
        if st.sidebar.button("立即锁定实验数据", key="_lock_exp_vault", width="stretch"):
            lock_vault("侧栏手动锁定")
            st.rerun()
    elif has_session_vault():
        st.sidebar.caption("实验保险库：已锁定")
    else:
        st.sidebar.caption("实验保险库：尚未创建/导入")
