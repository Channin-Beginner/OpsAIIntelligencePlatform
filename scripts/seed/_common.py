"""Seed data helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pymysql

from _config import MysqlConfig, ScriptConfig, ensure_seed_output_dir


@dataclass(frozen=True)
class PeakDay:
    day: date
    gmv: float
    order_count: int
    source: str


FALLBACK_PEAK_DAYS: list[PeakDay] = [
    PeakDay(date(2025, 6, 18), 1_280_000.0, 4200, "fallback"),
    PeakDay(date(2025, 11, 11), 2_560_000.0, 9100, "fallback"),
    PeakDay(date(2025, 12, 12), 1_980_000.0, 6800, "fallback"),
]


def connect_mysql(cfg: MysqlConfig):
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def write_peak_days_csv(path: Path, peaks: Iterable[PeakDay]) -> None:
    lines = ["day,gmv,order_count,source"]
    for peak in peaks:
        lines.append(f"{peak.day.isoformat()},{peak.gmv:.2f},{peak.order_count},{peak.source}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_peak_days_json(path: Path, peaks: Iterable[PeakDay]) -> None:
    payload = [asdict(peak) for peak in peaks]
    for item in payload:
        item["day"] = item["day"].isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_peak_days(config: ScriptConfig) -> list[PeakDay]:
    json_path = config.seed_output_dir / "peak_days.json"
    if json_path.is_file():
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        return [
            PeakDay(
                day=date.fromisoformat(item["day"]),
                gmv=float(item["gmv"]),
                order_count=int(item["order_count"]),
                source=item.get("source", "file"),
            )
            for item in raw
        ]
    return list(FALLBACK_PEAK_DAYS)


def iter_days(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def is_peak_day(day: date, peaks: set[date]) -> bool:
    return day in peaks
