-- 系统用户：运维工程师 + 管理员
-- 对应 OpenAPI JWT 认证（阶段一 1.B 实现登录）

USE opsai;

CREATE TABLE IF NOT EXISTS sys_user (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    username        VARCHAR(64)     NOT NULL COMMENT '登录名',
    password_hash   VARCHAR(255)    NOT NULL COMMENT 'bcrypt 哈希',
    display_name    VARCHAR(128)    NOT NULL COMMENT '显示名',
    role            ENUM('admin', 'operator') NOT NULL DEFAULT 'operator' COMMENT '角色',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_sys_user_username (username),
    KEY idx_sys_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户';
