<template>
  <div class="template-page">
    <div class="page-header">
      <h2>回复模板</h2>
      <div>
        <el-switch v-model="showInactive" active-text="显示已禁用" style="margin-right:16px" @change="load" />
        <el-button type="primary" @click="openCreate">新增模板</el-button>
      </div>
    </div>

    <el-card>
      <!-- Category tabs -->
      <el-tabs v-model="activeCategory" @tab-change="onCategoryChange">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane v-for="cat in store.categories" :key="cat" :label="cat" :name="cat" />
      </el-tabs>

      <el-row :gutter="20" v-loading="store.loading">
        <el-col :span="8" v-for="tpl in filteredTemplates" :key="tpl.id">
          <el-card shadow="hover" :class="['tpl-card', { inactive: !tpl.is_active }]">
            <template #header>
              <div class="tpl-header">
                <span>{{ tpl.title }}</span>
                <div>
                  <el-tag v-if="!tpl.is_active" type="danger" size="small" style="margin-right:4px">已禁用</el-tag>
                  <el-tag size="small">{{ tpl.category }}</el-tag>
                </div>
              </div>
            </template>
            <p class="tpl-preview">{{ tpl.content.substring(0, 100) }}...</p>
            <div class="tpl-actions">
              <span style="font-size:12px;color:#999">使用 {{ tpl.usage_count }} 次</span>
              <div>
                <el-button v-if="!tpl.is_active" link type="success" @click="enableTpl(tpl)">启用</el-button>
                <el-button link type="primary" @click="editTemplate(tpl)">编辑</el-button>
                <el-button link type="danger" @click="remove(tpl.id)">删除</el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!store.loading && filteredTemplates.length===0" description="暂无模板" />
    </el-card>

    <el-dialog v-model="showCreate" :title="editingId?'编辑模板':'新增模板'" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="6"
            placeholder="支持变量: {customer_name}, {issue_summary}, {possible_cause}" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate=false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">{{ editingId?'更新':'创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useTemplateStore } from '@/stores/templates'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useTemplateStore()
const showCreate = ref(false)
const saving = ref(false)
const editingId = ref(null)
const activeCategory = ref('')
const showInactive = ref(false)
const form = reactive({ title: '', category: '通用', content: '' })

const filteredTemplates = computed(() => {
  if (!activeCategory.value) return store.templates
  return store.templates.filter(t => t.category === activeCategory.value)
})

async function load() {
  await store.fetchTemplates(null, showInactive.value)
}

function onCategoryChange() {
  // 前端过滤，无需重新加载
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', category: '通用', content: '' })
  showCreate.value = true
}

function editTemplate(tpl) {
  editingId.value = tpl.id
  Object.assign(form, { title: tpl.title, category: tpl.category, content: tpl.content })
  showCreate.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await store.editTemplate(editingId.value, { ...form })
      ElMessage.success('已更新')
    } else {
      await store.addTemplate({ ...form })
      ElMessage.success('已创建')
    }
    showCreate.value = false
    editingId.value = null
    load()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function enableTpl(tpl) {
  try {
    await store.editTemplate(tpl.id, { is_active: true })
    ElMessage.success('已启用')
    load()
  } catch {
    ElMessage.error('启用失败')
  }
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await store.removeTemplate(id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.tpl-header { display: flex; justify-content: space-between; align-items: center; }
.tpl-card { margin-bottom: 16px; transition: opacity 0.3s; }
.tpl-card.inactive { opacity: 0.5; }
.tpl-preview { color: #666; font-size: 13px; }
.tpl-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
</style>