-- ADS：每日 MTTR（Mean Time To Repair，平均修复时长）
USE opsai;

CREATE TABLE IF NOT EXISTS ads_mttr_daily (
    stat_date           DATE            NOT NULL COMMENT '统计日期（按 resolved_at）',
    incident_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '当日解决 Incident 数',
    mttr_avg_minutes    DECIMAL(10, 2)  NULL COMMENT '平均 MTTR（分钟）',
    mttr_p50_minutes    DECIMAL(10, 2)  NULL COMMENT 'P50 MTTR（分钟）',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ADS 每日 MTTR';
