# RCA Agent 评估报告（阶段三 3.C.6）

> 评估集：`docs/rca_examples.jsonl` + `docs/chaos_scenarios.md` 五场景扩展。  
> 证据类型要求：每条结论须挂 `metric | log | trace | kb`；**至少 3 场景含 trace**。

## 评估方法

| 项 | 说明 |
|----|------|
| 触发方式 | 运维台 Incident 详情 →「运行 RCA」，或 `POST /api/v1/incidents/{id}/rca` |
| 命中标准 | `hypothesis` 与标答语义一致（混沌根因 / 下游超时 / 压测排队等关键词） |
| 证据标准 | 返回 `evidence[]` 含对应类型；trace 场景须 `type=trace` 非空 |
| 验收 KPI | 10 场景标答中 **≥6 命中**（文档 §9 阶段三） |

## 10 场景标答与证据要求

| # | 场景 | 期望根因关键词 | 必备证据类型 | 含 trace |
|---|------|----------------|--------------|:--------:|
| 1 | portal_500 | chaos `/chaos/error`、5xx | metric + log + kb | |
| 2 | slow_mysql | `SLEEP`、慢查询、P95 | metric + log + kb | |
| 3 | llm_timeout | `LLM_TIMEOUT`、NL2SQL 超时 | metric + log + **trace** | ✅ |
| 4 | traffic_spike | QPS 突增、排队 | metric (+ log 可选) | |
| 5 | ads_refresh_fail | ADS 任务失败 | log + kb | |
| 6 | service_down | 进程未启动、`up=0` | metric + log | |
| 7 | portal_500（复跑） | 同 #1，验证 KB 加权 | metric + log + kb | |
| 8 | slow_mysql（高并发） | workers 拉高连接池 | metric + log | |
| 9 | llm_timeout（带流量） | span `nl2sql` 超时 | metric + log + **trace** | ✅ |
| 10 | traffic_spike + slow | 压测叠加慢查询 | metric + log | ✅（可选 trace） |

标答语料见 `docs/rca_examples.jsonl` 前 6 条；场景 7～10 为混沌组合与复跑扩展。

## 实测记录模板

在本地跑通混沌后填写（示例占位，请按你的环境更新「实测」列）：

| # | 场景 | 标答摘要 | 实测 hypothesis | 证据 metric | 证据 log | 证据 trace | 证据 kb | 命中 |
|---|------|----------|-----------------|:-----------:|:--------:|:----------:|:-------:|:----:|
| 1 | portal_500 | chaos 500 路由 | （待填） | | | | | |
| 2 | slow_mysql | SELECT SLEEP | （待填） | | | | | |
| 3 | llm_timeout | LLM 超时 | （待填） | | | ✅ | | |
| 4 | traffic_spike | QPS 突增 | （待填） | | | | | |
| 5 | ads_refresh_fail | ADS 失败 | （待填） | | | | | |
| 6 | service_down | up=0 | （待填） | | | | | |
| 7 | portal_500 复跑 | 同 #1 | （待填） | | | | | |
| 8 | slow_mysql 高并发 | 连接池 | （待填） | | | | | |
| 9 | llm_timeout+traffic | NL2SQL span | （待填） | | | ✅ | | |
| 10 | spike+slow | 复合 | （待填） | | | ✅ | | |

## 本地验证步骤

```powershell
cd D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform
.\venv\Scripts\Activate.ps1

# 1) 应用新 DDL
python ops-api/scripts/init_db.py

# 2) 单元测试（含编排与 Redis 锁）
cd ops-api
python -m pytest tests/test_rca_agent.py tests/test_agent_tools.py -q

# 3) 启动 ops-api，登录运维台，对混沌产生的 Incident 点「运行 RCA」
# 4) 无 DeepSeek Key 时走 rule-based-fallback，仍可验证证据链四类型
```

## 架构说明

- **编排入口**：`ops-api/app/agent/rca/rca_agent.py` → `analyze_incident()`
- **工具层**：`metrics_tool` / `logs_tool` / `traces_tool` / `incident_rag`（3.B）
- **持久化**：`rca_result` 表；`incident.root_cause_preview` 同步摘要
- **并发控制**：Redis `rca:lock:{incident_id}`，TTL 300s
- **反馈闭环**：`incident_feedback` + 时间线 note（采纳/驳回 + 1～5 分）

## 当前实现状态

| 交付物 | 路径 | 状态 |
|--------|------|------|
| 3.C.1 rca_agent | `app/agent/rca/rca_agent.py` | ✅ |
| 3.C.2 DDL | `sql/ddl/07_rca_result.sql` | ✅ |
| 3.C.3 API | `POST/GET .../rca` | ✅ |
| 3.C.4 运维台面板 | `ops-ops-web/.../IncidentDetailView.vue` | ✅ |
| 3.C.5 feedback | `sql/ddl/08_incident_feedback.sql` + API | ✅ |
| 3.C.6 评估文档 | 本文档 | ✅ |

**说明**：全量 10 场景「命中 ≥6」需在 EcomAI + 可观测栈 +（可选）DeepSeek Key 就绪后人工跑混沌填表；无 Key 时 fallback 仍可收集四类型证据供演示。
