-- RCA RAG 示例语料（与 docs/rca_examples.jsonl / 混沌场景对齐）
INSERT INTO kb_article (title, summary, content, tags_text, service, status)
SELECT * FROM (
    SELECT
        'Portal 5xx 激增：chaos 路由未捕获异常' AS title,
        'HighErrorRate 告警时优先检查 /chaos/error 与 feature flag' AS summary,
        '根因多为 Portal 某路由在异常路径下未统一捕获，导致 5xx 计入 http_requests_total。处置：关闭 portal-500 chaos flag，检查 inject_portal_500 是否仍在运行，回滚最近发布。' AS content,
        'portal,5xx,HighErrorRate,chaos' AS tags_text,
        'ecom-api-portal' AS service,
        'published' AS status
    UNION ALL
    SELECT
        'Admin P95 延迟：MySQL 慢查询',
        'HighP95Latency on admin 时查 slow-query 与连接池',
        '常见根因为 SELECT SLEEP 或缺少索引导致慢 SQL。处置：停止 inject_slow_mysql，检查 MySQL 慢查询日志，临时限流 admin chaos API。',
        'admin,latency,mysql,slow-query',
        'ecom-api-admin',
        'published'
    UNION ALL
    SELECT
        'NL2SQL LLM 超时导致 Portal 延迟',
        'LLM_TIMEOUT 过低时 NL2SQL 接口 P95 飙升',
        '根因为 DeepSeek/豆包下游超时，Portal NL2SQL 长时间挂起。处置：恢复 LLM_TIMEOUT，检查 inject_llm_timeout 脚本是否未还原 .env。',
        'portal,llm,timeout,NL2SQL',
        'ecom-api-portal',
        'published'
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM kb_article LIMIT 1);
