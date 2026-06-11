<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { SEVERITY_LABELS, type AlertEventSummary } from '@opsai/shared'
import { listAlerts } from '@/api/alerts'

const loading = ref(false)
const items = ref<AlertEventSummary[]>([])
const total = ref(0)

const filters = reactive({
  page: 1,
  page_size: 20,
  severity: '',
  source: '',
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

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: filters.page,
      page_size: filters.page_size,
    }
    if (filters.severity) params.severity = filters.severity
    if (filters.source) params.source = filters.source
    if (filters.keyword) params.keyword = filters.keyword
    const data = await listAlerts(params)
    items.value = data.items
    total.value = data.meta.total
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载告警失败')
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

onMounted(fetchData)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>告警事件</span>
        <el-button type="primary" link @click="fetchData">刷新</el-button>
      </div>
    </template>

    <el-form :inline="true" class="filter-form" @submit.prevent="onSearch">
      <el-form-item label="严重级别">
        <el-select v-model="filters.severity" clearable placeholder="全部" style="width: 120px">
          <el-option label="严重" value="critical" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
      </el-form-item>
      <el-form-item label="来源">
        <el-input v-model="filters.source" placeholder="alertmanager" clearable style="width: 140px" />
      </el-form-item>
      <el-form-item label="关键词">
        <el-input v-model="filters.keyword" placeholder="标题搜索" clearable style="width: 160px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSearch">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="items" stripe border>
      <el-table-column prop="source" label="来源" width="120" />
      <el-table-column prop="severity" label="级别" width="90">
        <template #default="{ row }">
          <el-tag :type="severityTagType(row.severity)" size="small">
            {{ SEVERITY_LABELS[row.severity as keyof typeof SEVERITY_LABELS] || row.severity }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="fingerprint" label="Fingerprint" min-width="160" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
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

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
