#!/usr/bin/env python3
"""
混沌场景 2：Portal 接口 5xx

1. POST /admin/chaos/portal-500 开启 feature flag
2. 高频 GET /chaos/error（计入 Prometheus 5xx，触发 HighErrorRate）

告警规则 for: 2m，建议 duration >= 150s。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from _config import ScriptConfig
from chaos._common import (
    hammer_http,
    log,
    portal_chaos_still_injecting,
    try_chaos_api,
    verify_portal_chaos_returns_5xx,
)

DEFAULT_CHAOS_ROUTE = "/chaos/error"


def main() -> int:
    parser = argparse.ArgumentParser(description="注入 Portal 5xx 混沌")
    parser.add_argument("--duration", type=int, default=180, help="注入时长（秒），建议 >=150 以越过 for:2m")
    parser.add_argument("--route", default=DEFAULT_CHAOS_ROUTE, help="Portal 混沌路由（默认 /chaos/error）")
    parser.add_argument("--workers", type=int, default=8, help="并发请求数")
    parser.add_argument("--disable", action="store_true", help="关闭 portal-500 混沌")
    parser.add_argument("--force-hammer", action="store_true", help="跳过 chaos API，直接打流量（需已手动开启）")
    args = parser.parse_args()

    config = ScriptConfig.load()
    portal_url = f"{config.ecom_portal_base_url.rstrip('/')}{args.route}"
    enable = not args.disable

    if not args.force_hammer:
        ok = try_chaos_api(
            config,
            path="/admin/chaos/portal-500",
            payload={"enable": enable, "route": args.route, "duration_seconds": args.duration},
        )
        if not ok:
            log("未命中 EcomAI chaos API（需重启 EcomAI Admin 加载 /admin/chaos/*）")
            if args.disable:
                return 1
            log("回退：直接 hammer Portal（若无 flag 则不会 5xx）")
        elif args.disable:
            return 0
        if enable and not verify_portal_chaos_returns_5xx(portal_url):
            return 1

    if args.disable:
        log("--disable 仅对 chaos API 有效")
        return 0

    hammer_http(
        portal_url,
        workers=args.workers,
        duration=args.duration,
        should_continue=lambda: portal_chaos_still_injecting(portal_url),
    )

    if not args.force_hammer:
        try_chaos_api(
            config,
            path="/admin/chaos/portal-500",
            payload={"enable": False, "route": args.route},
        )

    log("Portal 5xx 压测结束。Prometheus 需约 2 分钟后 HighErrorRate 才会 Firing。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
