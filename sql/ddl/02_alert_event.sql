-- 原始告警事件（类比 EcomAI ecom_event_log）
-- 来源：Alertmanager Webhook、阶段一 Postman 模拟

USE opsai;

CREATE TABLE IF NOT EXISTS alert_event (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    fingerprint     VARCHAR(128)    NOT NULL COMMENT '告警指纹，去重与归并键',
    source          VARCHAR(32)     NOT NULL DEFAULT 'alertmanager' COMMENT '来源',
    status          ENUM('firing', 'resolved') NOT NULL COMMENT '告警状态',
    severity        ENUM('critical', 'high', 'medium', 'low') NOT NULL DEFAULT 'medium' COMMENT '严重级别',
    alertname       VARCHAR(128)    NULL COMMENT 'Prometheus alertname label',
    service         VARCHAR(128)    NULL COMMENT '服务标签，如 ecom-api-portal',
    title           VARCHAR(512)    NOT NULL COMMENT '展示标题（通常来自 annotations.summary）',
    summary         TEXT            NULL COMMENT '详细描述',
    labels_json     JSON            NULL COMMENT '原始 labels',
    annotations_json JSON           NULL COMMENT '原始 annotations',
    starts_at       DATETIME(3)     NULL COMMENT '告警开始时间',
    ends_at         DATETIME(3)     NULL COMMENT '告警结束时间',
    received_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'ops-api 接收时间',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_alert_event_fingerprint (fingerprint),
    KEY idx_alert_event_status_severity (status, severity),
    KEY idx_alert_event_service_created (service, created_at),
    KEY idx_alert_event_received (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警事件';
