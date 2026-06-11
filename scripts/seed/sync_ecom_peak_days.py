#!/usr/bin/env python3
"""
从 EcomAI MySQL 读取业务高峰日（GMV / 订单量 Top N），输出到 灌注数据/。

查询顺序：
  1. ads_order_daily（推荐 ADS 表）
  2. oms_order 按日聚合
  3. 内置 fallback 高峰日（618 / 双11 / 双12）
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

import pymysql

from _config import ScriptConfig, ensure_seed_output_dir
from seed._common import (
    FALLBACK_PEAK_DAYS,
    PeakDay,
    connect_mysql,
    write_peak_days_csv,
    write_peak_days_json,
)


def fetch_from_ads_order_daily(conn, *, top_n: int, start: date, end: date) -> list[PeakDay] | None:
    sql_candidates = [
        """
        SELECT stat_date AS day, gmv, order_count
        FROM ads_order_daily
        WHERE stat_date BETWEEN %s AND %s
        ORDER BY gmv DESC
        LIMIT %s
        """,
        """
        SELECT biz_date AS day, gmv, order_cnt AS order_count
        FROM ads_order_daily
        WHERE biz_date BETWEEN %s AND %s
        ORDER BY gmv DESC
        LIMIT %s
        """,
    ]
    with conn.cursor() as cursor:
        for sql in sql_candidates:
            try:
                cursor.execute(sql, (start.isoformat(), end.isoformat(), top_n))
                rows = cursor.fetchall()
            except pymysql.MySQLError:
                continue
            if not rows:
                continue
            peaks: list[PeakDay] = []
            for row in rows:
                day_value = row.get("day")
                if isinstance(day_value, datetime):
                    day_obj = day_value.date()
                else:
                    day_obj = date.fromisoformat(str(day_value)[:10])
                peaks.append(
                    PeakDay(
                        day=day_obj,
                        gmv=float(row.get("gmv") or 0),
                        order_count=int(row.get("order_count") or 0),
                        source="ads_order_daily",
                    )
                )
            return peaks
    return None


def fetch_from_oms_order(conn, *, top_n: int, start: date, end: date) -> list[PeakDay] | None:
    sql = """
        SELECT DATE(created_at) AS day,
               SUM(pay_amount) AS gmv,
               COUNT(*) AS order_count
        FROM oms_order
        WHERE created_at >= %s AND created_at < DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY DATE(created_at)
        ORDER BY gmv DESC
        LIMIT %s
    """
    with conn.cursor() as cursor:
        try:
            cursor.execute(sql, (start.isoformat(), end.isoformat(), top_n))
            rows = cursor.fetchall()
        except pymysql.MySQLError:
            return None
    if not rows:
        return None
    peaks: list[PeakDay] = []
    for row in rows:
        day_value = row["day"]
        if hasattr(day_value, "isoformat"):
            day_obj = day_value if isinstance(day_value, date) else day_value.date()
        else:
            day_obj = date.fromisoformat(str(day_value)[:10])
        peaks.append(
            PeakDay(
                day=day_obj,
                gmv=float(row.get("gmv") or 0),
                order_count=int(row.get("order_count") or 0),
                source="oms_order",
            )
        )
    return peaks


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 EcomAI 业务高峰日到 灌注数据/")
    parser.add_argument("--start", default="2025-06-01")
    parser.add_argument("--end", default="2026-01-01")
    parser.add_argument("--top-n", type=int, default=12, help="取 GMV Top N 日作为高峰")
    args = parser.parse_args()

    config = ScriptConfig.load()
    out_dir = ensure_seed_output_dir(config)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    peaks: list[PeakDay] | None = None
    try:
        with connect_mysql(config.ecom_mysql) as conn:
            peaks = fetch_from_ads_order_daily(conn, top_n=args.top_n, start=start, end=end)
            if not peaks:
                peaks = fetch_from_oms_order(conn, top_n=args.top_n, start=start, end=end)
    except pymysql.MySQLError as exc:
        print(f"[seed] 无法连接 EcomAI MySQL: {exc}")

    if not peaks:
        peaks = FALLBACK_PEAK_DAYS
        print("[seed] 使用内置 fallback 高峰日（未读到 ads_order_daily / oms_order）")

    csv_path = out_dir / "peak_days.csv"
    json_path = out_dir / "peak_days.json"
    write_peak_days_csv(csv_path, peaks)
    write_peak_days_json(json_path, peaks)

    print(f"[seed] 已写入 {len(peaks)} 个高峰日")
    print(f"  - {csv_path}")
    print(f"  - {json_path}")
    for peak in peaks:
        print(f"  * {peak.day} gmv={peak.gmv:.0f} orders={peak.order_count} ({peak.source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
