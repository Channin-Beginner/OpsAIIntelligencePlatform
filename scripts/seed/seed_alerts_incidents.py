#!/usr/bin/env python3
"""
灌入 2025-06-01～2026-01-01 历史 alert_event + incident + timeline 到 CSV，可选 --apply 写入 opsai。

高峰日告警密度约为平日 3 倍（对齐 §8.2）。
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

import pymysql

from _config import ScriptConfig, ensure_seed_output_dir
from seed._common import PeakDay, connect_mysql, iter_days, load_peak_days

SEED_START = date(2025, 6, 1)
SEED_END = date(2026, 1, 1)

SCENARIOS = [
    {
        "alertname": "HighP95Latency",
        "severity": "high",
        "service": "ecom-api-admin",
        "title": "admin P95 延迟 > 2s（慢 SQL）",
        "chaos": "inject_slow_mysql",
    },
    {
        "alertname": "HighErrorRate",
        "severity": "critical",
        "service": "ecom-api-portal",
        "title": "portal HTTP 5xx 比例 > 5%",
        "chaos": "inject_portal_500",
    },
    {
        "alertname": "HighP95Latency",
        "severity": "high",
        "service": "ecom-api-portal",
        "title": "portal P95 延迟 > 2s（LLM 超时）",
        "chaos": "inject_llm_timeout",
    },
    {
        "alertname": "AdsRefreshFailed",
        "severity": "medium",
        "service": "ecom-api-admin",
        "title": "ADS 日汇总刷新失败",
        "chaos": "inject_ads_refresh_fail",
    },
    {
        "alertname": "HighP95Latency",
        "severity": "high",
        "service": "ecom-api-portal",
        "title": "portal P95 延迟 > 2s（流量突增）",
        "chaos": "inject_traffic_spike",
    },
]

STATUS_FLOW = [
    ("open", "系统自动建单"),
    ("acknowledged", "值班工程师确认告警"),
    ("investigating", "开始调查根因"),
    ("mitigated", "已缓解：回滚/feature flag 关闭"),
    ("resolved", "故障已解决"),
    ("closed", "复盘完成并关单"),
]


@dataclass
class GeneratedAlert:
    fingerprint: str
    source: str
    status: str
    severity: str
    alertname: str
    service: str
    title: str
    summary: str
    starts_at: datetime
    received_at: datetime
    labels_json: str
    annotations_json: str
    chaos_script: str
    day: date


@dataclass
class GeneratedIncident:
    incident_no: str
    title: str
    description: str
    status: str
    severity: str
    service: str
    primary_fingerprint: str
    created_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    chaos_script: str
    day: date


def random_time_on_day(day: date, rng: random.Random) -> datetime:
    hour = rng.randint(9, 22)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    return datetime.combine(day, time(hour, minute, second))


def alerts_per_day(day: date, peak_days: set[date], rng: random.Random) -> int:
    base = rng.randint(1, 3)
    if day in peak_days:
        # 高峰日密度目标 ≥ 平日 3 倍（阶段二 2.D 验收）
        return base * 3 + rng.randint(1, 2)
    return base


def generate_dataset(peaks: list[PeakDay], *, seed: int) -> tuple[list[GeneratedAlert], list[GeneratedIncident], list[dict]]:
    rng = random.Random(seed)
    peak_set = {peak.day for peak in peaks}
    alerts: list[GeneratedAlert] = []
    incidents: list[GeneratedIncident] = []
    timeline_rows: list[dict] = []

    incident_seq = 0
    for day in iter_days(SEED_START, SEED_END):
        count = alerts_per_day(day, peak_set, rng)
        for idx in range(count):
            scenario = SCENARIOS[(day.toordinal() + idx) % len(SCENARIOS)]
            starts_at = random_time_on_day(day, rng)
            received_at = starts_at + timedelta(seconds=rng.randint(5, 90))
            fingerprint = f"seed-{day.strftime('%Y%m%d')}-{scenario['chaos']}-{idx:02d}"

            labels = {
                "alertname": scenario["alertname"],
                "service": scenario["service"],
                "severity": scenario["severity"],
                "chaos_script": scenario["chaos"],
            }
            annotations = {
                "summary": scenario["title"],
                "description": f"造数场景 {scenario['chaos']} @ {day.isoformat()}",
            }

            alert = GeneratedAlert(
                fingerprint=fingerprint,
                source="seed",
                status="firing",
                severity=scenario["severity"],
                alertname=scenario["alertname"],
                service=scenario["service"],
                title=scenario["title"],
                summary=annotations["description"],
                starts_at=starts_at,
                received_at=received_at,
                labels_json=json.dumps(labels, ensure_ascii=False),
                annotations_json=json.dumps(annotations, ensure_ascii=False),
                chaos_script=scenario["chaos"],
                day=day,
            )
            alerts.append(alert)

            if scenario["severity"] not in ("critical", "high"):
                continue

            incident_seq += 1
            incident_no = f"INC-{day.strftime('%Y%m%d')}-{incident_seq:04d}"
            resolved_at = received_at + timedelta(hours=rng.randint(1, 6))
            closed_at = resolved_at + timedelta(hours=rng.randint(2, 24))

            incident = GeneratedIncident(
                incident_no=incident_no,
                title=scenario["title"],
                description=annotations["description"],
                status="closed",
                severity=scenario["severity"],
                service=scenario["service"],
                primary_fingerprint=fingerprint,
                created_at=received_at,
                resolved_at=resolved_at,
                closed_at=closed_at,
                chaos_script=scenario["chaos"],
                day=day,
            )
            incidents.append(incident)

            cursor = received_at
            for status, content in STATUS_FLOW:
                timeline_rows.append(
                    {
                        "incident_no": incident_no,
                        "event_type": "status_change" if status != "open" else "system",
                        "content": content,
                        "actor_type": "system",
                        "created_at": cursor.isoformat(sep=" "),
                        "metadata_json": json.dumps(
                            {"to_status": status, "chaos_script": scenario["chaos"]},
                            ensure_ascii=False,
                        ),
                    }
                )
                cursor += timedelta(minutes=rng.randint(10, 45))

    return alerts, incidents, timeline_rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def apply_to_opsai(config: ScriptConfig, alerts: list[GeneratedAlert], incidents: list[GeneratedIncident], timeline_rows: list[dict]) -> None:
    incident_no_to_id: dict[str, int] = {}
    fingerprint_to_alert_id: dict[str, int] = {}
    with connect_mysql(config.ops_mysql) as conn:
        with conn.cursor() as cursor:
            for alert in alerts:
                cursor.execute(
                    "SELECT id FROM alert_event WHERE fingerprint = %s LIMIT 1",
                    (alert.fingerprint,),
                )
                existing = cursor.fetchone()
                if existing:
                    fingerprint_to_alert_id[alert.fingerprint] = int(existing["id"])
                    continue
                cursor.execute(
                    """
                    INSERT INTO alert_event (
                        fingerprint, source, status, severity, alertname, service,
                        title, summary, labels_json, annotations_json, starts_at, received_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        alert.fingerprint,
                        alert.source,
                        alert.status,
                        alert.severity,
                        alert.alertname,
                        alert.service,
                        alert.title,
                        alert.summary,
                        alert.labels_json,
                        alert.annotations_json,
                        alert.starts_at,
                        alert.received_at,
                    ),
                )
                fingerprint_to_alert_id[alert.fingerprint] = int(cursor.lastrowid)

            for incident in incidents:
                cursor.execute(
                    "SELECT id FROM incident WHERE incident_no = %s LIMIT 1",
                    (incident.incident_no,),
                )
                if cursor.fetchone():
                    continue
                cursor.execute(
                    """
                    INSERT INTO incident (
                        incident_no, title, description, status, severity, service,
                        primary_fingerprint, created_at, resolved_at, closed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        incident.incident_no,
                        incident.title,
                        incident.description,
                        incident.status,
                        incident.severity,
                        incident.service,
                        incident.primary_fingerprint,
                        incident.created_at,
                        incident.resolved_at,
                        incident.closed_at,
                    ),
                )
                cursor.execute("SELECT id FROM incident WHERE incident_no = %s", (incident.incident_no,))
                row = cursor.fetchone()
                if row:
                    incident_no_to_id[incident.incident_no] = int(row["id"])

            for incident in incidents:
                incident_id = incident_no_to_id.get(incident.incident_no)
                alert_id = fingerprint_to_alert_id.get(incident.primary_fingerprint)
                if not incident_id or not alert_id:
                    continue
                cursor.execute(
                    """
                    INSERT IGNORE INTO incident_alert_rel (incident_id, alert_event_id)
                    VALUES (%s, %s)
                    """,
                    (incident_id, alert_id),
                )

            for timeline in timeline_rows:
                incident_id = incident_no_to_id.get(timeline["incident_no"])
                if not incident_id:
                    continue
                cursor.execute(
                    """
                    INSERT INTO incident_timeline (
                        incident_id, event_type, content, actor_type, metadata_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        incident_id,
                        timeline["event_type"],
                        timeline["content"],
                        timeline["actor_type"],
                        timeline["metadata_json"],
                        timeline["created_at"],
                    ),
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="生成并灌入历史告警/故障造数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--apply", action="store_true", help="除写 CSV 外，写入 opsai MySQL")
    args = parser.parse_args()

    config = ScriptConfig.load()
    out_dir = ensure_seed_output_dir(config)
    peaks = load_peak_days(config)

    alerts, incidents, timeline_rows = generate_dataset(peaks, seed=args.seed)

    alert_rows = [
        {
            "fingerprint": a.fingerprint,
            "source": a.source,
            "status": a.status,
            "severity": a.severity,
            "alertname": a.alertname,
            "service": a.service,
            "title": a.title,
            "summary": a.summary,
            "starts_at": a.starts_at.isoformat(sep=" "),
            "received_at": a.received_at.isoformat(sep=" "),
            "labels_json": a.labels_json,
            "annotations_json": a.annotations_json,
            "chaos_script": a.chaos_script,
            "day": a.day.isoformat(),
        }
        for a in alerts
    ]
    incident_rows = [
        {
            "incident_no": i.incident_no,
            "title": i.title,
            "description": i.description,
            "status": i.status,
            "severity": i.severity,
            "service": i.service,
            "primary_fingerprint": i.primary_fingerprint,
            "created_at": i.created_at.isoformat(sep=" "),
            "resolved_at": i.resolved_at.isoformat(sep=" ") if i.resolved_at else "",
            "closed_at": i.closed_at.isoformat(sep=" ") if i.closed_at else "",
            "chaos_script": i.chaos_script,
            "day": i.day.isoformat(),
        }
        for i in incidents
    ]

    alerts_csv = out_dir / "alert_events.csv"
    incidents_csv = out_dir / "incidents.csv"
    timeline_csv = out_dir / "incident_timeline.csv"
    summary_json = out_dir / "seed_summary.json"

    write_csv(
        alerts_csv,
        list(alert_rows[0].keys()) if alert_rows else ["fingerprint"],
        alert_rows,
    )
    write_csv(
        incidents_csv,
        list(incident_rows[0].keys()) if incident_rows else ["incident_no"],
        incident_rows,
    )
    write_csv(
        timeline_csv,
        ["incident_no", "event_type", "content", "actor_type", "created_at", "metadata_json"],
        timeline_rows,
    )

    peak_days = {p.day for p in peaks}
    peak_alert_count = sum(1 for a in alerts if a.day in peak_days)
    normal_days = [d for d in iter_days(SEED_START, SEED_END) if d not in peak_days]
    normal_alert_count = sum(1 for a in alerts if a.day not in peak_days)
    density_ratio = 0.0
    if normal_days and peak_days:
        density_ratio = (peak_alert_count / len(peak_days)) / max(normal_alert_count / len(normal_days), 1)

    summary = {
        "alerts": len(alerts),
        "incidents": len(incidents),
        "timeline_events": len(timeline_rows),
        "peak_day_count": len(peak_days),
        "peak_vs_normal_density_ratio": round(density_ratio, 2),
        "window": {"start": SEED_START.isoformat(), "end": SEED_END.isoformat()},
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[seed] 告警 {len(alerts)} 条，Incident {len(incidents)} 条，时间线 {len(timeline_rows)} 条")
    print(f"[seed] 高峰日密度比（目标≥3）: {density_ratio:.2f}")
    print(f"  - {alerts_csv}")
    print(f"  - {incidents_csv}")
    print(f"  - {timeline_csv}")
    print(f"  - {summary_json}")

    if args.apply:
        apply_to_opsai(config, alerts, incidents, timeline_rows)
        print("[seed] 已写入 opsai 数据库（source=seed）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
