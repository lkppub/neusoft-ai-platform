<template>
  <div class="faq-page">
    <div class="page-header"><h2>FAQ管理</h2><el-button type="primary" @click="showCreate=true">新增FAQ</el-button></div>

    <el-card>
      <!-- Category tabs -->
      <el-tabs v-model="activeCategory" @tab-change="onCategoryChange">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane v-for="cat in store.allCategories" :key="cat" :label="cat" :name="cat" />
      </el-tabs>

      <el-input v-model="searchQuery" placeholder="搜索FAQ..." clearable style="width:300px;margin-bottom:16px" />

      <el-table :data="filteredFAQs" v-loading="loading">
        <el-table-column prop="category" label="分类" width="120"><template #default="{row}"><el-tag>{{ row.category }}</el-tag></template></el-table-column>
        <el-table-column prop="question" label="问题" min-width="250" />
        <el-table-column prop="answer" label="回答" min-width="300" show-overflow-tooltip />
        <el-table-column prop="is_published" label="状态" width="80"><template #default="{row}"><el-tag :type="row.is_published?'success':'info'" size="small">{{ row.is_published?'已发布':'草稿' }}</el-tag></template></el-table-column>
        <el-table-column prop="view_count" label="查看" width="80" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{row}">
            <el-button link type="primary" @click="editFAQ(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="store.faqsTotal"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="load"
        @size-change="load"
        style="margin-top:16px;justify-content:flex-end"
      />
    </el-card>

    <el-dialog v-model="showCreate" :title="editingId?'编辑FAQ':'新增FAQ'" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="问题"><el-input v-model="form.question" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="回答"><el-input v-model="form.answer" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="发布"><el-switch v-model="form.is_published" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="save" :loading="saving">{{ editingId?'更新':'创建' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useKnowledgeStore()
const loading = ref(false)
const showCreate = ref(false)
const saving = ref(false)
const editingId = ref(null)
const searchQuery = ref('')
const activeCategory = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const form = reactive({ category: '通用', question: '', answer: '', is_published: true })

const filteredFAQs = computed(() => {
  if (!searchQuery.value) return store.faqs
  const q = searchQuery.value.toLowerCase()
  return store.faqs.filter(f => f.question.toLowerCase().includes(q) || f.answer.toLowerCase().includes(q))
})

async function load() {
  loading.value = true
  try {
    await store.fetchFAQs(currentPage.value, pageSize.value, activeCategory.value || null, true)
  } finally {
    loading.value = false
  }
}

function onCategoryChange() {
  currentPage.value = 1
  load()
}

function editFAQ(row) {
  editingId.value = row.id
  Object.assign(form, row)
  showCreate.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await store.editFAQ(editingId.value, { ...form })
    } else {
      await store.addFAQ({ ...form })
    }
    showCreate.value = false
    editingId.value = null
    Object.assign(form, { category: '通用', question: '', answer: '', is_published: true })
    await load()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await store.removeFAQ(id)
    ElMessage.success('已删除')
    await load()
  } catch { /* cancelled */ }
}

onMounted(() => { load(); store.fetchAllCategories() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
</style>
