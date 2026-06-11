#!/usr/bin/env python3
"""
混沌场景 3：LLM 超时

方式 A（推荐）：调用 EcomAI Admin chaos API 临时降低 LLM 超时阈值
方式 B：修改 EcomAI ecom-api/.env 中 LLM_TIMEOUT，注入结束后自动还原

注入期间可配合对 NL2SQL / 推荐等 Portal 接口施压，拉高 P95。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from _config import ScriptConfig
from chaos._common import (
    log,
    patch_env_value,
    resolve_ecom_env_file,
    restore_env_value,
    try_chaos_api,
    wait_with_countdown,
)


def trigger_nl2sql_load(portal_base: str, duration: int) -> None:
    script = SCRIPTS_ROOT / "chaos" / "inject_traffic_spike.py"
    if not script.is_file():
        log("未找到 inject_traffic_spike.py，跳过联动压测")
        return
    log("联动压测 Portal NL2SQL 相关路由 …")
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--path",
            "/api/v1/nl2sql/query",
            "--duration",
            str(min(duration, 120)),
            "--workers",
            "4",
            "--rps",
            "2",
        ],
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="注入 LLM 超时混沌")
    parser.add_argument("--duration", type=int, default=120, help="混沌持续秒数")
    parser.add_argument("--timeout-seconds", type=int, default=1, help="临时 LLM_TIMEOUT 值")
    parser.add_argument("--with-traffic", action="store_true", help="同时打 Portal 接口")
    parser.add_argument("--force-env", action="store_true", help="跳过 chaos API，直接改 .env")
    args = parser.parse_args()

    config = ScriptConfig.load()
    restored = False
    env_path: Path | None = None
    old_timeout: str | None = None

    if not args.force_env:
        ok = try_chaos_api(
            config,
            path="/admin/chaos/llm-timeout",
            payload={
                "enable": True,
                "timeout_seconds": args.timeout_seconds,
                "duration_seconds": args.duration,
            },
        )
        if ok:
            if args.with_traffic:
                trigger_nl2sql_load(config.ecom_portal_base_url, args.duration)
            wait_with_countdown(args.duration, "LLM 超时混沌进行中")
            try_chaos_api(
                config,
                path="/admin/chaos/llm-timeout",
                payload={"enable": False},
            )
            log("已通过 chaos API 关闭 LLM 超时注入")
            return 0
        log("未命中 EcomAI chaos API，尝试修改 ecom-api/.env")

    env_path = resolve_ecom_env_file(config)
    if env_path is None:
        log("未找到 EcomAI ecom-api/.env。请设置 ECOM_API_REPO_PATH 或手动修改 LLM_TIMEOUT。")
        log("示例：在 EcomAI .env 将 LLM_TIMEOUT=60 改为 LLM_TIMEOUT=1，重启 ecom-api 后压测 NL2SQL。")
        return 1

    old_timeout = patch_env_value(env_path, "LLM_TIMEOUT", str(args.timeout_seconds))
    log(f"已修改 {env_path}: LLM_TIMEOUT={args.timeout_seconds}（原值={old_timeout}）")
    log("请重启 EcomAI ecom-api 使配置生效，本脚本将等待 duration 后自动还原 .env")

    try:
        if args.with_traffic:
            trigger_nl2sql_load(config.ecom_portal_base_url, args.duration)
        wait_with_countdown(args.duration, "等待 LLM 超时混沌窗口")
    finally:
        restore_env_value(env_path, "LLM_TIMEOUT", old_timeout)
        restored = True
        log(f"已还原 {env_path} LLM_TIMEOUT={old_timeout or '(removed)'}")

    if not restored:
        return 1
    log("LLM 超时注入结束。请再次重启 ecom-api 并观察 HighP95Latency。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
