-- ADS：Agent 质量与 Runbook 成功率
USE opsai;

CREATE TABLE IF NOT EXISTS ads_agent_quality (
    stat_date               DATE            NOT NULL COMMENT '统计日期',
    rca_total               INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'RCA 完成次数',
    rca_accept_count        INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'RCA 采纳反馈数',
    rca_accept_rate         DECIMAL(6, 4)   NULL COMMENT 'RCA 采纳率',
    runbook_exec_total      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'Runbook 执行次数',
    runbook_exec_success    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'Runbook 成功次数',
    runbook_success_rate    DECIMAL(6, 4)   NULL COMMENT 'Runbook 成功率',
    kb_published_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '当日发布 KB 数',
    open_incident_count     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '当日末开放 Incident 快照',
    created_at              DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ADS Agent 质量';
