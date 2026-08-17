
from __future__ import annotations

import functools
import hashlib
import hmac
import time
import traceback

import streamlit as st


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


def access_code_enabled() -> bool:
    return bool(str(_secret("APP_ACCESS_CODE", "") or "").strip())


def ai_unlocked() -> bool:
    if not access_code_enabled():
        return True
    return bool(st.session_state.get("_kdp_ai_unlocked", False))


def sidebar_security():
    """
    公开浏览不受影响；若在 Streamlit Secrets 配置 APP_ACCESS_CODE，
    则所有 AI / 报告生成类功能需要先在侧栏解锁。
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='font-size:11px;color:#7889A1;letter-spacing:.12em;font-weight:700;'>ACCESS</div>",
        unsafe_allow_html=True,
    )

    if not access_code_enabled():
        st.sidebar.caption("公开浏览已启用；模型访问码尚未配置。会话限流仍然生效。")
        return

    if ai_unlocked():
        st.sidebar.success("模型分析与报告生成功能已解锁")
        if st.sidebar.button("锁定模型功能", key="_kdp_lock_ai", width="stretch"):
            st.session_state["_kdp_ai_unlocked"] = False
            st.rerun()
        return

    code = st.sidebar.text_input(
        "访问码",
        type="password",
        key="_kdp_access_code_input",
        placeholder="输入访问码后解锁模型分析",
    )

    if st.sidebar.button("解锁模型功能", key="_kdp_unlock_ai", width="stretch"):
        expected = str(_secret("APP_ACCESS_CODE", "") or "")
        if hmac.compare_digest(str(code or ""), expected):
            st.session_state["_kdp_ai_unlocked"] = True
            st.sidebar.success("已解锁")
            st.rerun()
        else:
            st.sidebar.error("访问码错误")


def validate_user_text(text: str, field_name: str = "输入"):
    max_chars = _int_secret("AI_MAX_INPUT_CHARS", 6000)
    text = str(text or "")
    if len(text) > max_chars:
        raise ValueError(f"{field_name}过长，最多允许 {max_chars} 个字符。")
    return text


def enforce_ai_quota():
    """
    轻量防刷：
    - 可选访问码
    - 单会话调用次数限制
    - 最小调用间隔
    - 输入长度限制由 validate_user_text 负责

    注：这是公开科研演示站的轻量保护，不等同于企业级账号/计费系统。
    """
    if not ai_unlocked():
        raise PermissionError("模型分析功能需要访问码。请先在左侧边栏解锁。")

    max_calls = _int_secret("AI_MAX_CALLS_PER_SESSION", 20)
    cooldown = _int_secret("AI_COOLDOWN_SECONDS", 4)

    used = int(st.session_state.get("_kdp_ai_calls_used", 0))
    last = float(st.session_state.get("_kdp_ai_last_call", 0.0))
    now = time.time()

    if used >= max_calls:
        raise PermissionError(
            f"本次浏览会话已达到 AI 调用上限（{max_calls} 次）。"
        )

    wait = cooldown - (now - last)
    if wait > 0:
        raise PermissionError(
            f"请求过于频繁，请约 {max(1, int(wait + 0.999))} 秒后再试。"
        )

    st.session_state["_kdp_ai_calls_used"] = used + 1
    st.session_state["_kdp_ai_last_call"] = now



def guard_duplicate_ai_request(payload: str, window_seconds: int = 30):
    """
    拦截短时间内完全相同的模型请求，降低重复点击/重复提交造成的API浪费。
    只作用于当前浏览会话，不保存用户内容到外部。
    """
    payload = str(payload or "")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    now = time.time()
    last_digest = st.session_state.get("_kdp_last_ai_digest", "")
    last_time = float(st.session_state.get("_kdp_last_ai_digest_time", 0.0))

    if digest == last_digest and now - last_time < window_seconds:
        wait = max(1, int(window_seconds - (now - last_time)))
        raise PermissionError(
            f"检测到与刚才完全相同的请求。为避免重复扣费，请约 {wait} 秒后再试，"
            "或修改问题/参数后重新提交。"
        )

    st.session_state["_kdp_last_ai_digest"] = digest
    st.session_state["_kdp_last_ai_digest_time"] = now



def remaining_ai_calls() -> int:
    max_calls = _int_secret("AI_MAX_CALLS_PER_SESSION", 20)
    used = int(st.session_state.get("_kdp_ai_calls_used", 0))
    return max(0, max_calls - used)


def safe_error(public_message: str, exc: Exception | None = None):
    """
    用户侧不展示内部文件路径/traceback；详细错误仅进入 Streamlit Cloud 日志。
    """
    if exc is not None:
        print("[KDP Research OS] internal error:")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    st.error(public_message)


def safe_page(func):
    """
    包装页面级异常，避免公开站直接暴露 traceback、服务器路径和代码行号。
    """
    @functools.wraps(func)
    def wrapped():
        try:
            return func()
        except Exception as exc:
            print(f"[KDP Research OS] page={func.__name__}")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
            st.error("该页面暂时无法完成加载。详细错误已记录，请稍后重试。")
    return wrapped
