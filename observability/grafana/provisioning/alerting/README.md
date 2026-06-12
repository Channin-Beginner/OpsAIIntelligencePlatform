"""Grafana Unified Alerting → ops-api Webhook 配置说明

在 Grafana UI 中配置 Contact Point：
1. Alerting → Contact points → New contact point
2. Integration: Webhook
3. URL: http://127.0.0.1:8280/webhooks/grafana
4. HTTP Method: POST
5. 可选：在 Message 中使用 Alertmanager 兼容 JSON（Grafana 默认 Unified Alerting 载荷已兼容）

Notification policy 中将 Metrics / Loki / Tempo 告警规则路由到该 Contact Point。

对比验证：
- Alertmanager → POST /webhooks/alertmanager （alert_event.source=alertmanager）
- Grafana UA → POST /webhooks/grafana （alert_event.source=grafana）
两者复用同一套 Alert Center 归并与 Incident 建单逻辑。
