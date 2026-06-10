-- 种子用户（阶段一 1.B 执行）
-- 默认密码均为：OpsAI@2025（bcrypt，请在生产环境修改）
-- 生成方式（Python）：
--   from passlib.context import CryptContext
--   CryptContext(schemes=["bcrypt"]).hash("OpsAI@2025")

USE opsai;

INSERT INTO sys_user (username, password_hash, display_name, role)
VALUES
    (
        'admin',
        '$2b$12$f6OEHeG6GJPDqYoD7yIMIuvM781TL2chTvQBOu6/3afwjMGvaVzzi',
        '系统管理员',
        'admin'
    ),
    (
        'operator',
        '$2b$12$f6OEHeG6GJPDqYoD7yIMIuvM781TL2chTvQBOu6/3afwjMGvaVzzi',
        '值班运维',
        'operator'
    )
ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    role = VALUES(role);
