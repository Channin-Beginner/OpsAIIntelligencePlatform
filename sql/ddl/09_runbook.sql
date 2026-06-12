-- Runbook 运行手册（阶段四 4.1）
USE opsai;

CREATE TABLE IF NOT EXISTS runbook (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(256) NOT NULL,
    description VARCHAR(1024) NULL,
    steps_json JSON NOT NULL COMMENT '步骤数组：order/title/action_type/action',
    risk_level ENUM('low', 'medium', 'high') NOT NULL DEFAULT 'low',
    service_tags JSON NULL COMMENT '适用服务标签，如 ecom-api-portal',
    alert_names JSON NULL COMMENT '适用告警名，如 HighErrorRate',
    status ENUM('draft', 'published') NOT NULL DEFAULT 'draft',
    created_by BIGINT UNSIGNED NULL,
    updated_by BIGINT UNSIGNED NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_runbook_status (status),
    KEY idx_runbook_risk (risk_level),
    CONSTRAINT fk_runbook_created_by FOREIGN KEY (created_by) REFERENCES sys_user (id) ON DELETE SET NULL,
    CONSTRAINT fk_runbook_updated_by FOREIGN KEY (updated_by) REFERENCES sys_user (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Runbook 运行手册';

-- Runbook 执行记录（阶段四 4.5）
CREATE TABLE IF NOT EXISTS runbook_execution (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    runbook_id BIGINT UNSIGNED NOT NULL,
    incident_id BIGINT UNSIGNED NOT NULL,
    rca_result_id BIGINT UNSIGNED NULL COMMENT '若由 RCA 推荐触发，用于采纳率统计',
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'pending',
    triggered_by BIGINT UNSIGNED NULL,
    step_results_json JSON NULL COMMENT '每步执行结果',
    error_message VARCHAR(512) NULL,
    started_at DATETIME(3) NULL,
    completed_at DATETIME(3) NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_runbook_exec_incident (incident_id),
    KEY idx_runbook_exec_runbook (runbook_id),
    KEY idx_runbook_exec_rca (rca_result_id),
    CONSTRAINT fk_runbook_exec_runbook FOREIGN KEY (runbook_id) REFERENCES runbook (id) ON DELETE RESTRICT,
    CONSTRAINT fk_runbook_exec_incident FOREIGN KEY (incident_id) REFERENCES incident (id) ON DELETE CASCADE,
    CONSTRAINT fk_runbook_exec_rca FOREIGN KEY (rca_result_id) REFERENCES rca_result (id) ON DELETE SET NULL,
    CONSTRAINT fk_runbook_exec_user FOREIGN KEY (triggered_by) REFERENCES sys_user (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Runbook 执行审计';
