"""Chaos injection helpers."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from _config import ScriptConfig  # noqa: E402


def log(message: str) -> None:
    print(f"[chaos] {message}", flush=True)


def http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: dict[str, Any] | str = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return exc.code, parsed
    except URLError as exc:
        raise RuntimeError(f"请求失败 {url}: {exc}") from exc


def try_chaos_api(
    config: ScriptConfig,
    *,
    path: str,
    method: str = "POST",
    payload: dict[str, Any] | None = None,
    base: str | None = None,
) -> bool:
    base_url = (base or config.ecom_admin_base_url).rstrip("/")
    url = f"{base_url}{path}"
    try:
        status, body = http_json(method, url, payload=payload, timeout=15.0)
    except RuntimeError as exc:
        log(str(exc))
        return False
    if 200 <= status < 300:
        log(f"EcomAI chaos API 成功: {method} {url} -> {status}")
        if body:
            log(f"响应: {body}")
        return True
    log(f"EcomAI chaos API 非 2xx: {method} {url} -> {status} body={body}")
    return False


def resolve_ecom_env_file(config: ScriptConfig) -> Path | None:
    if config.ecom_api_repo_path:
        candidate = config.ecom_api_repo_path / "ecom-api" / ".env"
        if candidate.is_file():
            return candidate
    return None


def patch_env_value(env_path: Path, key: str, value: str) -> str | None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    old_value: str | None = None
    found = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            old_value = line.split("=", 1)[1]
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return old_value


def restore_env_value(env_path: Path, key: str, old_value: str | None) -> None:
    if old_value is None:
        lines = [line for line in env_path.read_text(encoding="utf-8").splitlines() if not line.startswith(f"{key}=")]
        env_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return
    patch_env_value(env_path, key, old_value)


def wait_with_countdown(seconds: int, label: str) -> None:
    log(f"{label}，持续 {seconds}s …")
    for remaining in range(seconds, 0, -1):
        if remaining % 10 == 0 or remaining <= 5:
            log(f"剩余 {remaining}s")
        time.sleep(1)


def verify_portal_chaos_returns_5xx(portal_url: str, *, attempts: int = 5) -> bool:
    """确认 Portal 进程已读到共享 chaos flag（Admin/Portal 为独立进程）。"""
    for attempt in range(1, attempts + 1):
        try:
            status, _ = http_json("GET", portal_url, timeout=5.0)
        except RuntimeError as exc:
            log(str(exc))
            return False
        if status == 500:
            log(f"Portal chaos 已生效: GET {portal_url} -> 500")
            return True
        log(f"Portal 仍返回 {status}（第 {attempt}/{attempts} 次），Admin flag 可能未同步到 Portal")
        time.sleep(1)
    log("Portal 未返回 5xx：请重启 EcomAI Admin 与 Portal 后重试 inject_portal_500.py")
    return False


def portal_chaos_still_injecting(portal_url: str) -> bool:
    """Portal /chaos/error 仍返回 500 表示 chaos flag 仍开启。"""
    try:
        status, _ = http_json("GET", portal_url, timeout=5.0)
    except RuntimeError:
        return True
    return status == 500


def hammer_http(
    url: str,
    *,
    workers: int,
    duration: int,
    headers: dict[str, str] | None = None,
    label: str | None = None,
    should_continue: Callable[[], bool] | None = None,
) -> None:
    """Concurrent GET traffic until duration elapses (metrics need sustained load)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    display = label or url
    log(f"高频请求 {display} workers={workers} duration={duration}s")
    base_headers = {"Accept": "application/json"}
    if headers:
        base_headers.update(headers)

    def one_request(worker_id: int) -> None:
        request = Request(url, headers={**base_headers, "X-Chaos-Worker": str(worker_id)}, method="GET")
        try:
            with urlopen(request, timeout=30) as response:
                response.read()
        except HTTPError:
            pass
        except URLError:
            pass

    deadline = time.time() + duration
    round_no = 0
    while time.time() < deadline:
        if should_continue is not None and not should_continue():
            log("检测到 chaos 已关闭（如 Runbook 或 --disable），提前结束压测")
            return
        round_no += 1
        if round_no == 1 or round_no % 5 == 0:
            log(f"压测轮次 #{round_no}，剩余约 {max(0, int(deadline - time.time()))}s")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one_request, i + 1) for i in range(workers)]
            for future in as_completed(futures):
                future.result()
