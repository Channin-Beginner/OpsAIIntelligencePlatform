-- 阶段五：Postmortem 复盘草稿关联 Incident
USE opsai;

ALTER TABLE kb_article
    ADD COLUMN source_incident_id BIGINT UNSIGNED NULL COMMENT 'Postmortem 来源 Incident' AFTER service,
    ADD KEY idx_kb_article_source_incident (source_incident_id);
