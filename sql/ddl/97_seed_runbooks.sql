-- 阶段四示例 Runbook（与 chaos_scenarios.md 五场景对齐）
USE opsai;

INSERT INTO runbook (title, description, steps_json, risk_level, service_tags, alert_names, status)
SELECT * FROM (
    SELECT
        'Portal 500 Chaos 清除' AS title,
        '关闭 EcomAI Portal chaos 500 注入，恢复 HighErrorRate 指标' AS description,
        JSON_ARRAY(
            JSON_OBJECT(
                'order', 1,
                'title', '关闭 Portal 500 注入',
                'description', 'POST 关闭 portal-500 feature flag',
                'action_type', 'http',
                'action', JSON_OBJECT(
                    'method', 'POST',
                    'path', '/admin/chaos/portal-500',
                    'body', JSON_OBJECT('enable', false)
                )
            ),
            JSON_OBJECT(
                'order', 2,
                'title', '确认 chaos 状态',
                'description', '查看 Admin chaos 状态接口',
                'action_type', 'http',
                'action', JSON_OBJECT(
                    'method', 'GET',
                    'path', '/admin/chaos/status'
                )
            ),
            JSON_OBJECT(
                'order', 3,
                'title', '人工验证',
                'description', '在 Grafana 确认 portal 5xx 率回落；停止 inject_portal_500.py',
                'action_type', 'manual',
                'action', NULL
            )
        ) AS steps_json,
        'low' AS risk_level,
        JSON_ARRAY('ecom-api-portal') AS service_tags,
        JSON_ARRAY('HighErrorRate') AS alert_names,
        'published' AS status
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM runbook WHERE title = 'Portal 500 Chaos 清除');

INSERT INTO runbook (title, description, steps_json, risk_level, service_tags, alert_names, status)
SELECT * FROM (
    SELECT
        'MySQL 慢查询 Chaos 清除' AS title,
        '关闭 Admin slow-query chaos，缓解 HighP95Latency' AS description,
        JSON_ARRAY(
            JSON_OBJECT(
                'order', 1,
                'title', '关闭 MySQL 慢查询注入',
                'description', 'POST 关闭 mysql-slow chaos API',
                'action_type', 'http',
                'action', JSON_OBJECT(
                    'method', 'POST',
                    'path', '/admin/chaos/mysql-slow',
                    'body', JSON_OBJECT('enable', false)
                )
            ),
            JSON_OBJECT(
                'order', 2,
                'title', '停止压测脚本',
                'description', '确认 inject_slow_mysql.py 已停止',
                'action_type', 'manual',
                'action', NULL
            )
        ) AS steps_json,
        'low' AS risk_level,
        JSON_ARRAY('ecom-api-admin') AS service_tags,
        JSON_ARRAY('HighP95Latency') AS alert_names,
        'published' AS status
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM runbook WHERE title = 'MySQL 慢查询 Chaos 清除');

INSERT INTO runbook (title, description, steps_json, risk_level, service_tags, alert_names, status)
SELECT * FROM (
    SELECT
        'LLM 超时 Chaos 清除' AS title,
        '恢复 LLM 超时阈值，关闭 llm-timeout chaos flag' AS description,
        JSON_ARRAY(
            JSON_OBJECT(
                'order', 1,
                'title', '关闭 LLM 超时注入',
                'description', 'POST 关闭 llm-timeout chaos API',
                'action_type', 'http',
                'action', JSON_OBJECT(
                    'method', 'POST',
                    'path', '/admin/chaos/llm-timeout',
                    'body', JSON_OBJECT('enable', false)
                )
            ),
            JSON_OBJECT(
                'order', 2,
                'title', '恢复 .env LLM_TIMEOUT',
                'description', '若曾修改 EcomAI .env，恢复合理超时值',
                'action_type', 'manual',
                'action', NULL
            )
        ) AS steps_json,
        'low' AS risk_level,
        JSON_ARRAY('ecom-api-portal') AS service_tags,
        JSON_ARRAY('HighP95Latency') AS alert_names,
        'published' AS status
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM runbook WHERE title = 'LLM 超时 Chaos 清除');

INSERT INTO runbook (title, description, steps_json, risk_level, service_tags, alert_names, status)
SELECT * FROM (
    SELECT
        'ADS 刷新失败 Chaos 清除' AS title,
        '关闭 ADS 刷新失败演示开关' AS description,
        JSON_ARRAY(
            JSON_OBJECT(
                'order', 1,
                'title', '关闭 ADS 刷新失败注入',
                'description', 'POST 关闭 ads-refresh-fail chaos API',
                'action_type', 'http',
                'action', JSON_OBJECT(
                    'method', 'POST',
                    'path', '/admin/chaos/ads-refresh-fail',
                    'body', JSON_OBJECT('enable', false)
                )
            ),
            JSON_OBJECT(
                'order', 2,
                'title', '手动重跑 ADS 任务',
                'description', '确认 ads_order_daily 源表后重跑刷新',
                'action_type', 'manual',
                'action', NULL
            )
        ) AS steps_json,
        'low' AS risk_level,
        JSON_ARRAY('ecom-api-admin') AS service_tags,
        JSON_ARRAY('AdsRefreshFailed') AS alert_names,
        'published' AS status
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM runbook WHERE title = 'ADS 刷新失败 Chaos 清除');
