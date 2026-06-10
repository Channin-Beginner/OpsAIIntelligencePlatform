-- 故障主表 + 状态机（类比 EcomAI oms_order）
-- 状态枚举与 docs/incident_state_machine.md、OpenAPI IncidentStatus 一致

USE opsai;

CREATE TABLE IF NOT EXISTS incident (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    incident_no         VARCHAR(32)     NOT NULL COMMENT '人类可读编号 INC-YYYYMMDD-NNNN',
    title               VARCHAR(256)    NOT NULL COMMENT '标题',
    description         TEXT            NULL COMMENT '描述',
    status              ENUM(
                            'open',
                            'acknowledged',
                            'investigating',
                            'mitigated',
                            'resolved',
                            'closed'
                        ) NOT NULL DEFAULT 'open' COMMENT '状态机',
    severity            ENUM('critical', 'high', 'medium', 'low') NOT NULL COMMENT '严重级别',
    service             VARCHAR(128)    NULL COMMENT '关联服务',
    owner_id            BIGINT UNSIGNED NULL COMMENT '负责人 sys_user.id',
    primary_fingerprint VARCHAR(128)    NULL COMMENT '首条告警 fingerprint',
    root_cause_preview  VARCHAR(512)    NULL COMMENT '根因摘要（阶段三 RCA）',
    acknowledged_at     DATETIME(3)     NULL,
    resolved_at         DATETIME(3)     NULL,
    closed_at           DATETIME(3)     NULL,
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_incident_no (incident_no),
    KEY idx_incident_status (status),
    KEY idx_incident_severity (severity),
    KEY idx_incident_owner (owner_id),
    KEY idx_incident_service (service),
    KEY idx_incident_fingerprint (primary_fingerprint),
    KEY idx_incident_created (created_at),
    CONSTRAINT fk_incident_owner
        FOREIGN KEY (owner_id) REFERENCES sys_user (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='故障事件';
