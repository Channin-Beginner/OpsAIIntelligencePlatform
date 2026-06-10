-- Incident 审计时间线（类比订单操作日志）

USE opsai;

CREATE TABLE IF NOT EXISTS incident_timeline (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    incident_id     BIGINT UNSIGNED NOT NULL COMMENT 'incident.id',
    event_type      ENUM(
                        'status_change',
                        'assignment',
                        'severity_change',
                        'note',
                        'alert_merged',
                        'system'
                    ) NOT NULL COMMENT '事件类型',
    content         TEXT            NOT NULL COMMENT '展示文案',
    actor_type      ENUM('user', 'system') NOT NULL DEFAULT 'system' COMMENT '操作者类型',
    actor_id        BIGINT UNSIGNED NULL COMMENT 'sys_user.id；系统事件为 NULL',
    metadata_json   JSON            NULL COMMENT '扩展：from_status/to_status/alert_id 等',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_timeline_incident_created (incident_id, created_at),
    KEY idx_timeline_event_type (event_type),
    CONSTRAINT fk_timeline_incident
        FOREIGN KEY (incident_id) REFERENCES incident (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_timeline_actor
        FOREIGN KEY (actor_id) REFERENCES sys_user (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='故障时间线';
