# OpsAI 本地开发指南

## 端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| ops-api | 8280 | FastAPI 后端 |
| ops-admin-web | 8290 | 管理台 |
| ops-ops-web | 8295 | 运维工作台 |
| MySQL | 3306 | 库名 `opsai` |
| Redis | 6379 | 告警 fingerprint 去重 |
| Prometheus | 9090 | 指标抓取与告警规则（工具见下方） |
| Alertmanager | 9093 | 告警路由 → ops-api Webhook |
| Grafana | 3000 | 可视化大盘 |
| EcomAI ecom-api Admin | 8081 | 被监控服务 + `/metrics`（以 EcomAI `.env` `ADMIN_PORT` 为准） |
| EcomAI ecom-api Portal | 8085 | 被监控服务 + `/metrics` |

> **可观测工具安装路径**（与 OpsAI 仓库分离）：  
> `D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack`  
> 配置与大盘在仓库 `observability/`，详见 `observability/README.md`。

## 启动顺序

### 1. 基础设施

确保 MySQL、Redis 已启动，并执行 DDL：

```bash
# 在 MySQL 中依次执行
sql/ddl/00_database.sql
sql/ddl/01_sys_user.sql
sql/ddl/02_alert_event.sql
sql/ddl/03_incident.sql
sql/ddl/04_incident_timeline.sql
sql/ddl/05_incident_alert_rel.sql
sql/ddl/99_seed_users.sql
```

或使用脚本（若已配置 `.env`）：

```bash
cd ops-api
..\venv\Scripts\python scripts\init_db.py
```

### 2. 后端 ops-api

```bash
cd ops-api
copy .env.example .env
# 编辑 .env 填写 MySQL / Redis / JWT

..\venv\Scripts\activate
pip install -r requirements.txt
python run.py

快键命令：cd ops-api;python run.py
```

验证：`GET http://127.0.0.1:8280/health`

### 3. 运维台 ops-ops-web

```bash
cd ops-ops-web
npm install
npm run dev

快键命令：cd ops-ops-web;npm run dev
```

访问：http://127.0.0.1:8295

### 4. 管理台 ops-admin-web

```bash
cd ops-admin-web
npm install
npm run dev

快键命令：cd ops-admin-web;npm run dev
```

访问：http://127.0.0.1:8290

### 5. 可观测栈

**前置**：EcomAI `ecom-api` 已按 `docs/ecomai_metrics_integration.md` 暴露 `/metrics`。

```powershell
# 确保 ops-api 已在 8280 运行后执行
.\observability\scripts\start-observability-stack.ps1
```

| 控制台 | 地址 |
|--------|------|
| Prometheus Targets | http://127.0.0.1:9090/targets |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana（大盘在 OpsAI 文件夹） | http://127.0.0.1:3000 |

单独启动：

```powershell
.\observability\scripts\start-prometheus.ps1
.\observability\scripts\start-alertmanager.ps1
.\observability\scripts\start-grafana.ps1
```

## 种子账号

| 用户名 | 密码 | 角色 | 可登录 |
|--------|------|------|--------|
| admin | OpsAI@2025 | 管理员 | 运维台 + 管理台 |
| operator | OpsAI@2025 | 运维工程师 | 仅运维台 |

## Postman 模拟告警

**URL**：`POST http://127.0.0.1:8280/webhooks/alertmanager`  
**Headers**：`Content-Type: application/json`  
**Body（raw JSON）**：

```json
{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighErrorRate",
        "service": "ecom-api-portal",
        "severity": "critical"
      },
      "annotations": {
        "summary": "portal 5xx > 5%"
      },
      "startsAt": "2025-11-11T10:00:00Z",
      "fingerprint": "demo-fp-001"
    }
  ]
}
```

**预期**：

1. 响应 `incident_created: true`
2. 运维台「故障列表」出现新 Incident
3. 相同 `fingerprint` 再次 POST → 不新建第二个 Incident
4. 详情页点击「开始调查」→ status 变为 `investigating`，时间线有记录

**自动化回归**（阶段一 1.D 验收通过后可用）：

```bash
cd ops-api
..\venv\Scripts\pytest tests/test_phase1_acceptance.py -v
```

完整验收记录见 `docs/reviews/phase1-acceptance.md`。

## 环境变量

前端通过 `.env.development` 配置 API 地址：

```
VITE_API_BASE=http://127.0.0.1:8280
```

## 混沌工程与造数

**前置**：EcomAI + 可观测栈 + ops-api 均已启动。场景说明见 `docs/chaos_scenarios.md`。

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\venv\Scripts\Activate.ps1

# 混沌注入示例（Portal 5xx → 期望 30s 内自动建 Incident）
.\venv\Scripts\python scripts\chaos\inject_portal_500.py --duration 120

# EcomAI 高峰日联动 + 历史造数
.\venv\Scripts\python scripts\seed\sync_ecom_peak_days.py
.\venv\Scripts\python scripts\seed\seed_alerts_incidents.py
.\venv\Scripts\python scripts\seed\seed_alerts_incidents.py --apply
```

在 `ops-api/.env` 配置 `ECOM_MYSQL_*`、`ECOM_API_REPO_PATH`（可选）后，造数脚本可读取 EcomAI 业务库。  
CSV 输出目录：`灌注数据/`（已 gitignore）。

## 目录说明

```
packages/shared/     # axios 封装、TypeScript 类型、枚举（两端共用）
ops-ops-web/         # 运维工作台：告警列表、Incident 列表与详情
ops-admin-web/       # 管理台：用户列表、Webhook 接入配置说明
observability/       # Prometheus / Alertmanager / Grafana 配置与启动脚本
scripts/chaos/       # 五类故障注入（2.C.1～2.C.4 + ADS）
scripts/seed/        # EcomAI 高峰联动与历史灌数（2.C.6～2.C.7）
docs/chaos_scenarios.md
docs/metrics_dictionary.md
docs/ecomai_metrics_integration.md
```
