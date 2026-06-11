# EcomAI ecom-api Metrics 接入指南（阶段二 2.A.6）

OpsAI 监控的是 **姊妹项目 EcomAI** 的 `ecom-api`，不是 `ops-api`。  
请在 **EcomAI 仓库** 完成以下改动（单独 PR/commit）。

## 本地端口（与计划文档默认值可能不同）

以 EcomAI `ecom-api/.env` 为准：

| 服务 | 本机端口 | 环境变量 |
|------|----------|----------|
| Admin API | **8081** | `ADMIN_PORT` |
| Portal API | **8085** | `PORTAL_PORT`（若未改则仍为 8085） |

OpsAI 侧 `observability/prometheus/prometheus.yml` 的 scrape `targets` 必须与上述端口一致。

## 1. 安装依赖

在 EcomAI `ecom-api` 的 Python 环境中：

```bash
pip install "prometheus-fastapi-instrumentator>=7.0.0,<8.0.0"
```

> **版本说明**：8.x 会把 Starlette 降到 1.x，与当前 FastAPI 冲突，必须锁在 7.x。

并写入 `requirements.txt`：

```text
prometheus-fastapi-instrumentator>=7.0.0,<8.0.0
```

## 2. 在 FastAPI 应用中暴露 `/metrics`

在 **Admin** 与 **Portal** 的应用入口（或共用的 `create_app()`）中添加：

```python
from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app):
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
```

在 `app = FastAPI(...)` 创建之后调用：

```python
app = FastAPI(...)
setup_metrics(app)
```

## 3. 本地验证

启动 EcomAI 后执行（端口按你的 `.env`）：

```powershell
curl http://127.0.0.1:8081/metrics
curl http://127.0.0.1:8085/metrics
```

应看到 `# HELP http_requests_total` 等 Prometheus 文本格式输出。

## 4. 与 OpsAI Prometheus 联调

1. 启动 ecom-api（本机 Admin **8081** / Portal **8085**）
2. 启动 OpsAI 可观测栈：`observability/scripts/start-observability-stack.ps1`
3. 打开 Prometheus → **Status → Targets**，确认 `ecom-api-admin`、`ecom-api-portal` 为 **UP**
4. 访问几次 EcomAI 接口，在 Grafana 大盘 **EcomAI ecom-api 可观测大盘** 中应看到 QPS 曲线

## 5. 应用日志（训练营用，非 Loki）

在 `ecom-api` 配置日志写入本地文件，例如：

```text
logs/ecom-api/admin.log
logs/ecom-api/portal.log
```

训练营第 3 关使用：

```powershell
Get-Content -Wait logs\ecom-api\portal.log
```

## 6. 完成标准（2.A.6）

- [x] Admin、Portal 均可访问 `/metrics`（依赖 7.x instrumentator）
- [ ] Prometheus Targets 均为 UP（需 Prometheus 使用正确 Admin 端口 **8081**）
- [ ] Grafana 大盘有 QPS / 延迟数据
- [ ] 告警规则在 Prometheus **Alerts** 页可见（pending/firing 状态可解释）
