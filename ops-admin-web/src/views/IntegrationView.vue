<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8280'
const webhookUrl = computed(() => `${apiBase}/webhooks/alertmanager`)

const alertmanagerSnippet = `route:
  receiver: opsai-webhook
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 30s
  repeat_interval: 4h

receivers:
  - name: opsai-webhook
    webhook_configs:
      - url: '${webhookUrl.value}'
        send_resolved: true`

const postmanSample = `{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighErrorRate",
        "service": "ecom-api-portal",
        "severity": "critical"
      },
      "annotations": {
        "summary": "portal 5xx > 5%"
      },
      "startsAt": "2025-11-11T10:00:00Z",
      "fingerprint": "demo-fp-001"
    }
  ]
}`

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="12">
      <el-card shadow="never">
        <template #header>Webhook 接入地址</template>
        <p class="desc">Alertmanager 将告警 POST 到以下 URL（阶段二实装后生效）：</p>
        <el-input :model-value="webhookUrl" readonly>
          <template #append>
            <el-button @click="copyText(webhookUrl)">复制</el-button>
          </template>
        </el-input>
        <el-alert
          class="mt-16"
          title="阶段一可用 Postman 直接向该地址发送模拟 JSON 进行验收"
          type="info"
          :closable="false"
          show-icon
        />
      </el-card>
    </el-col>

    <el-col :span="12">
      <el-card shadow="never">
        <template #header>Alertmanager 配置示例</template>
        <p class="desc">将以下内容写入 <code>alertmanager.yml</code> 的 receivers 段：</p>
        <el-input
          :model-value="alertmanagerSnippet"
          type="textarea"
          :rows="12"
          readonly
          class="code-area"
        />
        <el-button class="mt-8" @click="copyText(alertmanagerSnippet)">复制配置</el-button>
      </el-card>
    </el-col>
  </el-row>

  <el-card shadow="never" class="mt-16">
    <template #header>Postman 模拟告警 JSON（阶段一验收）</template>
    <el-input :model-value="postmanSample" type="textarea" :rows="14" readonly class="code-area" />
    <el-button class="mt-8" @click="copyText(postmanSample)">复制 JSON</el-button>
  </el-card>
</template>

<style scoped>
.desc {
  color: #606266;
  font-size: 14px;
  margin: 0 0 12px;
}

.mt-8 {
  margin-top: 8px;
}

.mt-16 {
  margin-top: 16px;
}

.code-area :deep(textarea) {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
}
</style>
