# OpsAI 可观测栈路径（工具与项目分离）
# 二进制在 OperationalTools；配置与大盘在 OpsAI 仓库 observability/

$Observability = @{
    OpsAiRoot            = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform'
    EcomAiRoot           = 'D:\YIBANWENJIANJI\BIANCHENG\Project\EcomAIIntelligencePlatform'
    ToolsRoot            = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack'

    PrometheusExe        = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\prometheus-3.11.3.windows-amd64\prometheus.exe'
    PromtoolExe          = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\prometheus-3.11.3.windows-amd64\promtool.exe'
    AlertmanagerExe      = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\alertmanager-0.32.0.windows-amd64\alertmanager.exe'
    GrafanaExe           = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\grafana-12.3.7\bin\grafana-server.exe'
    GrafanaHome          = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\grafana-12.3.7'
    OtelCollectorExe     = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\otelcol-contrib_0.153.0_windows_amd64\otelcol-contrib.exe'
    LokiExe              = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\loki-windows-amd64.exe\loki-windows-amd64.exe'
    PromtailExe          = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\promtail-windows-amd64.exe\promtail-windows-amd64.exe'
    TempoExe             = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\tempo_3.0.2_windows_amd64\tempo.exe'

    PrometheusConfig     = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\prometheus\prometheus.yml'
    AlertmanagerConfig   = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\alertmanager\alertmanager.yml'
    OtelCollectorConfig  = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\otel-collector\config.yaml'
    LokiConfig           = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\loki\loki-config.yml'
    PromtailConfig       = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\promtail\promtail-config.yml'
    TempoConfig          = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\tempo\tempo-config.yml'
    ProvisioningDir      = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\grafana\provisioning'

    PrometheusData       = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\prometheus'
    AlertmanagerData     = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\alertmanager'
    LokiData             = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\loki'
    TempoData            = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\tempo'
    PromtailData         = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\promtail'
    EcomApiLogDir        = 'D:\YIBANWENJIANJI\BIANCHENG\Project\EcomAIIntelligencePlatform\ecom-api\logs'
}
