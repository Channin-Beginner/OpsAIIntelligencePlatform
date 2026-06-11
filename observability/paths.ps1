# OpsAI 可观测栈路径（工具与项目分离）
# 二进制在 OperationalTools；配置与大盘在 OpsAI 仓库 observability/

$Observability = @{
    OpsAiRoot       = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform'
    ToolsRoot       = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack'
    PrometheusExe   = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\prometheus-2.53.0.windows-amd64\prometheus.exe'
    AlertmanagerExe = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\alertmanager-0.27.0.windows-amd64\alertmanager.exe'
    GrafanaExe      = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\grafana-v11.0.0\bin\grafana-server.exe'
    GrafanaHome     = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\grafana-v11.0.0'
    PrometheusConfig = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\prometheus\prometheus.yml'
    AlertmanagerConfig = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\alertmanager\alertmanager.yml'
    PrometheusData  = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\prometheus'
    AlertmanagerData = 'D:\YIBANWENJIANJI\BIANCHENG\OperationalTools\PrometheusStack\data\alertmanager'
    ProvisioningDir = 'D:\YIBANWENJIANJI\BIANCHENG\Project\OpsAIIntelligencePlatform\observability\grafana\provisioning'
}
