<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  INCIDENT_STATUS_LABELS,
  SEVERITY_LABELS,
  type IncidentSummary,
} from '@opsai/shared'
import { listIncidents } from '@/api/incidents'

const router = useRouter()
const loading = ref(false)
const items = ref<IncidentSummary[]>([])
const total = ref(0)

const filters = reactive({
  page: 1,
  page_size: 20,
  status: '',
  severity: '',
  keyword: '',
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

function statusTagType(status: string) {
  if (status === 'closed') return 'info'
  if (status === 'resolved') return 'success'
  if (status === 'open') return 'danger'
  return 'warning'
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: filters.page,
      page_size: filters.page_size,
    }
    if (filters.status) params.status = filters.status
    if (filters.severity) params.severity = filters.severity
    if (filters.keyword) params.keyword = filters.keyword
    const data = await listIncidents(params)
    items.value = data.items
    total.value = data.meta.total
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载故障列表失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  filters.page = 1
  fetchData()
}

function onPageChange(page: number) {
  filters.page = page
  fetchData()
}

function goDetail(row: IncidentSummary) {
  router.push(`/incidents/${row.id}`)
}

onMounted(fetchData)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>故障事件 (Incident)</span>
        <el-button type="primary" link @click="fetchData">刷新</el-button>
      </div>
    </template>

    <el-form :inline="true" class="filter-form" @submit.prevent="onSearch">
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 140px">
          <el-option
            v-for="(label, value) in INCIDENT_STATUS_LABELS"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="严重级别">
        <el-select v-model="filters.severity" clearable placeholder="全部" style="width: 120px">
          <el-option label="严重" value="critical" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
      </el-form-item>
      <el-form-item label="关键词">
        <el-input v-model="filters.keyword" placeholder="标题搜索" clearable style="width: 160px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSearch">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table
      v-loading="loading"
      :data="items"
      stripe
      border
      class="clickable-table"
      @row-click="goDetail"
    >
      <el-table-column prop="incident_no" label="单号" width="160" />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ INCIDENT_STATUS_LABELS[row.status as keyof typeof INCIDENT_STATUS_LABELS] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="severity" label="级别" width="90">
        <template #default="{ row }">
          <el-tag :type="severityTagType(row.severity)" size="small">
            {{ SEVERITY_LABELS[row.severity as keyof typeof SEVERITY_LABELS] || row.severity }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="负责人" width="120">
        <template #default="{ row }">{{ row.owner_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="service" label="服务" width="140" show-overflow-tooltip />
      <el-table-column prop="alert_count" label="告警数" width="80" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="filters.page"
        :page-size="filters.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-form {
  margin-bottom: 16px;
}

.clickable-table :deep(tbody tr) {
  cursor: pointer;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
