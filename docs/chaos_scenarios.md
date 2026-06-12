# 混沌工程场景表（阶段二 2.C.5）

> 五场景与 EcomAI《项目一介绍文档》§14.4 对齐；告警规则见 `observability/prometheus/alerts/ecom-api.yml`。

## 前置条件

1. EcomAI `ecom-api` Admin **8081** / Portal **8085** 已启动并暴露 `/metrics`
2. OpsAI 可观测栈已启动：`observability/scripts/start-observability-stack.ps1`
3. `ops-api` 在 **8280** 运行，Alertmanager Webhook 指向 `/webhooks/alertmanager`
4. `ops-api/.env` 已配置 `MYSQL_*`；联动造数另配 `ECOM_MYSQL_*`（见 `.env.example`）

## 场景总览

| # | 场景 | 脚本 | 注入方式 | 期望 Prometheus 告警 | 期望 ops-api 行为 | 阶段三 RCA 预期 |
|---|------|------|----------|----------------------|-------------------|-----------------|
| 1 | MySQL 慢查询 | `scripts/chaos/inject_slow_mysql.py` | Admin chaos API 或直连 `SELECT SLEEP(n)` | `HighP95Latency`（admin） | 2～5min 内 firing → 建 Incident | 慢 SQL / 连接池耗尽 |
| 2 | Portal 500 | `scripts/chaos/inject_portal_500.py` | Feature flag 或高频打 Portal 路由 | `HighErrorRate`（portal） | ≤30s 建 critical Incident | 某路由未捕获异常 |
| 3 | LLM 超时 | `scripts/chaos/inject_llm_timeout.py` | 降低 `LLM_TIMEOUT` + NL2SQL 压测 | `HighP95Latency`（portal） | warning/high Incident | NL2SQL 下游 LLM 超时 |
| 4 | ADS 刷新失败 | `scripts/chaos/inject_ads_refresh_fail.py` | `ADS_REFRESH_CHAOS` 或 Admin API | 日志 + 造数 `AdsRefreshFailed` | medium 告警（造数/手工） | ADS 任务失败、依赖表未更新 |
| 5 | 流量突增 | `scripts/chaos/inject_traffic_spike.py` | 内置并发 HTTP 或 `hey` | `HighP95Latency`（portal） | warning Incident | QPS 突增导致排队 |

## 各场景操作步骤

### 1. MySQL 慢查询

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\venv\Scripts\python scripts\chaos\inject_slow_mysql.py --duration 150 --sleep-seconds 3 --workers 4
```

**机制**：脚本会并发请求 Admin `GET /admin/chaos/slow-query?sleep=3`（经 ecom-api 计入 HTTP P95）。告警规则使用 **`http_request_duration_highr_seconds`**（高精度分桶），勿用粗分桶 `http_request_duration_seconds`（3s 请求会被算成 ~1s，永远过不了 >2s）。

**观察**：Grafana **Admin** job P95 上升 → 持续 **≥2 分钟** 后 `HighP95Latency` pending/firing → Alertmanager → ops-ops-web 新 Incident。

### 2. Portal 500

```powershell
.\venv\Scripts\python scripts\chaos\inject_portal_500.py --duration 180
# 默认 route=/chaos/error；勿用不存在的 /api/v1/products（只会 404，不会触发 5xx 告警）
```

**机制**：`POST /admin/chaos/portal-500` 开启 flag 后，脚本持续 hammer `GET /chaos/error`（返回 500 且计入 metrics）。Admin 与 Portal 为**独立进程**，flag 写入 `ecom-api/data/chaos_state.json` 共享；更新 EcomAI 代码后需**重启 Admin + Portal**。

**观察**：`http_requests_total{status=~"5.."}` 占比 >5%，**for: 2m** 后 `HighErrorRate` firing。

**排错**：脚本会先探测 `GET /chaos/error` 是否返回 500；若仍是 200，说明 flag 未同步，重启 EcomAI 后再跑。Prometheus 可执行：
`sum(rate(http_requests_total{job="ecom-api-portal",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="ecom-api-portal"}[5m]))`

### 3. LLM 超时

```powershell
.\venv\Scripts\python scripts\chaos\inject_llm_timeout.py --duration 120 --timeout-seconds 1 --with-traffic
```

**说明**：若修改了 EcomAI `.env`，需 **重启 ecom-api**；脚本结束会自动还原 `LLM_TIMEOUT`。

### 4. ADS 刷新失败

```powershell
.\venv\Scripts\python scripts\chaos\inject_ads_refresh_fail.py --duration 300
```

**观察**：EcomAI Admin 日志出现 ADS 任务失败；Prometheus 一期无专用规则时，用造数 `AdsRefreshFailed` 做历史演示。

### 5. 流量突增

```powershell
.\venv\Scripts\python scripts\chaos\inject_traffic_spike.py --duration 120 --workers 20 --rps 10
# 默认 /product/search?keyword=chaos；若要稳定触发 P95>2s 可改用慢查询：
.\venv\Scripts\python scripts\chaos\inject_slow_mysql.py --duration 150 --sleep-seconds 3 --workers 8

## EcomAI Chaos API（已实现）

脚本会 **优先** 调用下列 Admin 接口；Portal 侧配合 `/chaos/error`。**修改 EcomAI 代码后需重启 Admin/Portal 进程**。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/chaos/mysql-slow` | 返回 hammer 提示；实际压测 `GET /admin/chaos/slow-query?sleep=3` |
| GET | `/admin/chaos/slow-query?sleep=3` | 执行 `SELECT SLEEP(3)`，推高 Admin P95 |
| POST | `/admin/chaos/portal-500` | 开启 Portal `/chaos/error` 返回 500 |
| GET | `/chaos/error`（Portal 8085） | chaos 500 路由，计入 5xx 指标 |
| POST | `/admin/chaos/llm-timeout` | 演示 flag；仍建议改 `.env` LLM_TIMEOUT |
| POST | `/admin/chaos/ads-refresh-fail` | 演示 flag |
| GET | `/admin/chaos/status` | 查看 portal-500 是否激活 |

## 阶段二验收对照（2.D）

| 验收项 | 操作 | 通过标准 |
|--------|------|----------|
| Portal 500 自动建单 | 跑场景 2 + 看 ops-ops-web | Grafana 异常 → AM firing → Incident ≤30s |
| 高峰联动造数 | `sync_ecom_peak_days.py` + `seed_alerts_incidents.py` | `seed_summary.json` 中 `peak_vs_normal_density_ratio` ≥ 3 |
| 手动排障 | 训练营 3+4 关 | 不用 AI，能从 Grafana+日志定位注入路由 |

## 运维台「已解决」与 Prometheus Firing 的关系

| 操作 | 影响范围 |
|------|----------|
| 运维台手动「标记解决」 | 仅更新 **Incident 工单** 状态，**不会**关闭 Prometheus/Alertmanager 告警 |
| Prometheus 告警恢复 | 需 **停止混沌**（如 `inject_portal_500.py --disable`）且指标恢复正常并持续 **for: 2m** |
| 关联告警状态 | Alertmanager 发送 `resolved` webhook 后，运维台会展示该 fingerprint **最新** 告警状态 |

```powershell
# 停止 Portal 5xx 混沌（否则 HighErrorRate 会一直 firing）
python scripts/chaos/inject_portal_500.py --disable
```

修改 `observability/prometheus/alerts/ecom-api.yml` 后，Prometheus 约 15s 内自动热加载；也可访问 Status → Rules 确认 `HighP95Latency` 已引用 `http_request_duration_highr_seconds_bucket`。

## 造数脚本

```powershell
# 1) 从 EcomAI 同步高峰日 → 灌注数据/peak_days.csv
.\venv\Scripts\python scripts\seed\sync_ecom_peak_days.py

# 2) 生成 2025-06～2026-01 历史 CSV（可选写入 opsai）
.\venv\Scripts\python scripts\seed\seed_alerts_incidents.py
.\venv\Scripts\python scripts\seed\seed_alerts_incidents.py --apply
```

输出目录：`灌注数据/`（已在 `.gitignore`）。
