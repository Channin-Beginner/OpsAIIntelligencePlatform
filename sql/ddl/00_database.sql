-- OpsAI Intelligence Platform — 建库脚本
-- 执行前请确认 MySQL 8+ 已启动；与 EcomAI 同实例，库名互不覆盖

CREATE DATABASE IF NOT EXISTS opsai
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE opsai;
