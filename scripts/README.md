# scripts/ — 混沌注入与造数（阶段二 2.C）

## 环境

在仓库根目录激活 **OpsAI 独立 venv**，并确保 `ops-api/.env` 已配置：

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\venv\Scripts\Activate.ps1
```

联动 EcomAI 时补充（见 `ops-api/.env.example`）：

- `ECOM_MYSQL_*` — 读 `ads_order_daily` / `oms_order`
- `ECOM_ADMIN_BASE_URL` / `ECOM_PORTAL_BASE_URL`
- `ECOM_API_REPO_PATH` — 指向 EcomAI 仓库根目录（用于改 `.env` 回退模式）

## 混沌脚本

| 脚本 | 场景 |
|------|------|
| `chaos/inject_slow_mysql.py` | MySQL 慢查询 |
| `chaos/inject_portal_500.py` | Portal 5xx |
| `chaos/inject_llm_timeout.py` | LLM 超时 |
| `chaos/inject_ads_refresh_fail.py` | ADS 刷新失败 |
| `chaos/inject_traffic_spike.py` | 流量突增 |

详细步骤与期望告警见 **`docs/chaos_scenarios.md`**。

## 造数脚本

| 脚本 | 说明 |
|------|------|
| `seed/sync_ecom_peak_days.py` | EcomAI 高峰日 → `灌注数据/peak_days.csv` |
| `seed/seed_alerts_incidents.py` | 历史 alert/incident CSV；`--apply` 写入 opsai |

## 典型联调顺序

```powershell
# 可观测栈 + ops-api + ecom-api 均已启动后
.\venv\Scripts\python scripts\chaos\inject_portal_500.py --duration 120
.\venv\Scripts\python scripts\seed\sync_ecom_peak_days.py
.\venv\Scripts\python scripts\seed\seed_alerts_incidents.py --apply
```
