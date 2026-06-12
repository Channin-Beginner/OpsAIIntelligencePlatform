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
  type RcaEvidenceItem,
  type RcaResult,
  type TimelineEvent,
} from '@opsai/shared'
import {
  getIncident,
  getIncidentRca,
  listTimeline,
  patchIncident,
  submitIncidentFeedback,
  triggerIncidentRca,
} from '@/api/incidents'
import { getRunbook, listRunbookExecutions, startRunbookExecution } from '@/api/runbooks'
import type { Runbook, RunbookExecution } from '@opsai/shared'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const actionLoading = ref(false)
const rcaLoading = ref(false)
const feedbackLoading = ref(false)
const incident = ref<IncidentDetail | null>(null)
const timeline = ref<TimelineEvent[]>([])
const rcaResult = ref<RcaResult | null>(null)
const feedbackScore = ref(4)
const feedbackComment = ref('')
const loadedRunbook = ref<Runbook | null>(null)
const runbookLoading = ref(false)
const executeLoading = ref(false)
const runbookExecutions = ref<RunbookExecution[]>([])
const suggestedRunbooks = ref<Runbook[]>([])

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

function evidenceTagType(type: RcaEvidenceItem['type']) {
  const map: Record<string, string> = {
    metric: 'primary',
    log: 'warning',
    trace: 'success',
    kb: 'info',
  }
  return map[type] || ''
}

async function fetchSuggestedRunbooks(ids: number[]) {
  if (!ids.length) {
    suggestedRunbooks.value = []
    return
  }
  const books: Runbook[] = []
  for (const id of ids) {
    try {
      books.push(await getRunbook(id))
    } catch {
      /* skip missing */
    }
  }
  suggestedRunbooks.value = books
}

async function fetchRunbookExecutions() {
  try {
    const data = await listRunbookExecutions(incidentId.value)
    runbookExecutions.value = data.items
  } catch {
    runbookExecutions.value = []
  }
}

async function loadRunbook(runbook: Runbook) {
  runbookLoading.value = true
  try {
    loadedRunbook.value = await getRunbook(runbook.id)
    ElMessage.success(`已加载 Runbook：${loadedRunbook.value.title}`)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载 Runbook 失败')
  } finally {
    runbookLoading.value = false
  }
}

async function executeLoadedRunbook() {
  if (!loadedRunbook.value) return
  try {
    const hasManualStep = loadedRunbook.value.steps.some((s) => s.action_type === 'manual')
    await ElMessageBox.confirm(
      `确认半自动执行「${loadedRunbook.value.title}」？\n` +
        '将自动调用本机 EcomAI Admin chaos API（关闭 feature flag 等）。' +
        (hasManualStep
          ? '\n\n注意：含人工步骤，不会自动结束终端里的 inject_portal_500.py；执行后请 Ctrl+C 停脚本，或等待脚本检测到 flag 关闭后自行退出。'
          : ''),
      'Runbook 执行确认',
      { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '取消' },
    )
    executeLoading.value = true
    const result = await startRunbookExecution(incidentId.value, {
      runbook_id: loadedRunbook.value.id,
      rca_result_id: rcaResult.value?.id,
      confirmed: true,
    })
    if (result.status === 'completed') {
      const manualPending = result.step_results?.some((s) => s.action_type === 'manual')
      ElMessage.success({
        message: manualPending
          ? 'HTTP 步骤已完成；请停止终端中的 inject_portal_500.py（或等待其自动退出）'
          : 'Runbook 执行完成',
        duration: manualPending ? 8000 : 3000,
      })
    } else {
      ElMessage.warning('Runbook 执行结束（含失败步骤）')
    }
    await fetchDetail()
    await fetchRunbookExecutions()
  } catch (e) {
    if (e === 'cancel') return
    ElMessage.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    executeLoading.value = false
  }
}

async function fetchDetail() {
  loading.value = true
  try {
    const [detail, timelineData, rca] = await Promise.all([
      getIncident(incidentId.value),
      listTimeline(incidentId.value),
      getIncidentRca(incidentId.value),
    ])
    incident.value = detail
    timeline.value = timelineData.items
    rcaResult.value = rca
    await fetchSuggestedRunbooks(rca?.suggested_runbook_ids || [])
    await fetchRunbookExecutions()
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

async function sleep(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function pollRcaResult(maxAttempts = 20, intervalMs = 3000) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const rca = await getIncidentRca(incidentId.value)
    if (rca?.status === 'completed') {
      return rca
    }
    if (attempt < maxAttempts - 1) {
      await sleep(intervalMs)
    }
  }
  return null
}

async function runRca() {
  rcaLoading.value = true
  try {
    rcaResult.value = await triggerIncidentRca(incidentId.value)
    ElMessage.success('RCA 分析完成')
    await fetchDetail()
  } catch (e) {
    const message = e instanceof Error ? e.message : 'RCA 失败'
    const timedOut = /timeout/i.test(message)
    if (timedOut) {
      ElMessage.warning('分析仍在进行，正在同步结果…')
      const polled = await pollRcaResult()
      if (polled) {
        rcaResult.value = polled
        ElMessage.success('RCA 分析已完成（后台已生成结果）')
        await fetchDetail()
        return
      }
    }
    ElMessage.error(message)
  } finally {
    rcaLoading.value = false
  }
}

async function submitFeedback(verdict: 'accept' | 'reject') {
  if (!rcaResult.value) {
    ElMessage.warning('请先运行 RCA')
    return
  }
  feedbackLoading.value = true
  try {
    await submitIncidentFeedback(incidentId.value, {
      score: feedbackScore.value,
      verdict,
      comment: feedbackComment.value || undefined,
      rca_result_id: rcaResult.value.id,
    })
    ElMessage.success(verdict === 'accept' ? '已采纳 RCA' : '已驳回 RCA')
    feedbackComment.value = ''
    await fetchDetail()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交反馈失败')
  } finally {
    feedbackLoading.value = false
  }
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
          <template #header>
            <div class="rca-header">
              <span>RCA 根因分析</span>
              <el-button type="primary" size="small" :loading="rcaLoading" @click="runRca">
                {{ rcaResult ? '重新分析' : '运行 RCA' }}
              </el-button>
            </div>
          </template>

          <template v-if="rcaResult">
            <el-descriptions :column="1" border class="rca-summary">
              <el-descriptions-item label="状态">
                <el-tag size="small">{{ rcaResult.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="置信度">
                {{
                  rcaResult.confidence != null
                    ? `${(rcaResult.confidence * 100).toFixed(0)}%`
                    : '—'
                }}
                <span v-if="rcaResult.model_name" class="model-hint">
                  · {{ rcaResult.model_name }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="根因假设">
                {{ rcaResult.hypothesis || '—' }}
              </el-descriptions-item>
              <el-descriptions-item
                v-if="rcaResult.suggested_actions?.length"
                label="建议处置"
              >
                <ul class="action-list">
                  <li v-for="(action, idx) in rcaResult.suggested_actions" :key="idx">
                    {{ action }}
                  </li>
                </ul>
              </el-descriptions-item>
            </el-descriptions>

            <div v-if="rcaResult.evidence?.length" class="evidence-block">
              <h4 class="evidence-title">证据链</h4>
              <el-collapse accordion>
                <el-collapse-item
                  v-for="(item, idx) in rcaResult.evidence"
                  :key="idx"
                  :name="idx"
                >
                  <template #title>
                    <el-tag :type="evidenceTagType(item.type)" size="small" class="ev-tag">
                      {{ item.type }}
                    </el-tag>
                    <span class="ev-summary">{{ item.summary }}</span>
                  </template>
                  <p v-if="item.query" class="ev-query">{{ item.query }}</p>
                  <pre v-if="item.detail" class="ev-detail">{{
                    JSON.stringify(item.detail, null, 2)
                  }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>

            <div v-if="rcaResult.status === 'completed'" class="feedback-block">
              <h4 class="evidence-title">工程师反馈</h4>
              <div class="feedback-row">
                <span>评分</span>
                <el-rate v-model="feedbackScore" :max="5" />
              </div>
              <el-input
                v-model="feedbackComment"
                type="textarea"
                :rows="2"
                placeholder="可选：补充意见"
              />
              <div class="feedback-actions">
                <el-button
                  type="success"
                  :loading="feedbackLoading"
                  @click="submitFeedback('accept')"
                >
                  采纳
                </el-button>
                <el-button :loading="feedbackLoading" @click="submitFeedback('reject')">
                  驳回
                </el-button>
              </div>
            </div>
          </template>
          <el-empty v-else description="尚未运行 RCA，点击右上角开始分析" :image-size="72" />
        </el-card>

        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="rca-header">
              <span>Runbook 半自动处置</span>
              <el-tag v-if="loadedRunbook" size="small" type="success">
                已加载：{{ loadedRunbook.title }}
              </el-tag>
            </div>
          </template>

          <div v-if="suggestedRunbooks.length" class="runbook-suggest">
            <h4 class="evidence-title">RCA 推荐 Runbook</h4>
            <div class="runbook-chips">
              <el-button
                v-for="rb in suggestedRunbooks"
                :key="rb.id"
                size="small"
                :loading="runbookLoading"
                @click="loadRunbook(rb)"
              >
                一键加载 · {{ rb.title }}
              </el-button>
            </div>
          </div>
          <el-empty
            v-else-if="rcaResult"
            description="暂无推荐 Runbook（可先在管理台发布手册）"
            :image-size="56"
          />

          <div v-if="loadedRunbook" class="runbook-loaded">
            <el-descriptions :column="1" border size="small" class="runbook-meta">
              <el-descriptions-item label="风险">
                {{ loadedRunbook.risk_level }}
              </el-descriptions-item>
              <el-descriptions-item label="描述">
                {{ loadedRunbook.description || '—' }}
              </el-descriptions-item>
            </el-descriptions>

            <ol class="runbook-steps">
              <li v-for="step in loadedRunbook.steps" :key="step.order">
                <strong>{{ step.title }}</strong>
                <span class="step-type">（{{ step.action_type }}）</span>
                <p v-if="step.description" class="step-desc">{{ step.description }}</p>
              </li>
            </ol>

            <el-button type="warning" :loading="executeLoading" @click="executeLoadedRunbook">
              确认并执行 Runbook
            </el-button>
          </div>

          <div v-if="runbookExecutions.length" class="runbook-history">
            <h4 class="evidence-title">执行记录</h4>
            <el-table :data="runbookExecutions" size="small" border>
              <el-table-column prop="runbook_title" label="Runbook" min-width="140" />
              <el-table-column prop="status" label="状态" width="90" />
              <el-table-column prop="completed_at" label="完成时间" width="170" />
              <el-table-column label="步骤" min-width="120">
                <template #default="{ row }">
                  {{ row.step_results?.length || 0 }} 步
                </template>
              </el-table-column>
            </el-table>
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

.rca-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rca-summary {
  margin-bottom: 12px;
}

.model-hint {
  color: #909399;
  font-size: 12px;
}

.evidence-block,
.feedback-block {
  margin-top: 16px;
}

.evidence-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
}

.ev-tag {
  margin-right: 8px;
}

.ev-summary {
  font-size: 13px;
  color: #606266;
}

.ev-query {
  margin: 0 0 8px;
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}

.ev-detail {
  margin: 0;
  padding: 8px;
  font-size: 11px;
  background: #f5f7fa;
  border-radius: 4px;
  max-height: 200px;
  overflow: auto;
}

.action-list {
  margin: 0;
  padding-left: 18px;
}

.feedback-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.feedback-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.runbook-suggest {
  margin-bottom: 12px;
}

.runbook-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.runbook-loaded {
  margin-top: 12px;
}

.runbook-meta {
  margin-bottom: 12px;
}

.runbook-steps {
  margin: 0 0 12px;
  padding-left: 20px;
  font-size: 13px;
}

.step-type {
  color: #909399;
  margin-left: 4px;
}

.step-desc {
  margin: 4px 0 0;
  color: #606266;
  font-size: 12px;
}

.runbook-history {
  margin-top: 16px;
}
</style>
