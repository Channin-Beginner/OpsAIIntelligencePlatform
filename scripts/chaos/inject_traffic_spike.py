#!/usr/bin/env python3
"""
混沌场景 5：流量突增

使用标准库并发 HTTP 请求模拟压测（无需 hey/locust）。
可选：若本机已安装 hey，加 --use-hey 调用外部二进制。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from _config import ScriptConfig
from chaos._common import log


def run_hey(url: str, *, duration: int, workers: int, rps: int) -> int:
    hey = shutil.which("hey")
    if not hey:
        log("未找到 hey 可执行文件，回退到内置并发请求")
        return 1
    cmd = [
        hey,
        "-z",
        f"{duration}s",
        "-c",
        str(workers),
        "-q",
        str(rps),
        url,
    ]
    log(f"执行: {' '.join(cmd)}")
    return subprocess.call(cmd)


def builtin_spike(url: str, *, duration: int, workers: int, rps: int) -> None:
    interval = 1.0 / max(rps, 1)
    log(f"内置压测 {url} duration={duration}s workers={workers} rps={rps}")

    def worker_loop(worker_id: int, deadline: float) -> None:
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        sent = 0
        while time.time() < deadline:
            try:
                with urlopen(request, timeout=15) as response:
                    response.read()
            except (HTTPError, URLError):
                pass
            sent += 1
            if sent % 20 == 0:
                log(f"worker-{worker_id} 已发送 {sent} 次")
            time.sleep(interval)

    deadline = time.time() + duration
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker_loop, i + 1, deadline) for i in range(workers)]
        for future in as_completed(futures):
            future.result()


def main() -> int:
    parser = argparse.ArgumentParser(description="Portal 流量突增混沌")
    parser.add_argument(
        "--path",
        default="/product/search?keyword=chaos",
        help="Portal 路径（默认 /product/search，勿用不存在的 /api/v1/products）",
    )
    parser.add_argument("--duration", type=int, default=120, help="压测时长（秒）")
    parser.add_argument("--workers", type=int, default=20, help="并发 worker 数")
    parser.add_argument("--rps", type=int, default=10, help="每 worker 约等于请求频率（近似）")
    parser.add_argument("--use-hey", action="store_true", help="优先使用 hey CLI")
    args = parser.parse_args()

    config = ScriptConfig.load()
    url = f"{config.ecom_portal_base_url.rstrip('/')}{args.path}"

    if args.use_hey and run_hey(url, duration=args.duration, workers=args.workers, rps=args.rps) == 0:
        log("hey 压测完成")
        return 0

    builtin_spike(url, duration=args.duration, workers=args.workers, rps=args.rps)
    log("流量突增结束。请观察 Grafana QPS / P95 与 HighP95Latency。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
