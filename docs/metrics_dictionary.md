# EcomAI ecom-api 指标字典（阶段二 2.A.7）

> 指标由 **`prometheus-fastapi-instrumentator`** 暴露在 `/metrics`。  
> 若 EcomAI 尚未完成埋点，见 `docs/ecomai_metrics_integration.md`。

## 抓取目标

| job | 地址 | service 标签 |
|-----|------|----------------|
| `ecom-api-admin` | `http://127.0.0.1:8081/metrics`（EcomAI `.env` `ADMIN_PORT`） | `ecom-api-admin` |
| `ecom-api-portal` | `http://127.0.0.1:8085/metrics` | `ecom-api-portal` |

## 核心指标

| 指标名 | 类型 | 主要标签 | 含义 |
|--------|------|----------|------|
| `http_requests_total` | Counter | `method`, `status`, `handler`, `job` | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | `method`, `handler`, `le`, `job` | 请求耗时分布 |
| `http_request_size_bytes` | Summary | `method`, `handler` | 请求体大小 |
| `http_response_size_bytes` | Summary | `method`, `handler` | 响应体大小 |
| `up` | Gauge | `job`, `service` | Prometheus 抓取是否成功（1=UP） |

## 常用 PromQL

| 场景 | PromQL | 对应告警 |
|------|--------|----------|
| QPS | `sum(rate(http_requests_total{job=~"ecom-api-.*"}[1m])) by (job)` | — |
| 5xx 错误率 | `sum(rate(http_requests_total{job=~"ecom-api-.*",status=~"5.."}[5m])) by (job) / sum(rate(http_requests_total{job=~"ecom-api-.*"}[5m])) by (job)` | `HighErrorRate` |
| P95 延迟 | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job=~"ecom-api-.*"}[5m])) by (le, job))` | `HighP95Latency` |
| 服务存活 | `up{job=~"ecom-api-.*"}` | `EcomApiDown` |

## 告警规则与故障对照

| 告警名 | severity | 可能故障 | 训练营/混沌关联 |
|--------|----------|----------|-----------------|
| `EcomApiDown` | critical | 进程未启动、端口错误、未暴露 `/metrics` | 停掉 ecom-api 可验证 |
| `HighErrorRate` | critical | 接口 5xx 激增 | `inject_portal_500` |
| `HighP95Latency` | warning | 慢 SQL、下游超时、流量突增 | `inject_slow_mysql`、`inject_traffic_spike` |

## 配置文件位置

| 文件 | 路径 |
|------|------|
| Prometheus 主配置 | `observability/prometheus/prometheus.yml` |
| 告警规则 | `observability/prometheus/alerts/ecom-api.yml` |
| Alertmanager | `observability/alertmanager/alertmanager.yml` |
| Grafana 大盘 | `observability/grafana/dashboards/ecom-api.json` |
