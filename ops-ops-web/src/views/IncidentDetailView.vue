<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  INCIDENT_STATUS_LABELS,
  SEVERITY_LABELS,
  STATUS_ACTIONS,
  type IncidentAction,
  type IncidentDetail,
  type TimelineEvent,
} from '@opsai/shared'
import { getIncident, listTimeline, patchIncident } from '@/api/incidents'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const actionLoading = ref(false)
const incident = ref<IncidentDetail | null>(null)
const timeline = ref<TimelineEvent[]>([])

const incidentId = computed(() => Number(route.params.id))

const availableActions = computed(() => {
  if (!incident.value) return []
  return STATUS_ACTIONS[incident.value.status] || []
})

function severityTagType(severity: string) {
  const map: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: '',
    low: 'info',
  }
  return map[severity] || 'info'
}

async function fetchDetail() {
  loading.value = true
  try {
    const [detail, timelineData] = await Promise.all([
      getIncident(incidentId.value),
      listTimeline(incidentId.value),
    ])
    incident.value = detail
    timeline.value = timelineData.items
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载详情失败')
    router.push('/incidents')
  } finally {
    loading.value = false
  }
}

async function runAction(action: IncidentAction, label: string) {
  try {
    let note: string | undefined
    if (action === 'add_note') {
      const { value } = await ElMessageBox.prompt('请输入备注', '添加备注', {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
      })
      note = value
    }
    actionLoading.value = true
    await patchIncident(incidentId.value, { action, note })
    ElMessage.success(`已执行：${label}`)
    await fetchDetail()
  } catch (e) {
    if (e === 'cancel') return
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function addNote() {
  await runAction('add_note' as IncidentAction, '添加备注')
}

onMounted(fetchDetail)
</script>

<template>
  <div v-loading="loading">
    <el-page-header class="page-header" @back="router.push('/incidents')">
      <template #content>
        <span v-if="incident">{{ incident.incident_no }} · {{ incident.title }}</span>
      </template>
    </el-page-header>

    <el-row v-if="incident" :gutter="16" class="detail-row">
      <el-col :span="16">
        <el-card shadow="never" class="section-card">
          <template #header>基本信息</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="状态">
              <el-tag size="small">
                {{ INCIDENT_STATUS_LABELS[incident.status] || incident.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="严重级别">
              <el-tag :type="severityTagType(incident.severity)" size="small">
                {{ SEVERITY_LABELS[incident.severity] || incident.severity }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="负责人">
              {{ incident.owner_name || '未指派' }}
            </el-descriptions-item>
            <el-descriptions-item label="服务">{{ incident.service || '—' }}</el-descriptions-item>
            <el-descriptions-item label="Fingerprint" :span="2">
              {{ incident.primary_fingerprint || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ incident.description || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ incident.created_at }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ incident.updated_at }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="availableActions.length" class="action-bar">
            <span class="action-label">状态操作：</span>
            <el-button
              v-for="item in availableActions"
              :key="item.action"
              type="primary"
              :loading="actionLoading"
              @click="runAction(item.action, item.label)"
            >
              {{ item.label }}
            </el-button>
            <el-button :loading="actionLoading" @click="addNote">添加备注</el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="section-card">
          <template #header>关联告警 ({{ incident.related_alerts.length }})</template>
          <el-table :data="incident.related_alerts" size="small" border>
            <el-table-column prop="fingerprint" label="Fingerprint" min-width="140" />
            <el-table-column prop="title" label="标题" min-width="160" />
            <el-table-column prop="severity" label="级别" width="80" />
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="section-card timeline-card">
          <template #header>时间线</template>
          <el-timeline v-if="timeline.length">
            <el-timeline-item
              v-for="event in timeline"
              :key="event.id"
              :timestamp="event.created_at"
              placement="top"
            >
              <p class="timeline-content">{{ event.content }}</p>
              <p class="timeline-meta">
                {{ event.actor_name || event.actor_type }} · {{ event.event_type }}
              </p>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无时间线记录" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 16px;
}

.detail-row {
  margin-top: 8px;
}

.section-card {
  margin-bottom: 16px;
}

.action-bar {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.action-label {
  color: #606266;
  font-size: 14px;
  margin-right: 4px;
}

.timeline-content {
  margin: 0 0 4px;
  font-size: 14px;
  color: #303133;
}

.timeline-meta {
  margin: 0;
  font-size: 12px;
  color: #909399;
}

.timeline-card {
  max-height: calc(100vh - 140px);
  overflow-y: auto;
}
</style>
