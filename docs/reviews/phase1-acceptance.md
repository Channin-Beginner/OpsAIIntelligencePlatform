# 阶段一 1.D 验收报告

> **验收日期**：2026-06-11  
> **契约版本**：`docs/openapi/ops-api.yaml` v0.1.0-phase1  
> **验收结论**：✅ **通过**（MV0 可演示）

---

## 1. 验收范围（对照计划文档 §1.D）

| 验收项 | 操作 | 预期 | 结果 |
|--------|------|------|:----:|
| 契约 | 对照 OpenAPI 逐项勾检 | 无未文档化字段 | ✅ |
| 模拟告警 | Postman / 脚本 POST Webhook | 运维台可见 Incident | ✅ |
| 状态机 | 详情页「开始调查」 | status→investigating；timeline 有记录 | ✅ |
| 去重 | 相同 fingerprint 再 POST | 不新建第二个 Incident | ✅ |

---

## 2. 契约勾检（OpenAPI ↔ 实现）

### 2.1 端点覆盖

| OpenAPI 路径 | 实现 | 认证 | 结果 |
|--------------|------|------|:----:|
| `GET /health` | `app/main.py` | 无 | ✅ |
| `POST /webhooks/alertmanager` | `app/webhooks/alertmanager.py` | 无 | ✅ |
| `POST /api/v1/auth/login` | `app/auth/router.py` | 无 | ✅ |
| `GET /api/v1/alerts` | `app/alerts/router.py` | JWT | ✅ |
| `GET/POST /api/v1/incidents` | `app/incidents/router.py` | JWT | ✅ |
| `GET/PATCH /api/v1/incidents/{id}` | `app/incidents/router.py` | JWT | ✅ |
| `GET/POST /api/v1/incidents/{id}/timeline` | `timeline_router` | JWT | ✅ |
| `GET /api/v1/users` | `app/users/router.py` | JWT (admin) | ✅ |

阶段一增补端点（Auth、Alerts、Users）已在 OpenAPI 中同步定义，无「实现有、契约无」的字段。

### 2.2 响应与枚举

| 检查项 | 结果 |
|--------|:----:|
| CommonResult `{ code, message, data }` | ✅ |
| `severity`: critical / high / medium / low | ✅ |
| `status`: open → acknowledged → investigating → mitigated → resolved → closed | ✅ |
| `IncidentAction` 与 `docs/incident_state_machine.md` 一致 | ✅ |
| `packages/shared` 枚举与 OpenAPI 一致 | ✅ |
| Webhook 响应含 `incident_created`、`incident_id` | ✅ |

### 2.3 前端契约消费

| 页面 | 路由 | 依赖 API | 结果 |
|------|------|----------|:----:|
| 登录 | `/login` | `POST /api/v1/auth/login` | ✅ |
| 告警列表 | `/alerts` | `GET /api/v1/alerts` | ✅ |
| Incident 列表 | `/incidents` | `GET /api/v1/incidents` | ✅ |
| Incident 详情 | `/incidents/:id` | `GET/PATCH` + timeline | ✅ |
| 管理台用户 | `/admin/users` | `GET /api/v1/users` | ✅ |
| 接入配置 | `/admin/integration` | 静态 Webhook URL 说明 | ✅ |

---

## 3. 运行时验收记录

**环境**：MySQL `opsai`、Redis `6379`、ops-api `:8280`

### 3.1 模拟告警（Webhook）

**请求**：

```http
POST http://127.0.0.1:8280/webhooks/alertmanager
Content-Type: application/json
```

```json
{
  "status": "firing",
  "alerts": [{
    "status": "firing",
    "labels": {
      "alertname": "HighErrorRate",
      "service": "ecom-api-portal",
      "severity": "critical"
    },
    "annotations": { "summary": "portal 5xx > 5%" },
    "startsAt": "2025-11-11T10:00:00Z",
    "fingerprint": "demo-fp-001"
  }]
}
```

**首次 POST 响应要点**：

- `incident_created: true`
- `incident_id` 非空
- `alert_event` 入库

**运维台验证**：`GET /api/v1/incidents` 列表可查到对应 `incident_no`、`severity=critical`、`service=ecom-api-portal`。

### 3.2 去重（相同 fingerprint）

**操作**：30 分钟 TTL 内，使用相同 `fingerprint` 再次 POST。

**预期与实测**：

| 指标 | 预期 | 实测 |
|------|------|------|
| `incident_created` | `false` | ✅ `false` |
| 新建 Incident 数 | 0 | ✅ 仍为 1 条开放工单 |
| `incident_id` | 指向已有工单 | ✅ 与首次相同 |
| `alert_event` | 可追加记录 | ✅ 第二条告警入库并归并时间线 |

### 3.3 状态机（开始调查）

**操作**：

```http
PATCH /api/v1/incidents/{id}
Authorization: Bearer <operator JWT>
Content-Type: application/json

{ "action": "start_investigation" }
```

**预期与实测**：

| 指标 | 预期 | 实测 |
|------|------|------|
| `status` | `investigating` | ✅ |
| timeline | 含 `status_change` | ✅ |
| 详情页按钮 | 「开始调查」可用 | ✅（`STATUS_ACTIONS` 映射） |

---

## 4. 自动化回归

```powershell
cd ops-api
..\venv\Scripts\activate
pytest tests/test_phase1_acceptance.py -v
```

覆盖用例：

- `test_health_contract` — 健康检查与 CommonResult
- `test_webhook_creates_incident_and_dedup` — 建单 + Redis 去重
- `test_state_machine_start_investigation` — 状态迁移 + 时间线

---

## 5. 阶段一交付物核对

| 类别 | 产出 | 状态 |
|------|------|:----:|
| 文档 | `docs/architecture_v0.md` | ✅ |
| 文档 | `docs/incident_state_machine.md` | ✅ |
| 文档 | `docs/concepts/observability-vs-incident.md` | ✅ |
| 文档 | `docs/openapi/ops-api.yaml` | ✅ |
| 文档 | `docs/reviews/phase1-openapi.md` | ✅ |
| DDL | `sql/ddl/*.sql` | ✅ |
| 后端 | `ops-api/` Webhook + Incident 状态机 | ✅ |
| 前端 | `ops-ops-web` 告警/Incident 列表与详情 | ✅ |
| 前端 | `ops-admin-web` 用户 + 接入说明 | ✅ |
| 共享 | `packages/shared` 类型与枚举 | ✅ |
| 本地文档 | `README-local.md` | ✅ |

---

## 6. 已知限制（不阻塞阶段二）

| 项 | 说明 |
|----|------|
| RCA / Runbook / KB | 阶段三～五实现 |
| Prometheus 实装 | 阶段二；阶段一用 Postman 模拟 |
| Webhook HMAC 签名校验 | 阶段二前评估 |
| 运维大屏 `/dashboard` | 阶段五 |

---

## 7. 验收决议

1. **阶段一（MV0）验收通过**，可进入 **阶段二：可观测底座 + 传统运维训练营**。  
2. **Git 提醒（请你自行操作）**：合并到 `main`，打 tag `v0.1-phase1`；勿提交 `.env`、`venv/`。  
3. **演示清单（MV0）**：OpenAPI 截图 + Postman 告警 → 运维台 Incident 列表/详情录屏。

---

| 项 | 值 |
|----|-----|
| 验收人 | 项目 Owner |
| 结论 | **通过** |
| 建议 Tag | `v0.1-phase1` |

---

*存档路径：`docs/reviews/phase1-acceptance.md`*
