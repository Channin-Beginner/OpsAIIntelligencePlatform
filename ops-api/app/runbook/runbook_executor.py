"""Runbook 沙箱执行器（阶段四 4.4）。

仅允许对本机 EcomAI Admin chaos demo API 发起 HTTP 请求，禁止 SSH / 外网 / 非白名单路径。
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx

from app.common.exceptions import BadRequestError
from app.config import get_settings

ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})
ALLOWED_PATH_PREFIX = "/admin/chaos/"
ALLOWED_METHODS = frozenset({"GET", "POST"})


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def resolve_action_url(path_or_url: str) -> str:
    """将相对 path 或绝对 URL 解析为可请求地址，并校验沙箱白名单。"""
    raw = path_or_url.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_HOSTS:
            raise BadRequestError(message=f"沙箱拒绝：不允许访问主机 {host}")
        if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
            raise BadRequestError(message=f"沙箱拒绝：路径须以 {ALLOWED_PATH_PREFIX} 开头")
        return raw

    if not raw.startswith("/"):
        raw = f"/{raw}"
    if not raw.startswith(ALLOWED_PATH_PREFIX):
        raise BadRequestError(message=f"沙箱拒绝：路径须以 {ALLOWED_PATH_PREFIX} 开头")

    base = _normalize_base_url(get_settings().ecom_admin_base_url)
    parsed_base = urlparse(base)
    host = (parsed_base.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise BadRequestError(message=f"沙箱拒绝：ECOM_ADMIN_BASE_URL 主机不在白名单 ({host})")
    return f"{base}{raw}"


def execute_http_step(action: dict[str, Any]) -> dict[str, Any]:
    """执行单步 HTTP 动作，返回结构化结果。"""
    method = str(action.get("method") or "GET").upper()
    if method not in ALLOWED_METHODS:
        raise BadRequestError(message=f"沙箱拒绝：不允许 HTTP 方法 {method}")

    path = action.get("path") or action.get("url")
    if not path:
        raise BadRequestError(message="HTTP 步骤缺少 path 或 url")

    url = resolve_action_url(str(path))
    body = action.get("body")
    timeout = float(action.get("timeout_seconds") or get_settings().runbook_http_timeout)

    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=body if body is not None else None)
    except httpx.RequestError as exc:
        return {
            "success": False,
            "method": method,
            "url": url,
            "error": str(exc),
        }

    text_preview = response.text[:500] if response.text else ""
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        response_json = None

    return {
        "success": 200 <= response.status_code < 300,
        "method": method,
        "url": url,
        "status_code": response.status_code,
        "response_preview": text_preview,
        "response_json": response_json,
    }


def execute_step(step: dict[str, Any]) -> dict[str, Any]:
    """执行单个 Runbook 步骤。"""
    order = step.get("order")
    title = step.get("title") or f"step-{order}"
    action_type = step.get("action_type") or "manual"

    result: dict[str, Any] = {
        "order": order,
        "title": title,
        "action_type": action_type,
        "status": "pending",
    }

    if action_type == "manual":
        result["status"] = "manual"
        result["message"] = step.get("description") or "需人工完成"
        return result

    if action_type == "http":
        action = step.get("action") or {}
        http_result = execute_http_step(action)
        result["http"] = http_result
        result["status"] = "success" if http_result.get("success") else "failed"
        if not http_result.get("success"):
            preview = http_result.get("response_preview") or ""
            base_err = http_result.get("error") or f"HTTP {http_result.get('status_code')}"
            if preview and preview not in base_err:
                result["error"] = f"{base_err}: {preview[:200]}"
            else:
                result["error"] = base_err
        return result

    result["status"] = "skipped"
    result["error"] = f"未知 action_type: {action_type}"
    return result


def execute_runbook_steps(steps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool, str | None]:
    """
    顺序执行全部步骤。
    返回 (step_results, overall_success, error_message)。
    """
    ordered = sorted(steps, key=lambda s: int(s.get("order") or 0))
    results: list[dict[str, Any]] = []
    for step in ordered:
        step_result = execute_step(step)
        results.append(step_result)
        if step_result.get("action_type") == "http" and step_result.get("status") == "failed":
            err = step_result.get("error") or "HTTP 步骤失败"
            return results, False, str(err)

    return results, True, None
