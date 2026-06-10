# Observability vs Incident Management — 概念备忘

> **读者**：未来的自己（面试前 5 分钟复习用）  
> **版本**：v0.1（阶段一 1.A）

---

## 1. 为什么容易混？

传统教程常把「监控平台」和「故障平台」画成一张图，但它们在产业链上解决 **不同问题**：

| | Observability（可观测性） | Incident Management（故障管理） |
|---|---------------------------|-----------------------------------|
| **核心问题** | 系统 **怎么了**？ | 团队 **谁来做、做到哪了**？ |
| **典型输出** | 指标曲线、日志行、Trace Span | 工单、负责人、SLA、复盘 |
| **代表组件** | Prometheus、Grafana、OTel | Dispatch、PagerDuty、**OpsAI Incident** |
| **告警之后** | 往往到此为止（学生项目） | **才刚开始** |

**一句话**：Prometheus 告诉你「Portal 5xx 超阈值」；Incident 系统告诉你「张三在查、已缓解、预计 14:00 恢复」。

---

## 2. 传统监控链（只解决「发现问题」）

```text
指标/日志异常
    ↓
Prometheus 发现问题
    ↓
Alertmanager 通知问题
    ↓
工程师收到通知（邮件/钉钉/短信）
    ↓
【学生项目常在此结束】
```

企业还关心：

```text
谁来处理？（Owner）
什么时候处理？（SLA）
处理到哪一步？（Status）
要不要升级？（Escalation）
有没有解决？（Resolution）
有没有复盘？（Postmortem）
```

→ 这是 **Incident Management**，Dispatch 解决的问题。

---

## 3. 告警太多：Alert Aggregation 层

一个故障可能触发几十条告警（CPU 高、内存高、接口超时、MySQL 慢查询…）。

**Keep 的思路**（OpsAI 在 `ops-api` 自研，不部署 Keep）：

```text
多源告警 → 去重（fingerprint）→ 归并（关联）→ 升级为 1 个 Incident
```

**Alertmanager 不做归并**：它只做路由、分组、静默、Webhook 转发。  
**归并在 ops-api 的 Alert Center** 完成。

---

## 4. OpsAI 在产业链上的位置

| 层次 | 解决什么 | 典型组件 | OpsAI 策略 |
|------|----------|----------|------------|
| Observability | 看见系统 | Prometheus、Grafana、OTel SDK | **集成，不 fork** |
| Alerting | 发现问题 | Alertmanager | **集成** |
| Alert Aggregation | 降噪、归并 | Keep 的思路 | **ops-api 自研** |
| Incident Management | 协同、状态机 | Dispatch 的思路 | **ops-api 自研** |
| AIOps Agent | 根因、处置、飞轮 | RCA Agent | **自研** |

---

## 5. 对照表（面试速查）

| 维度 | Observability | Incident |
|------|---------------|----------|
| 数据类型 | 时序指标、日志流、Trace | 工单、时间线、负责人 |
| 存储 | Prometheus TSDB、日志文件 | MySQL `incident` 表 |
| 实时性 | 秒级 scrape | 分钟级人工 + 状态流转 |
| 用户 | SRE 看大盘 | On-Call 走工单 |
| 初版组件 | Prometheus + Grafana（阶段二） | ops-api + ops-ops-web（阶段一） |
| AI 介入点 | 查 PromQL、读日志（阶段三工具） | RCA 写回 Incident、KB 飞轮 |

---

## 6. 数据流：从指标到 Incident（OpsAI 全链路）

```text
ecom-api /metrics
    → Prometheus (PromQL 规则 firing)
    → Alertmanager (Webhook POST)
    → ops-api Alert Center (alert_event + Redis 去重)
    → ops-api Incident Manager (incident + timeline)
    → ops-ops-web 运维台列表/详情
    → [阶段三] RCA Agent 读指标+日志+KB
```

**Grafana 在哪？** 旁路给人 **看曲线**，不写入 Incident 主链；阶段二训练营必学。

---

## 7. 与 EcomAI 的统一产品思路

```text
EcomAI：业务工作流 + 数据飞轮（ecom_event_log → ADS → 推荐/NL2SQL）
OpsAI：运维工作流 + 数据飞轮（alert_event → incident → kb_article → RCA 更准）
```

技术三连：

```text
Data  = 日志 + 指标 + Trace + Incident 数据
Web   = 运维台 + 管理台 + 大屏
AI    = RCA Agent + Runbook 推荐 + 复盘 Agent
```

业务三连：

```text
Observability → Workflow → Data Flywheel
```

---

## 8. 简历该怎么写 / 不该怎么写

**推荐**：

```text
参考 Keep 的 Alert Aggregation 模型
参考 Dispatch 的 Incident 生命周期管理模型
基于 FastAPI + Vue 3 实现 AIOps Incident 闭环平台
```

**不要写**：

```text
参考 Prometheus / Grafana / OpenTelemetry 源码改造
```

它们只是基础设施，不是你的差异化。

---

## 9. 企业建设 AIOps 的真实顺序

```text
监控 → 告警 → Incident → RCA → Runbook → Postmortem → Knowledge Base
```

**不要** 一上来做「运维聊天机器人」—— 先有 **Workflow**，再嵌 Agent。

OpsAI 五阶段即按此顺序：一 Incident 骨架 → 二 可观测+训练营 → 三 RCA → 四 Runbook → 五 KB+大屏。

---

*备忘：若面试被问「你和 Prometheus 什么关系」→ 答：Prometheus 是数据源，Incident 闭环是我们在 ops-api 自研的核心价值。*
