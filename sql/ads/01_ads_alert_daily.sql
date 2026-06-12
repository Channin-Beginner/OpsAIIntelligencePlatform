-- ADS：每日告警统计（原始 vs 去重）
USE opsai;

CREATE TABLE IF NOT EXISTS ads_alert_daily (
    stat_date           DATE            NOT NULL COMMENT '统计日期',
    raw_count           INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '原始告警条数',
    deduped_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '按 fingerprint 去重条数',
    alertmanager_count  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'Alertmanager 来源',
    grafana_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'Grafana 来源',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ADS 每日告警';
