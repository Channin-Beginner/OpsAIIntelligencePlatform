# OpsAI Intelligence Platform — 架构设计 v0

> **版本**：v0.1（阶段一 1.A）  
> **状态**：已冻结（瘦身栈 + Incident 骨架边界）  
> **姊妹项目**：EcomAI Intelligence Platform（监控对象：`ecom-api`）

---

## 1. 一句话定义

**OpsAI Intelligence Platform（运维智脑平台）** 是以 **FastAPI + Vue 3** 三端实现的 **AIOps Incident 闭环系统**：在 **精简版可观测底座** 之上，自研 **Alert Center + Incident Manager + RCA Agent + Runbook + KB**，监控姊妹项目 **EcomAI 的 `ecom-api`**。

---

## 2. 业务价值链

```text
FastAPI 服务（ecom-api）
    ↓
指标埋点（prometheus-fastapi-instrumentator / OTel SDK）
    ↓
Prometheus（指标存储 + PromQL 告警规则）
    ↓
Alertmanager（路由、分组、静默、Webhook 转发）
    ↓
Alert Center（ops-api：去重 / 归并 / 关联 —— 参考 Keep）
    ↓
Incident Manager（ops-api：状态机 / 负责人 / 时间线 —— 参考 Dispatch）
    ↓
RCA Agent（DeepSeek + 证据链）
    ↓
Runbook 执行器（沙箱）
    ↓
Postmortem → Knowledge Base
    ↓
数据沉淀（MySQL opsai + Redis）
```

---

## 3. 系统架构图（技术 + 业务合一）

```text
┌─────────────────────────────────────────────────────────────┐
│  EcomAI ecom-api（被监控 FastAPI 服务）                       │
│  + prometheus-fastapi-instrumentator 暴露 /metrics           │
│  + 应用日志写文件 logs/ecom-api/*.log（训练营手动查看）        │
│  Admin :8081  |  Portal :8085（以 EcomAI .env 为准）            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP scrape（Prometheus Pull）
                            ▼
              ┌─────────────────────────┐
              │  Prometheus :9090      │
              │  时序指标 + 告警规则      │
              └─────────────┬───────────┘
                            │ firing alerts
                            ▼
              ┌─────────────────────────┐
              │  Alertmanager :9093    │
              │  路由 / 分组 / 静默       │
              └─────────────┬───────────┘
                            │ Webhook POST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ops-api（FastAPI :8280，本项目后端）                         │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │ Alert Center    │  │ Incident Manager                 │  │
│  │ 去重/归并/关联   │→ │ 状态机/负责人/时间线/升级         │  │
│  │ （Keep 思路）    │  │ （Dispatch 思路）                 │  │
│  └─────────────────┘  └──────────────┬───────────────────┘  │
│                                      ▼                      │
│  [阶段三+] RCA Agent → Runbook → Postmortem → KB            │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
              MySQL 8（库 opsai）+ Redis :6379
                            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ops-ops-web  │  │ /dashboard   │  │ ops-admin-web│
│ 运维工作台    │  │ 运维大屏      │  │ 管理台        │
│ :8295        │  │ [阶段五]      │  │ :8290        │
└──────────────┘  └──────────────┘  └──────────────┘

旁路（给人看，阶段二必学 —— 不进入 Agent 主链）：
  Prometheus ──→ Grafana :3000（可视化大盘）
  日志文件 ──→ Get-Content -Wait / 文本编辑器
  [可选] Jaeger（分布式链路，阶段三 RCA 引用）
```

---

## 4. 瘦身栈决策（初版采用 vs 明确不采用）

| 类别 | 初版采用 | 明确不采用 | 理由 |
|------|----------|------------|------|
| 指标 | Prometheus + `prometheus-fastapi-instrumentator` | SigNoz、自研时序库 | 够用、学习价值高 |
| 告警 | Alertmanager → ops-api Webhook | 自写告警引擎 | 行业标准 |
| 可视化 | Grafana 1～2 张大盘 | 自研监控 UI 替代 Grafana | 训练营必学 |
| 日志 | 应用写本地文件 + 手动查看 | Loki + Promtail 全栈 | 初版减负，阶段三后可加 |
| 链路 | 可选 Jaeger all-in-one | Tempo + OTel Collector 全家桶 | 初版可省略 |
| 采集 | Prometheus 直接 scrape | OTel Collector | 二期再加 |
| 告警聚合 | **自研 ops-api Alert Center** | Fork / 部署 Keep | 差异化 + 简历叙事 |
| Incident | **自研 ops-api Incident Manager** | Fork / 部署 Dispatch | 同上 |
| LLM | **DeepSeek**（独立 Key） | 与 EcomAI 共用豆包 | 避免限速争抢 |

---

## 5. Keep 与 Dispatch 借鉴边界

### 5.1 借鉴什么（数据模型 + 流程思想）

| 参考项目 | 借鉴内容 | 落在 ops-api |
|----------|----------|--------------|
| **Keep** | 多源告警统一入口、fingerprint 去重、告警归并升级为 Incident | `app/alerts/`、`alert_event` 表、Redis SETNX |
| **Dispatch** | Incident 生命周期、负责人、参与者、审计时间线 | `app/incidents/`、`incident` + `incident_timeline` 表 |

### 5.2 不做什么（明确边界）

| 不做 | 原因 |
|------|------|
| Fork Keep / Dispatch 源码 | 运维复杂、偏离 AIOps Agent 差异化 |
| Fork Prometheus / Grafana / OTel 源码 | 基础设施集成即可 |
| 在 Alertmanager 内做告警归并 | Alertmanager 只做路由转发；归并在 ops-api |
| 初版部署 Keep / Dispatch 服务 | 只参考模型，不自托管 |

### 5.3 模块映射表

| 模块 | 参考 | 目录 | 阶段 |
|------|------|------|:----:|
| Alert Center | Keep | `ops-api/app/alerts/` | 一 |
| Webhook 接入 | Alertmanager 官方格式 | `ops-api/app/webhooks/` | 一 |
| Incident Manager | Dispatch | `ops-api/app/incidents/` | 一 |
| RCA Agent | 自研 | `ops-api/app/agent/rca/` | 三 |
| Runbook Engine | 自研 | `ops-api/app/runbook/` | 四 |
| KB / Postmortem | 自研 | `ops-api/app/kb/` | 五 |

---

## 6. 工程命名与端口（对齐 EcomAI）

| EcomAI | OpsAI | 端口 |
|--------|-------|------|
| `ecom-api` | **`ops-api`** | **8280** |
| `ecom-admin-web` | **`ops-admin-web`** | **8290** |
| `ecom-ops-web` | **`ops-ops-web`** | **8295** |
| — | Prometheus | 9090 |
| — | Alertmanager | 9093 |
| — | Grafana | 3000 |
| — | Redis | 6379 |
| — | MySQL（库 `opsai`） | 3306 |

EcomAI 端口（本机 `.env`）：Admin API **8081**（`ADMIN_PORT`）、Portal API 8085、Web 8090/8095/5173。计划文档默认写 8080，以实际 `.env` 与 `observability/prometheus/prometheus.yml` 为准。

---

## 7. 技术栈

### 7.1 后端（ops-api）

| 项 | 选型 |
|----|------|
| 框架 | FastAPI 0.136+ |
| ORM | SQLAlchemy 2.x |
| 数据库驱动 | PyMySQL |
| 缓存 / 去重 | Redis（fingerprint TTL 30min） |
| 认证 | JWT（python-jose + passlib） |
| HTTP 客户端 | httpx（阶段三调 Prometheus） |
| LLM | DeepSeek API（阶段三启用） |
| 响应格式 | CommonResult：`{ code, message, data }` |

### 7.2 前端（ops-ops-web / ops-admin-web）

Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios + Element Plus + ECharts。

### 7.3 共享包

`packages/shared`：axios 封装、TypeScript 类型、枚举常量（与 OpenAPI 代码生成对齐）。

---

## 8. 数据层概览（阶段一表）

```text
alert_event ──┐
              ├── incident_alert_rel ── incident ── incident_timeline
              │
sys_user ─────┘（owner / timeline actor）
```

| 表 | 用途 | 类比 EcomAI |
|----|------|-------------|
| `alert_event` | 原始告警 | `ecom_event_log` |
| `incident` | 故障主表 + 状态机 | `oms_order` |
| `incident_timeline` | 审计时间线 | 订单操作日志 |
| `incident_alert_rel` | 多告警归并到一个 Incident | — |
| `sys_user` | 运维 / 管理员账号 | 系统用户 |

阶段三～五扩展：`rca_result`、`runbook`、`kb_article` 等（本阶段不建表）。

---

## 9. 阶段一边界（MV0 做什么 / 不做什么）

### 9.1 阶段一必做

- Contract First：`docs/openapi/ops-api.yaml` 评审通过
- DDL 建表 + 种子用户
- `POST /webhooks/alertmanager` 解析 Alertmanager v4 JSON
- Redis fingerprint 去重（30min）
- 新 fingerprint 或 `severity=critical` 自动建 Incident
- Incident CRUD + 状态机 PATCH 校验
- 每次状态变更写 `incident_timeline`
- ops-ops-web：告警列表、Incident 列表与详情（1.C，非 1.A）

### 9.2 阶段一不做

- Prometheus / Grafana 实装（阶段二）
- RCA / Runbook / KB（阶段三～五）
- 真实 EcomAI 联调混沌（阶段二）
- OTel Collector、Loki、Tempo

### 9.3 阶段一验收口径

- Postman 模拟 Webhook → 运维台可见 Incident
- 相同 fingerprint 不重复建单
- 状态机流转 + timeline 有记录
- OpenAPI 与实现字段一致（契约测试）

---

## 10. 安全与配置约定

- 敏感配置仅放 `ops-api/.env`，模板见 `ops-api/.env.example`
- `.env`、`venv/`、`logs/`、`灌注数据/` 不入 Git
- Webhook 端点阶段一可不做签名校验；阶段二前评估 Alertmanager 来源 IP 白名单
- Runbook 执行器（阶段四）仅允许调用本机 demo API，禁止 SSH 生产

---

## 11. 与 EcomAI 的互补叙事

| 维度 | EcomAI | OpsAI |
|------|--------|-------|
| 证明能力 | Data + Web + AI | Agent + 企业工作流 + 运维数据飞轮 |
| 核心数据 | OLTP、埋点、ADS | alert、incident、rca、kb |
| 被监控对象 | — | **ecom-api** |
| LLM | 豆包 | **DeepSeek** |
| 面试一句话 | AI 电商闭环 | AIOps Agent 诊断我自己的电商系统 |

---

## 12. 构建流程（Contract First）

```text
① 需求与五阶段边界（本文档 + 计划文档）
    ↓
② 架构设计 architecture_v0.md（本文件）
    ↓
③ 数据模型 ER + sql/ddl
    ↓
④ OpenAPI 评审通过 → docs/openapi/ops-api.yaml
    ↓
⑤ 并行开发 ops-api + Vue 三端
    ↓
⑥ 联调：Webhook + 混沌 + 训练营
```

**门禁**：步骤 ④ 评审通过前，禁止编写 Vue 业务页面。

---

*文档维护：阶段一 1.A 产出 | 下一版更新时机：阶段二可观测栈接入后补充 metrics 数据流图*
