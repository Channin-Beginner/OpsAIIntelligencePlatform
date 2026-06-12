-- 知识库文章（阶段三 RAG；阶段五 Postmortem 审核发布）
CREATE TABLE IF NOT EXISTS kb_article (
    id BIGINT NOT NULL AUTO_INCREMENT,
    title VARCHAR(256) NOT NULL,
    summary VARCHAR(512) NULL,
    content TEXT NOT NULL,
    tags_text VARCHAR(512) NULL COMMENT '逗号分隔标签，供关键词检索',
    service VARCHAR(128) NULL,
    status ENUM('draft', 'published') NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_kb_article_service (service),
    KEY idx_kb_article_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
