#!/usr/bin/env python3
"""
混沌场景 1：MySQL 慢查询（仅 demo / 本地）

1. POST /admin/chaos/mysql-slow
2. 并发 GET /admin/chaos/slow-query?sleep=N（经 ecom-api 计入 P95，触发 HighP95Latency）

直连 MySQL SLEEP 不会进入 HTTP 指标，仅作最后回退。
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

import pymysql

from _config import ScriptConfig
from chaos._common import hammer_http, log, try_chaos_api

DEFAULT_SLOW_PATH = "/admin/chaos/slow-query"


def inject_via_mysql(config: ScriptConfig, *, duration: int, sleep_seconds: int, workers: int) -> None:
    mysql = config.ecom_mysql
    log(
        f"直连 MySQL 注入慢查询: host={mysql.host} db={mysql.database} "
        f"sleep={sleep_seconds}s workers={workers} duration={duration}s"
    )
    log("注意：此模式不会推高 ecom-api HTTP P95，Prometheus 告警通常不会触发")

    def run_sleep_query(worker_id: int) -> None:
        conn = pymysql.connect(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.password,
            database=mysql.database,
            charset="utf8mb4",
            connect_timeout=10,
            read_timeout=sleep_seconds + 30,
            write_timeout=sleep_seconds + 30,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT SLEEP(%s)", (sleep_seconds,))
                cursor.fetchone()
                log(f"worker-{worker_id} 完成一次 SLEEP({sleep_seconds})")
        finally:
            conn.close()

    deadline = time.time() + duration
    round_no = 0
    while time.time() < deadline:
        round_no += 1
        log(f"慢查询轮次 #{round_no}")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_sleep_query, i + 1) for i in range(workers)]
            for future in as_completed(futures):
                future.result()


def main() -> int:
    parser = argparse.ArgumentParser(description="注入 MySQL 慢查询混沌（demo）")
    parser.add_argument("--duration", type=int, default=150, help="注入总时长（秒），建议 >=150")
    parser.add_argument("--sleep-seconds", type=int, default=3, help="每条 SQL SLEEP 秒数")
    parser.add_argument("--workers", type=int, default=4, help="并发慢请求数")
    parser.add_argument("--force-mysql", action="store_true", help="跳过 HTTP 慢查询，直连 MySQL")
    args = parser.parse_args()

    config = ScriptConfig.load()
    slow_url = (
        f"{config.ecom_admin_base_url.rstrip('/')}{DEFAULT_SLOW_PATH}?sleep={args.sleep_seconds}"
    )

    if not args.force_mysql:
        ok = try_chaos_api(
            config,
            path="/admin/chaos/mysql-slow",
            payload={
                "duration_seconds": args.duration,
                "sleep_seconds": args.sleep_seconds,
                "workers": args.workers,
            },
        )
        if not ok:
            log("未命中 EcomAI chaos API，仍尝试 hammer Admin 慢查询路由（需重启 EcomAI Admin）")
        hammer_http(
            slow_url,
            workers=args.workers,
            duration=args.duration,
            label=f"Admin slow-query sleep={args.sleep_seconds}s",
        )
        log("慢查询 HTTP 压测结束。Prometheus 需约 2 分钟后 HighP95Latency 才会 Firing。")
        return 0

    try:
        inject_via_mysql(
            config,
            duration=args.duration,
            sleep_seconds=args.sleep_seconds,
            workers=args.workers,
        )
    except pymysql.MySQLError as exc:
        log(f"MySQL 注入失败: {exc}")
        log("请确认 EcomAI MySQL 可连，或在 ops-api/.env 配置 ECOM_MYSQL_*")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
