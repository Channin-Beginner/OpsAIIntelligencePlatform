# 阶段一 OpenAPI 评审记录

> **契约文件**：`docs/openapi/ops-api.yaml`  
> **版本**：0.1.0-phase1  
> **评审日期**：2026-06-09  
> **评审结论**：✅ **通过**（可进入 1.B 实现阶段）

---

## 1. 评审范围

阶段一 1.A 要求的最小端点集：

| 端点 | 方法 | 状态 |
|------|------|:----:|
| `/health` | GET | ✅ 已定义 |
| `/webhooks/alertmanager` | POST | ✅ 已定义 |
| `/api/v1/incidents` | GET, POST | ✅ 已定义 |
| `/api/v1/incidents/{incident_id}` | GET, PATCH | ✅ 已定义 |
| `/api/v1/incidents/{incident_id}/timeline` | GET, POST | ✅ 已定义 |

---

## 2. Checklist 自查

### 2.1 字段与枚举

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| `severity` 枚举统一 | ✅ | `critical \| high \| medium \| low`，全文件一致 |
| `status` 枚举统一 | ✅ | `open \| acknowledged \| investigating \| mitigated \| resolved \| closed`，小写 snake_case |
| 前后端不会出现 `OPEN` vs `open` | ✅ | 明确禁止大写 Dispatch 风格 |
| `IncidentAction` 与状态机文档一致 | ✅ | 见 `docs/incident_state_machine.md` §4 |
| 列表含 `severity`、`assignee`（owner_name） | ✅ | `IncidentSummary.owner_name` |
| 列表含 `root_cause_preview` | ✅ | 阶段一可为 null，阶段三 RCA 写入 |
| Webhook `fingerprint` 必填 | ✅ | `AlertmanagerAlert.fingerprint` required |
| Alertmanager 官方 JSON 对齐 | ✅ | `status`、`alerts[]`、`labels`、`annotations`、`startsAt`、`fingerprint` |

### 2.2 分页与列表

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 统一分页参数 | ✅ | `page`（默认 1）、`page_size`（默认 20，最大 100） |
| 分页元数据 | ✅ | `PageMeta`: total, total_pages |
| Incident 列表筛选 | ✅ | status, severity, owner_id, service, keyword |

### 2.3 响应格式（CommonResult）

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 成功响应 `{ code, message, data }` | ✅ | 对齐 EcomAI |
| 业务错误码与 HTTP 状态码分离 | ✅ | 409 状态机冲突仍返回 CommonResult body |
| `code: 200` 表示业务成功 | ✅ | HTTP 200/201 配合 body.code |

### 2.4 错误码

| HTTP | 场景 | body.code 示例 |
|------|------|----------------|
| 400 | Webhook/请求体校验失败 | 400 |
| 401 | JWT 无效 | 401 |
| 404 | Incident 不存在 | 404 |
| 409 | 状态机非法迁移 | 409 |

### 2.5 角色视角评审

| 角色 | 问题 | 决议 |
|------|------|------|
| **前端** | 列表要不要 severity、assignee、root_cause_preview？ | ✅ 已纳入 `IncidentSummary` |
| **前端** | 详情页要不要关联告警？ | ✅ `IncidentDetail.related_alerts` |
| **前端** | 详情页要不要时间线预览？ | ✅ `recent_timeline` + 独立 timeline 分页 API |
| **运维** | 状态能否 acknowledge？ | ✅ `action: acknowledge` |
| **运维** | 与 Dispatch 状态是否一致？ | ✅ 简化版 + `acknowledged` 显式态，见状态机文档 |
| **Agent（阶段三）** | `POST /incidents/{id}/rca` 是否含 evidence[]？ | ⏳ 阶段三增补 OpenAPI，本阶段不阻塞 |
| **测试** | Webhook 样例是否可 Postman 直发？ | ✅ yaml 内 `firingCritical` example + 计划文档 JSON |

---

## 3. 与 DDL 一致性

| OpenAPI 字段 | 数据库列 | 一致 |
|--------------|----------|:----:|
| `Incident.id` | `incident.id` | ✅ |
| `incident_no` | `incident.incident_no` | ✅ |
| `status` | `incident.status` ENUM | ✅ |
| `severity` | `incident.severity` ENUM | ✅ |
| `owner_id` | `incident.owner_id` | ✅ |
| `primary_fingerprint` | `incident.primary_fingerprint` | ✅ |
| `root_cause_preview` | `incident.root_cause_preview` | ✅ |
| `AlertmanagerAlert.fingerprint` | `alert_event.fingerprint` | ✅ |
| `TimelineEvent.*` | `incident_timeline.*` | ✅ |

---

## 4. 明确推迟项（不阻塞 1.B）

| 端点 / 能力 | 计划阶段 |
|-------------|----------|
| `GET /api/v1/alerts` 告警列表 | 1.B 实现时可增补 OpenAPI patch |
| `POST /api/v1/auth/login` | 1.B |
| `POST /api/v1/incidents/{id}/rca` | 三 |
| Webhook HMAC 签名校验 | 二前评估 |

---

## 5. 评审决议

1. **接口冻结**：阶段一 1.B～1.C 实现不得擅自修改枚举值与 CommonResult 结构。  
2. **变更流程**：若必须变更，先改 `ops-api.yaml` + 本评审记录 + 状态机/DDL，再改代码。  
3. **下一步**：进入 **1.B** — `ops-api` 骨架、DDL 执行、Webhook 与状态机实现。

---

## 6. 签核

| 项 | 值 |
|----|-----|
| 评审人 | 项目 Owner（自评审 checklist） |
| 结论 | **通过** |
| Tag 建议 | 完成 1.A 后 commit：`docs: phase1 architecture and openapi review` |

---

*存档路径：`docs/reviews/phase1-openapi.md`*
