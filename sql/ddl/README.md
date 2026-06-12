# DDL 执行顺序

在 MySQL 8+ 上按序号执行：

```text
00_database.sql
01_sys_user.sql
02_alert_event.sql
03_incident.sql
04_incident_timeline.sql
05_incident_alert_rel.sql
06_kb_article.sql
07_rca_result.sql       # 阶段三 3.C RCA 结果
08_incident_feedback.sql   # 阶段三 3.C 反馈闭环
09_runbook.sql             # 阶段四 Runbook + 执行记录
99_seed_users.sql   # 可选，阶段一 1.B 建库后执行
98_seed_kb_articles.sql   # 可选，阶段三 3.B RAG 示例语料
97_seed_runbooks.sql      # 可选，阶段四 chaos 场景 Runbook
10_kb_source_incident.sql # 阶段五 Postmortem 关联 Incident
```

ADS 聚合表见 `sql/ads/`（阶段五 Data Flywheel 大屏）：

```text
01_ads_alert_daily.sql
02_ads_mttr_daily.sql
03_ads_agent_quality.sql
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
