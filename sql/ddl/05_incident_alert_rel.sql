-- 多告警归并到同一 Incident（Keep 归并思路）

USE opsai;

CREATE TABLE IF NOT EXISTS incident_alert_rel (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    incident_id     BIGINT UNSIGNED NOT NULL COMMENT 'incident.id',
    alert_event_id  BIGINT UNSIGNED NOT NULL COMMENT 'alert_event.id',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_incident_alert (incident_id, alert_event_id),
    KEY idx_rel_alert (alert_event_id),
    CONSTRAINT fk_rel_incident
        FOREIGN KEY (incident_id) REFERENCES incident (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rel_alert
        FOREIGN KEY (alert_event_id) REFERENCES alert_event (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='故障-告警关联';
