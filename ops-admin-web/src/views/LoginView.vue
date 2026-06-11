<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'OpsAI@2025',
})

async function onSubmit() {
  loading.value = true
  try {
    await auth.login({ username: form.username, password: form.password })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/admin/users'
    router.push(redirect)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <h1 class="title">OpsAI 管理台</h1>
      <p class="subtitle">用户管理 · 接入配置</p>
      <el-form :model="form" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="管理员账号">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="success" native-type="submit" :loading="loading" class="submit-btn">
          登录
        </el-button>
      </el-form>
      <p class="hint">仅 role=admin 的账号可登录管理台</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2d3a4b 0%, #3d5a45 50%, #2d3a4b 100%);
}

.login-card {
  width: 400px;
  padding: 8px;
}

.title {
  margin: 0 0 4px;
  font-size: 22px;
  text-align: center;
}

.subtitle {
  margin: 0 0 24px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.hint {
  margin: 16px 0 0;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
</style>
