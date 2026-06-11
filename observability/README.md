# OpsAI 可观测配置（阶段二 2.A）

**设计原则**：工具二进制与项目代码分离。

| 类型 | 位置 |
|------|------|
| Prometheus / Alertmanager / Grafana 可执行文件 | `D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\` |
| 时序与 Alertmanager 运行时数据 | `...\PrometheusStack\data\` |
| 配置文件、告警规则、Grafana 大盘 | 本目录 `observability/`（随 OpsAI Git 管理） |

修改安装路径时，只需编辑 `observability/paths.ps1`。

## 目录结构

```text
observability/
├── paths.ps1                 # 工具与配置路径（本机）
├── prometheus/
│   ├── prometheus.yml
│   └── alerts/ecom-api.yml
├── alertmanager/
│   └── alertmanager.yml
├── grafana/
│   ├── provisioning/       # 自动注册 Prometheus 数据源与大盘
│   └── dashboards/ecom-api.json
└── scripts/
    ├── start-prometheus.ps1
    ├── start-alertmanager.ps1
    ├── start-grafana.ps1
    └── start-observability-stack.ps1   # 一键开三个窗口
```

## 启动前依赖

1. **ops-api** `http://127.0.0.1:8280`（接收 Alertmanager Webhook）
2. **EcomAI ecom-api** Admin `8081` / Portal `8085` 且已暴露 `/metrics`（见 `docs/ecomai_metrics_integration.md`）

## 快速启动

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\observability\scripts\start-observability-stack.ps1
```

| 服务 | URL |
|------|-----|
| Prometheus | http://127.0.0.1:9090 |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana | http://127.0.0.1:3000 |

## 验收检查

1. Prometheus → **Status → Targets**：`ecom-api-admin`、`ecom-api-portal` = UP  
2. Prometheus → **Alerts**：可见 `EcomApiDown`、`HighErrorRate`、`HighP95Latency`  
3. Alertmanager → **Status**：配置无报错  
4. Grafana → 文件夹 **OpsAI** → 大盘 **EcomAI ecom-api 可观测大盘**  
5. 触发 firing 后，ops-ops-web 出现新 Incident（需 ops-api 运行）

## 相关文档

- `docs/metrics_dictionary.md` — 指标与 PromQL 说明  
- `docs/ecomai_metrics_integration.md` — EcomAI 埋点步骤（2.A.6）  
- `README-local.md` — 全栈启动顺序
