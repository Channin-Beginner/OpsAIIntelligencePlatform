-- RCA Agent 分析结果（阶段三 3.C.2）
USE opsai;

CREATE TABLE IF NOT EXISTS rca_result (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    incident_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    hypothesis TEXT NULL COMMENT '根因假设',
    confidence DECIMAL(4, 3) NULL COMMENT '0.000 ~ 1.000',
    evidence_json JSON NULL COMMENT '证据链数组 metric|log|trace|kb',
    suggested_runbook_ids JSON NULL COMMENT '推荐 Runbook ID 列表（阶段四联动）',
    suggested_actions JSON NULL COMMENT '建议处置步骤',
    model_name VARCHAR(64) NULL,
    error_message VARCHAR(512) NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    completed_at DATETIME(3) NULL,
    PRIMARY KEY (id),
    KEY idx_rca_result_incident (incident_id),
    KEY idx_rca_result_status (status),
    CONSTRAINT fk_rca_result_incident FOREIGN KEY (incident_id) REFERENCES incident (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RCA 分析结果';
