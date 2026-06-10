# DDL 执行顺序

在 MySQL 8+ 上按序号执行：

```text
00_database.sql
01_sys_user.sql
02_alert_event.sql
03_incident.sql
04_incident_timeline.sql
05_incident_alert_rel.sql
99_seed_users.sql   # 可选，阶段一 1.B 建库后执行
```

PowerShell 示例（按文件逐个 source，或使用 MySQL Workbench 依次运行）。

## ER 关系

```text
sys_user ──< incident (owner_id)
sys_user ──< incident_timeline (actor_id)

alert_event ──< incident_alert_rel >── incident
incident ──< incident_timeline
```

## 与 OpenAPI 对齐

字段命名与 `docs/openapi/ops-api.yaml` 中 `Incident`、`AlertEventSummary`、`TimelineEvent` 一致。
