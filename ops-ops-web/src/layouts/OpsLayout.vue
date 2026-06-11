<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, List, Monitor } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/incidents')) return '/incidents'
  return route.path
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="ops-layout">
    <el-aside width="220px" class="ops-aside">
      <div class="brand">
        <el-icon :size="22"><Monitor /></el-icon>
        <span>OpsAI 运维台</span>
      </div>
      <el-menu :default-active="activeMenu" router class="ops-menu">
        <el-menu-item index="/alerts">
          <el-icon><Bell /></el-icon>
          <span>告警列表</span>
        </el-menu-item>
        <el-menu-item index="/incidents">
          <el-icon><List /></el-icon>
          <span>故障列表</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="ops-header">
        <span class="page-title">{{ (route.meta.title as string) || '运维工作台' }}</span>
        <div class="header-right">
          <span class="user-name">{{ auth.user?.displayName }}</span>
          <el-button type="primary" link @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="ops-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.ops-layout {
  min-height: 100vh;
  background: #f0f2f5;
}

.ops-aside {
  background: #1a2332;
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ops-menu {
  border-right: none;
  background: transparent;
}

.ops-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.75);
}

.ops-menu :deep(.el-menu-item.is-active) {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

.ops-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  height: 56px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: #606266;
  font-size: 14px;
}

.ops-main {
  padding: 20px;
}
</style>
