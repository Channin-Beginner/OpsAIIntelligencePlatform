# EcomAI ecom-api — OpenTelemetry 埋点（架构二期 3.A.0d）

> 在 **EcomAI 仓库** `ecom-api` 中实现；与现有 `prometheus-fastapi-instrumentator` **过渡期并存**。

## 1. 做了什么

| 文件 | 说明 |
|------|------|
| `app/common/telemetry.py` | OTLP traces / metrics / logs → OpsAI Collector |
| `app/admin_app.py` | `setup_telemetry(admin_app, "ecom-api-admin")` |
| `app/portal_app.py` | `setup_telemetry(portal_app, "ecom-api-portal")` |
| `requirements.txt` | OpenTelemetry SDK + FastAPI/Logging instrumentation |
| `.env.example` | `OTEL_ENABLED`、`OTEL_EXPORTER_OTLP_ENDPOINT` |

## 2. 安装依赖（EcomAI venv）

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\EcomAIIntelligencePlatform\ecom-api
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. 启用

在 `ecom-api/.env` 增加（**必须写在 `.env`，不是 `.env.example`**）：

```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
OTEL_METRIC_EXPORT_INTERVAL_MS=15000
```

`telemetry.py` 通过 `app.config.Settings` 读取上述变量。若日志仍出现 `OpenTelemetry disabled`，说明未读到 `.env` 或值为 `false`，需**重启** `python run.py`。

先启动 OpsAI 架构二期栈（含 OTel Collector），再启动 ecom-api。启动后应看到：

```text
INFO ... OpenTelemetry enabled service=ecom-api-portal endpoint=http://127.0.0.1:4318
```

## 4. 验收

1. Collector 窗口无 export 报错  
2. Grafana → Explore → Tempo：TraceQL 用引号，例如 `{resource.service.name="ecom-api-portal"}`；`/health` 被排除不产生 trace，请打业务接口如 `/home/content`  
3. Grafana → Explore → Loki：OTLP 日志或 Promtail 文件日志可见  
4. Prometheus → Targets：`otel-collector` job = UP（:8889）  
5. `/metrics` 仍可用（instrumentator 未移除）

### 常见 Collector 报错

| 现象 | 原因 | 处理 |
|------|------|------|
| `connectex: actively refused` on `:3100` | Loki 未启动或正在重启 | 先 `start-loki.ps1`，等 `http://127.0.0.1:3100/ready` 返回 200 再开 Collector |
| `connectex: actively refused` on `:4319` | Tempo 未启动 | 先 `start-tempo.ps1`，等 `http://127.0.0.1:3200/ready` 返回 200 再开 Collector |
| `503 empty ring` on `/otlp/v1/logs` | Loki 进程已起但 ingester 尚未注册（启动窗口） | 等待 10–30 秒；仍失败则重启 Loki |
| `allow_structured_metadata is disallowed` | Loki 未开启 OTLP structured metadata | `observability/loki/loki-config.yml` 中 `allow_structured_metadata: true` 并重启 Loki |
| 日志 `OpenTelemetry packages missing` | 用了**系统 Python** 而非 EcomAI venv（`where python` 不是 `..\venv\Scripts\python.exe`） | `..\venv\Scripts\Activate.ps1` 后 `pip install -r requirements.txt`，再 `..\venv\Scripts\python.exe run.py` |
| Grafana Tempo 0 series | 上一条导致未导出 trace；或只打了 `/health`（被排除） | 确认启动日志有 `OpenTelemetry enabled`；打 `GET /home/content` |

## 5. OpsAI 侧配置

Collector 配置：`observability/otel-collector/config.yaml`  
一键启动：`observability/scripts/start-arch-phase2-stack.ps1`
