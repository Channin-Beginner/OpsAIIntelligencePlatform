<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { KbArticle } from '@opsai/shared'
import {
  createKbArticle,
  deleteKbArticle,
  listKbArticles,
  publishKbArticle,
  unpublishKbArticle,
  updateKbArticle,
} from '@/api/kb'

const loading = ref(false)
const articles = ref<KbArticle[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filterStatus = ref<string>('')

const form = reactive({
  title: '',
  summary: '',
  content: '',
  tags_text: '',
  service: '',
})

function resetForm() {
  editingId.value = null
  form.title = ''
  form.summary = ''
  form.content = ''
  form.tags_text = ''
  form.service = ''
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: KbArticle) {
  editingId.value = row.id
  form.title = row.title
  form.summary = row.summary || ''
  form.content = row.content
  form.tags_text = row.tags_text || ''
  form.service = row.service || ''
  dialogVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const data = await listKbArticles({
      page: 1,
      page_size: 100,
      status: filterStatus.value || undefined,
    })
    articles.value = data.items
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载 KB 失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('标题与正文不能为空')
    return
  }
  try {
    const payload = {
      title: form.title,
      summary: form.summary || null,
      content: form.content,
      tags_text: form.tags_text || null,
      service: form.service || null,
    }
    if (editingId.value) {
      await updateKbArticle(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createKbArticle(payload)
      ElMessage.success('已创建草稿')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handlePublish(row: KbArticle) {
  try {
    await publishKbArticle(row.id)
    ElMessage.success('已发布，将参与 RCA RAG')
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '发布失败')
  }
}

async function handleUnpublish(row: KbArticle) {
  try {
    await unpublishKbArticle(row.id)
    ElMessage.success('已撤回为草稿')
    await fetchData()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function handleDelete(row: KbArticle) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, '确认')
    await deleteKbArticle(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch {
    /* cancel */
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="kb-page">
    <div class="toolbar">
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 140px" @change="fetchData">
        <el-option label="草稿" value="draft" />
        <el-option label="已发布" value="published" />
      </el-select>
      <el-button type="primary" @click="openCreate">新建文章</el-button>
      <el-button @click="fetchData">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="articles" stripe>
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="service" label="服务" width="140" />
      <el-table-column label="来源 Incident" width="120">
        <template #default="{ row }">
          <span v-if="row.source_incident_id">#{{ row.source_incident_id }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
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
          <el-button v-else link type="warning" @click="handleUnpublish(row)">撤回</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 KB' : '新建 KB'" width="720px">
      <el-form label-width="88px">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="服务">
          <el-input v-model="form.service" placeholder="ecom-api-portal" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags_text" placeholder="postmortem,portal" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.content" type="textarea" :rows="12" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.muted {
  color: #909399;
}
</style>
