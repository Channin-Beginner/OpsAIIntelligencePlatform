-- 调整 Portal Runbook：先关闭 chaos 再查 status（避免 status 接口异常阻断处置）
USE opsai;

UPDATE runbook
SET steps_json = JSON_ARRAY(
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
)
WHERE title = 'Portal 500 Chaos 清除';
