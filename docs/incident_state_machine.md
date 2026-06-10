# Incident 状态机设计

> **版本**：v0.1（阶段一 1.A）  
> **参考**：Netflix Dispatch Incident 生命周期（简化版）  
> **实现位置**：`ops-api/app/incidents/` + `PATCH /api/v1/incidents/{id}`

---

## 1. 状态枚举

| 状态值 | 中文 | 含义 |
|--------|------|------|
| `open` | 待处理 | 系统或人工创建，尚未确认 |
| `acknowledged` | 已确认 | On-Call 已接单，开始响应 |
| `investigating` | 调查中 | 正在定位根因 |
| `mitigated` | 已缓解 | 影响已止血，待彻底修复 |
| `resolved` | 已解决 | 根因已修复，待关闭 |
| `closed` | 已关闭 | 归档，可触发复盘（阶段五） |

**API 与数据库统一使用小写 snake_case**，与 OpenAPI `IncidentStatus` 枚举一致。

---

## 2. 状态流转图

```text
                    ┌──────────────────────────────────────┐
                    │              open                     │
                    │  （Webhook 自动建单 / 人工 POST）      │
                    └───────────────┬──────────────────────┘
                                    │ acknowledge
                                    ▼
                    ┌──────────────────────────────────────┐
                    │          acknowledged                 │
                    └───────────────┬──────────────────────┘
                                    │ start_investigation
                                    ▼
                    ┌──────────────────────────────────────┐
                    │         investigating                 │
                    └───────────────┬──────────────────────┘
                                    │ mitigate
                                    ▼
                    ┌──────────────────────────────────────┐
                    │           mitigated                   │
                    └───────────────┬──────────────────────┘
                                    │ resolve
                                    ▼
                    ┌──────────────────────────────────────┐
                    │           resolved                    │
                    └───────────────┬──────────────────────┘
                                    │ close
                                    ▼
                    ┌──────────────────────────────────────┐
                    │            closed                     │
                    │         （终态，不可再变更）            │
                    └──────────────────────────────────────┘
```

### 2.1 允许的快捷跳转（初版支持）

为减少运维台点击次数，以下 **跨步跳转** 在业务上合理，初版 API 允许：

| 从 | 到 | 触发动作 | 说明 |
|----|-----|----------|------|
| `open` | `investigating` | `start_investigation` | 跳过 acknowledge，小团队可接受 |
| `open` | `acknowledged` | `acknowledge` | 标准路径 |
| `investigating` | `resolved` | `resolve` | 简单故障可跳过 mitigated |
| `mitigated` | `closed` | `close` | 需先 resolve；若当前为 mitigated，须先 resolve 再 close |
| `resolved` | `investigating` | `reopen_investigation` | 复发或误判，回退调查 |

**不允许**：

- `closed` → 任何状态（终态）
- `open` → `closed`（须至少经过 acknowledge 或 investigating）
- `open` → `resolved` / `mitigated`（跳过调查）

---

## 3. 状态迁移矩阵

行 = 当前状态，列 = 目标状态；`✓` = 允许。

| 当前 ↓ / 目标 → | ack | investigating | mitigated | resolved | closed |
|-----------------|:---:|:-------------:|:---------:|:--------:|:------:|
| **open** | ✓ | ✓ | — | — | — |
| **acknowledged** | — | ✓ | — | — | — |
| **investigating** | — | — | ✓ | ✓ | — |
| **mitigated** | — | — | — | ✓ | — |
| **resolved** | — | ✓* | — | — | ✓ |
| **closed** | — | — | — | — | — |

\* `resolved` → `investigating` 仅通过 `reopen_investigation` 动作。

---

## 4. API 动作与状态映射

`PATCH /api/v1/incidents/{id}` 请求体字段 `action`：

| action | 目标状态 | 前置状态要求 | timeline 事件类型 |
|--------|----------|--------------|-------------------|
| `acknowledge` | `acknowledged` | `open` | `status_change` |
| `start_investigation` | `investigating` | `open`, `acknowledged` | `status_change` |
| `mitigate` | `mitigated` | `investigating` | `status_change` |
| `resolve` | `resolved` | `investigating`, `mitigated` | `status_change` |
| `close` | `closed` | `resolved` | `status_change` |
| `reopen_investigation` | `investigating` | `resolved` | `status_change` |
| `assign` | （不变） | 非 `closed` | `assignment` |
| `update_severity` | （不变） | 非 `closed` | `severity_change` |
| `add_note` | （不变） | 任意 | `note` |

同时支持 `PATCH` 直接设置 `owner_id`（通过 `assign` 动作或独立字段，以实现为准，OpenAPI 已定义 `action` 优先）。

---

## 5. 操作者角色

| 角色 | sys_user.role | 权限 |
|------|---------------|------|
| **系统** | — | Webhook 建单、`open` 初始状态、自动 timeline |
| **运维工程师** | `operator` | acknowledge / investigate / mitigate / resolve / close / assign / note |
| **管理员** | `admin` | 运维全部权限 + 用户管理 + 配置（ops-admin-web） |

阶段一不实现细粒度 RBAC；`operator` 与 `admin` 在 Incident 操作上等价。

---

## 6. 与 Dispatch 的对照

| Dispatch 概念 | OpsAI 初版 | 说明 |
|---------------|------------|------|
| Active / Stable | `open` ~ `investigating` | 进行中 |
| Mitigated | `mitigated` | 影响已控制 |
| Resolved | `resolved` | 修复完成 |
| Closed | `closed` | 归档 |
| Acknowledged | `acknowledged` | 显式接单（Dispatch 隐含在 assign） |
| Commander / Assignee | `owner_id` | 负责人 |
| Timeline events | `incident_timeline` | 审计链 |

Dispatch 原版：`OPEN → INVESTIGATING → MITIGATING → RESOLVED → CLOSED`（大写）。  
OpsAI 增加 `acknowledged` 与 `mitigated` 细分，更贴近国内 On-Call 习惯。

---

## 7. 自动建单规则（Alert → Incident）

由 `app/alerts/service.py` 在 Webhook 入库后执行：

| 条件 | 行为 |
|------|------|
| 新 `fingerprint`（Redis 无去重键） | 创建 `incident`，`status=open`，timeline「系统自动建单」 |
| `severity=critical` 且 fingerprint 已存在但无开放 Incident | 创建新 Incident |
| 相同 fingerprint 且已有 `status` ∉ `{resolved, closed}` 的 Incident | **归并**：写 `incident_alert_rel`，不新建 |
| 相同 fingerprint 在 Redis TTL（30min）内重复 firing | 仅更新 `alert_event`，不新建 |

---

## 8. 时间戳字段

| 字段 | 写入时机 |
|------|----------|
| `incident.created_at` | 建单 |
| `incident.acknowledged_at` | → `acknowledged` |
| `incident.resolved_at` | → `resolved` |
| `incident.closed_at` | → `closed` |
| `incident.updated_at` | 任意变更 |

---

## 9. 错误处理

状态机校验失败时 API 返回：

```json
{
  "code": 409,
  "message": "不允许从 closed 迁移到 investigating",
  "data": {
    "current_status": "closed",
    "requested_action": "start_investigation"
  }
}
```

HTTP 状态码：**409 Conflict**。

---

*维护：状态枚举变更须同步修改 OpenAPI、`packages/shared` 枚举与本文档。*
