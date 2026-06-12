# 三大支柱可观测 — 查询示例（架构二期）

> **范围**：Metrics（Prometheus）、Logs（Loki + Promtail）、Traces（Tempo + OTel Collector）。  
> **被监控对象**：EcomAI `ecom-api`（Admin / Portal）。  
> **配置目录**：`observability/`；二进制：`OperationalTools/PrometheusStack/`。

---

## 1. 启动顺序

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\observability\scripts\start-arch-phase2-stack.ps1
```

| 组件 | 地址 | 说明 |
|------|------|------|
| Prometheus | http://127.0.0.1:9090 | 指标存储 + 告警规则 |
| Loki | http://127.0.0.1:3100 | 日志聚合 |
| Tempo | http://127.0.0.1:3200 | 链路存储 |
| OTel Collector | OTLP `:4317` / `:4318` | SDK 统一入口 |
| Promtail | http://127.0.0.1:9080 | 采集 `ecom-api/logs/*.log` |
| Grafana | http://127.0.0.1:3000 | 三数据源联动 |

**EcomAI 启用 OTLP**（可选，与 `/metrics` 并存）：

```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
```

---

## 2. Metrics — PromQL 示例

在 Prometheus **Graph** 或 Grafana **Explore → Prometheus** 执行：

```promql
# Admin / Portal HTTP QPS（instrumentator）
sum(rate(http_requests_total{job=~"ecom-api-.*"}[5m])) by (job)

# 5xx 错误率
sum(rate(http_requests_total{job=~"ecom-api-.*", status=~"5.."}[5m])) by (job)
/
sum(rate(http_requests_total{job=~"ecom-api-.*"}[5m])) by (job)

# OTel Collector 暴露的 SDK 指标（启用 OTEL_ENABLED 后）
up{job="otel-collector"}

# P95 延迟（若 histogram 存在）
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{job="ecom-api-portal"}[5m])) by (le)
)
```

**HTTP API**（阶段三 `metrics_tool.py` 将封装）：

```http
GET http://127.0.0.1:9090/api/v1/query?query=up{job="ecom-api-admin"}
```

---

## 3. Logs — LogQL 示例

Grafana **Explore → Loki**，或 Loki API：

```logql
# 按服务过滤
{service="ecom-api-portal"}

# 含 error 的日志行
{job="ecom-api"} |= "error" | json

# 某 request_id（与 access log / JSON log 字段对齐）
{service="ecom-api-admin"} | json | request_id="abc-123"

# 速率
sum(rate({job="ecom-api"}[5m])) by (service)
```

**数据来源**：

1. **Promtail**：`ecom-api/logs/admin.log`、`portal.log`（`LOG_FILE_ENABLED=true`）  
2. **OTLP logs**：`OTEL_ENABLED=true` 时经 Collector → Loki

**HTTP API**：

```http
GET http://127.0.0.1:3100/loki/api/v1/query_range?query={service="ecom-api-portal"}&limit=50
```

---

## 4. Traces — Trace ID 查链路

### 4.1 获取 trace_id

- Grafana **Explore → Tempo**：Search by service name `ecom-api-portal`  
- 或从日志 JSON 字段 / OTel 注入的 trace context 复制 `trace_id`

### 4.2 Tempo Query API

```http
GET http://127.0.0.1:3200/api/traces/<trace_id>
```

### 4.2b Grafana Search 报 TraceQL 解析错误？

若 Search 页自动生成的查询是：

```traceql
{resource.service.name=ecom-api-portal}
```

会报错 `unknown identifier: ecom`（连字符被当成减号）。请改用 **TraceQL** 页，**给服务名加引号**：

```traceql
{resource.service.name="ecom-api-portal"}
```

或：

```traceql
{resource.service.name="ecom-api-admin"}
```

### 4.3 Grafana 联动

Tempo 数据源已配置 **tracesToLogs → Loki**，在 Trace 详情页可跳转到同一时间窗日志。

---

## 5. 三支柱联合排障（训练营 / RCA 预演）

1. **Prometheus**：确认 `EcomApiDown` / `HighErrorRate` 是否 firing  
2. **Loki**：`{service="ecom-api-portal"} |= "500"` 看异常栈  
3. **Tempo**：按 Portal 服务名搜索慢请求或错误 span  
4. **关联**：日志中的 `trace_id` → Tempo 查完整链路  

---

## 6. 端口与冲突说明

| 端口 | 占用者 |
|------|--------|
| 4317 / 4318 | OTel Collector **入站**（ecom-api SDK） |
| 4319 / 4320 | Tempo **入站**（Collector 转发 traces） |
| 8889 | Collector Prometheus exporter（Prometheus scrape） |

---

## 7. 相关文档

- `observability/README.md` — 启动脚本与验收  
- `docs/ecomai_metrics_integration.md` — instrumentator `/metrics`  
- `docs/ecomai_otel_integration.md` — OTel SDK 开关与依赖  
- `docs/metrics_dictionary.md` — 指标字典  
