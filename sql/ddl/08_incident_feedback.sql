-- 工程师对 RCA 的采纳/驳回反馈（阶段三 3.C.5，Feedback Loop 起点）
USE opsai;

CREATE TABLE IF NOT EXISTS incident_feedback (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    incident_id BIGINT UNSIGNED NOT NULL,
    rca_result_id BIGINT UNSIGNED NULL,
    user_id BIGINT UNSIGNED NULL,
    score TINYINT NOT NULL COMMENT '1~5 分',
    verdict ENUM('accept', 'reject') NOT NULL,
    comment VARCHAR(2000) NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_incident_feedback_incident (incident_id),
    KEY idx_incident_feedback_rca (rca_result_id),
    CONSTRAINT fk_incident_feedback_incident FOREIGN KEY (incident_id) REFERENCES incident (id) ON DELETE CASCADE,
    CONSTRAINT fk_incident_feedback_rca FOREIGN KEY (rca_result_id) REFERENCES rca_result (id) ON DELETE SET NULL,
    CONSTRAINT fk_incident_feedback_user FOREIGN KEY (user_id) REFERENCES sys_user (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RCA 工程师反馈';
