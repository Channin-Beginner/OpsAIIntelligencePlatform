<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Runbook, RunbookStep } from '@opsai/shared'
import {
  createRunbook,
  deleteRunbook,
  getRunbookAdoptionStats,
  listRunbooks,
  publishRunbook,
  unpublishRunbook,
  updateRunbook,
} from '@/api/runbooks'

const loading = ref(false)
const statsLoading = ref(false)
const runbooks = ref<Runbook[]>([])
const stats = ref({
  recommended_rca_count: 0,
  adopted_rca_count: 0,
  adoption_rate: 0,
  total_executions: 0,
  successful_executions: 0,
  execution_success_rate: 0,
})

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  title: '',
  description: '',
  risk_level: 'low',
  service_tags_text: '',
  alert_names_text: '',
  steps_json_text: '',
})

const riskLabels: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
}

const defaultSteps: RunbookStep[] = [
  {
    order: 1,
    title: '示例 HTTP 步骤',
    description: '调用 chaos demo API',
    action_type: 'http',
    action: { method: 'GET', path: '/admin/chaos/status' },
  },
  {
    order: 2,
    title: '人工验证',
    description: '在 Grafana 确认指标恢复',
    action_type: 'manual',
    action: null,
  },
]

function resetForm() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.risk_level = 'low'
  form.service_tags_text = ''
  form.alert_names_text = ''
  form.steps_json_text = JSON.stringify(defaultSteps, null, 2)
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Runbook) {
  editingId.value = row.id
  form.title = row.title
  form.description = row.description || ''
  form.risk_level = row.risk_level
  form.service_tags_text = (row.service_tags || []).join(', ')
  form.alert_names_text = (row.alert_names || []).join(', ')
  form.steps_json_text = JSON.stringify(row.steps || [], null, 2)
  dialogVisible.value = true
}

function parseTags(text: string) {
  return text
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

function parseSteps(): RunbookStep[] {
  const parsed = JSON.parse(form.steps_json_text)
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('steps 必须是非空 JSON 数组')
  }
  return parsed
}

async function fetchData() {
  loading.value = true
  try {
    const data = await listRunbooks({ page: 1, page_size: 100 })
    runbooks.value = data.items
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载 Runbook 失败')
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  statsLoading.value = true
  try {
    stats.value = await getRunbookAdoptionStats()
  } catch {
    /* 统计可选 */
  } finally {
    statsLoading.value = false
  }
}

async function saveRunbook() {
  try {
    const steps = parseSteps()
    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      risk_level: form.risk_level,
      service_tags: parseTags(form.service_tags_text),
      alert_names: parseTags(form.alert_names_text),
      steps,
    }
    if (editingId.value) {
      await updateRunbook(editingId.value, payload)
      ElMessage.success('已更新 Runbook')
    } else {
      await createRunbook(payload)
      ElMessage.success('已创建草稿 Runbook')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handlePublish(row: Runbook) {
  try {
    await publishRunbook(row.id)
    ElMessage.success('已发布')
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '发布失败')
  }
}

async function handleUnpublish(row: Runbook) {
  try {
    await unpublishRunbook(row.id)
    ElMessage.success('已下架为草稿')
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '下架失败')
  }
}

async function handleDelete(row: Runbook) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, '删除确认', { type: 'warning' })
    await deleteRunbook(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch (e) {
    if (e === 'cancel') return
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

onMounted(() => {
  fetchData()
  fetchStats()
})
</script>

<template>
  <div>
    <el-row :gutter="16" class="stats-row">
      <el-col :span="8">
        <el-card v-loading="statsLoading" shadow="never">
          <div class="stat-label">RCA 推荐采纳率</div>
          <div class="stat-value">{{ (stats.adoption_rate * 100).toFixed(1) }}%</div>
          <div class="stat-sub">
            {{ stats.adopted_rca_count }} / {{ stats.recommended_rca_count }} 次推荐被执行
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card v-loading="statsLoading" shadow="never">
          <div class="stat-label">Runbook 执行成功率</div>
          <div class="stat-value">{{ (stats.execution_success_rate * 100).toFixed(1) }}%</div>
          <div class="stat-sub">
            {{ stats.successful_executions }} / {{ stats.total_executions }} 次执行
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>Runbook 管理</span>
          <el-button type="primary" @click="openCreate">新建 Runbook</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="runbooks" stripe border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ riskLabels[row.risk_level] || row.risk_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用服务" min-width="140">
          <template #default="{ row }">
            <el-tag v-for="tag in row.service_tags" :key="tag" size="small" class="tag-gap">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="步骤数" width="80">
          <template #default="{ row }">{{ row.steps?.length || 0 }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft'"
              link
              type="success"
              @click="handlePublish(row)"
            >
              发布
            </el-button>
            <el-button
              v-else
              link
              type="warning"
              @click="handleUnpublish(row)"
            >
              下架
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 Runbook' : '新建 Runbook'"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="256" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="form.risk_level" style="width: 160px">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务标签">
          <el-input
            v-model="form.service_tags_text"
            placeholder="逗号分隔，如 ecom-api-portal"
          />
        </el-form-item>
        <el-form-item label="告警名">
          <el-input
            v-model="form.alert_names_text"
            placeholder="逗号分隔，如 HighErrorRate"
          />
        </el-form-item>
        <el-form-item label="步骤 JSON" required>
          <el-input
            v-model="form.steps_json_text"
            type="textarea"
            :rows="12"
            placeholder="steps_json 数组"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRunbook">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-row {
  margin-bottom: 16px;
}

.stat-label {
  color: #909399;
  font-size: 13px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  margin: 8px 0 4px;
}

.stat-sub {
  color: #606266;
  font-size: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tag-gap {
  margin-right: 4px;
  margin-bottom: 2px;
}
</style>
