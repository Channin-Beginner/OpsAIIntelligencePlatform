<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UserSummary } from '@opsai/shared'
import { listUsers } from '@/api/users'

const loading = ref(false)
const users = ref<UserSummary[]>([])

const roleLabels: Record<string, string> = {
  admin: '管理员',
  operator: '运维工程师',
}

async function fetchData() {
  loading.value = true
  try {
    const data = await listUsers()
    users.value = data.items
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载用户失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>系统用户</span>
        <el-tag type="info" size="small">阶段一：只读列表，CRUD 阶段五扩展</el-tag>
      </div>
    </template>

    <el-table v-loading="loading" :data="users" stripe border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="display_name" label="显示名" width="140" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'success' : ''" size="small">
            {{ roleLabels[row.role] || row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
      <el-table-column prop="updated_at" label="更新时间" min-width="180" />
    </el-table>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
