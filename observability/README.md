# OpsAI 可观测配置

**设计原则**：工具二进制与项目代码分离。

| 类型 | 位置 |
|------|------|
| Prometheus / Alertmanager / Grafana / Loki / Tempo / OTel Collector / Promtail | `D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\` |
| 时序与组件运行时数据 | `...\PrometheusStack\data\` |
| 配置文件、告警规则、Grafana 大盘 | 本目录 `observability/`（随 OpsAI Git 管理） |

修改安装路径或版本目录时，编辑 `observability/paths.ps1`。

## 当前二进制版本（paths.ps1）

| 组件 | 版本目录 |
|------|----------|
| Prometheus | `prometheus-3.11.3.windows-amd64` |
| Alertmanager | `alertmanager-0.32.0.windows-amd64` |
| Grafana | `grafana-12.3.7` |
| OTel Collector | `otelcol-contrib_0.153.0_windows_amd64` |
| Loki | `loki-windows-amd64.exe/` |
| Promtail | `promtail-windows-amd64.exe/` |
| Tempo | `tempo_3.0.2_windows_amd64` |

## 目录结构

```text
observability/
├── paths.ps1
├── prometheus/
├── alertmanager/
├── otel-collector/          # 阶段三 3.A
├── loki/
├── promtail/
├── tempo/
├── grafana/
└── scripts/
    ├── start-prometheus.ps1
    ├── start-alertmanager.ps1
    ├── start-grafana.ps1
    ├── start-otel-collector.ps1
    ├── start-loki.ps1
    ├── start-promtail.ps1
    ├── start-tempo.ps1
    ├── start-observability-stack.ps1      # 架构一期三件套
    └── start-arch-phase2-stack.ps1         # 架构二期全栈
```

## 启动

**架构一期**（Prometheus + Alertmanager + Grafana）：

```powershell
.\observability\scripts\start-observability-stack.ps1
```

**架构二期**（+ Loki + Promtail + Tempo + OTel Collector）：

```powershell
.\observability\scripts\start-arch-phase2-stack.ps1
```

### 前置依赖

1. **ops-api** `http://127.0.0.1:8280`
2. **ecom-api** Admin `8081` / Portal `8085`，`/metrics` 可用
3. （可选）ecom-api `OTEL_ENABLED=true` — 见 `docs/ecomai_otel_integration.md`

### 服务 URL

| 服务 | URL |
|------|-----|
| Prometheus | http://127.0.0.1:9090 |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana | http://127.0.0.1:3000 |
| Loki | http://127.0.0.1:3100 |
| Tempo | http://127.0.0.1:3200 |
| OTel Collector OTLP | `4317` (gRPC) / `4318` (HTTP) |
| Promtail | http://127.0.0.1:9080 |

## 验收检查

### 架构一期

1. Prometheus → **Targets**：`ecom-api-admin`、`ecom-api-portal` = UP  
2. Prometheus → **Alerts**：`EcomApiDown`、`HighErrorRate`、`HighP95Latency`  
3. Grafana → **OpsAI** 文件夹 → **EcomAI ecom-api 可观测大盘**

### 架构二期（3.A）

1. Grafana → **Connections → Data sources**：Prometheus、Loki、Tempo 均可用  
2. Explore → Loki：`{service="ecom-api-portal"}` 有日志  
3. Explore → Tempo：能搜到 `ecom-api-*` 服务（需 `OTEL_ENABLED=true` 且有流量）  
4. Prometheus → **Targets**：`otel-collector` = UP  

## 相关文档

- `docs/observability_three_pillars.md` — PromQL / LogQL / Trace 查询示例  
- `docs/ecomai_otel_integration.md` — EcomAI OTel SDK  
- `docs/metrics_dictionary.md`  
- `docs/ecomai_metrics_integration.md`
