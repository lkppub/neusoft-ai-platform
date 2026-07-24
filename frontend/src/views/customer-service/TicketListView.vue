<template>
  <div class="ticket-list-page">
    <div class="page-header">
      <h2>工单管理</h2>
      <el-button type="primary" @click="showCreate = true" v-if="authStore.isEnterprise">创建工单</el-button>
    </div>

    <el-card>
      <div class="filters">
        <el-input v-model="filters.search" placeholder="🔍 搜索主题/描述..." clearable @change="load(1)" style="width:220px" />
        <el-select v-model="filters.status" placeholder="全部状态" clearable @change="load(1)" style="width:130px;margin-left:10px">
          <el-option label="待处理" value="open" /><el-option label="处理中" value="in_progress" />
          <el-option label="等待客户" value="waiting_customer" /><el-option label="已解决" value="resolved" /><el-option label="已关闭" value="closed" />
        </el-select>
        <el-select v-model="filters.priority" placeholder="全部优先级" clearable @change="load(1)" style="width:130px;margin-left:10px">
          <el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /><el-option label="紧急" value="urgent" />
        </el-select>
        <el-select v-model="filters.category" placeholder="全部分类" clearable @change="load(1)" style="width:150px;margin-left:10px">
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-tag type="info" v-if="store.ticketsTotal > 0" style="margin-left:10px">共 {{ store.ticketsTotal }} 条</el-tag>
      </div>

      <el-table :data="store.tickets" v-loading="loading" @row-click="goDetail"
        @sort-change="onSortChange" :default-sort="{prop: 'updated_at', order: 'descending'}"
        style="cursor:pointer;margin-top:16px" stripe>
        <el-table-column prop="subject" label="主题" min-width="200" sortable="custom" />
        <el-table-column prop="problem_category" label="分类" width="130" sortable="custom">
          <template #default="{row}"><el-tag v-if="row.problem_category" size="small" type="">{{ row.problem_category }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="110" sortable="custom">
          <template #default="{row}"><el-tag :type="priorityType(row.priority)" size="small">{{ priorityMap[row.priority] }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" sortable="custom">
          <template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ statusMap[row.status] }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="175" sortable="custom">
          <template #default="{row}">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="175" sortable="custom">
          <template #default="{row}">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar" v-if="store.ticketsTotal > 0">
        <el-pagination
          :total="store.ticketsTotal"
          :page-size="20"
          :current-page="currentPage"
          layout="total, prev, pager, next, sizes"
          :page-sizes="[10, 20, 50]"
          @current-change="p => load(p)"
          @size-change="s => { pageSize = s; load(1) }" />
      </div>
    </el-card>

    <el-dialog v-model="showCreate" title="创建工单" width="500px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="主题"><el-input v-model="createForm.subject" /></el-form-item>
        <el-form-item label="描述">
          <div style="display:flex;align-items:flex-start;gap:8px;width:100%">
            <el-input v-model="createForm.description" type="textarea" :rows="4" style="flex:1" placeholder="输入描述或使用语音..." />
            <VoiceInput @transcribed="onDescVoiceTranscribed" style="margin-top:2px" />
          </div>
        </el-form-item>
        <el-form-item label="优先级"><el-select v-model="createForm.priority"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /><el-option label="紧急" value="urgent" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="create" :loading="creating">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketStore } from '@/stores/ticket'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import VoiceInput from '@/components/voice/VoiceInput.vue'

const router = useRouter(); const store = useTicketStore(); const authStore = useAuthStore()
const loading = ref(false); const showCreate = ref(false); const creating = ref(false)
const currentPage = ref(1); const pageSize = ref(20)

// Initialize local filters from store (persist across navigations)
const filters = reactive({
  status: store.filters.status || '',
  priority: store.filters.priority || '',
  category: store.filters.category || '',
  search: store.filters.search || '',
  sortBy: store.filters.sortBy || 'updated_at',
  sortOrder: store.filters.sortOrder || 'desc',
})

// Extract unique categories from current tickets (non-reactive computed list)
const categories = computed(() => {
  const cats = new Set()
  store.tickets.forEach(t => { if (t.problem_category) cats.add(t.problem_category) })
  return [...cats].sort()
})

const createForm = reactive({ subject: '', description: '', priority: 'medium' })

const statusMap = { open: '待处理', in_progress: '处理中', waiting_customer: '等待客户', resolved: '已解决', closed: '已关闭' }
const priorityMap = { low: '低', medium: '中', high: '高', urgent: '紧急' }
function statusType(s) { return { open: 'danger', in_progress: 'warning', waiting_customer: 'info', resolved: 'success', closed: 'info' }[s] || 'info' }
function priorityType(p) { return { low: 'info', medium: 'info', high: 'warning', urgent: 'danger' }[p] || 'info' }
function formatDate(d) { if (!d) return ''; return new Date(d).toLocaleString('zh-CN') }
function goDetail(row) { router.push(`/tickets/${row.id}`) }

// Sync local filters → store → API
function syncFiltersToStore() {
  store.setFilters({
    status: filters.status, priority: filters.priority,
    category: filters.category, search: filters.search,
    sortBy: filters.sortBy, sortOrder: filters.sortOrder,
  })
}

async function load(page = currentPage.value) {
  currentPage.value = page
  syncFiltersToStore()
  loading.value = true
  try { await store.fetchTickets(page, pageSize.value) } finally { loading.value = false }
}

function onSortChange({ prop, order }) {
  if (!prop) return
  filters.sortBy = prop
  filters.sortOrder = order === 'ascending' ? 'asc' : 'desc'
  load(1)
}

function onDescVoiceTranscribed(text) {
  createForm.description = createForm.description
    ? createForm.description + ' ' + text
    : text
}

async function create() {
  if (!createForm.subject) return ElMessage.warning('请输入主题')
  creating.value = true
  try { await store.createNewTicket(createForm); showCreate.value = false; ElMessage.success('工单创建成功'); load() }
  catch { ElMessage.error('创建失败') }
  finally { creating.value = false }
}

// Restore filters from store on mount (survives navigation back from detail page)
onMounted(() => {
  filters.status = store.filters.status || ''
  filters.priority = store.filters.priority || ''
  filters.category = store.filters.category || ''
  filters.search = store.filters.search || ''
  filters.sortBy = store.filters.sortBy || 'updated_at'
  filters.sortOrder = store.filters.sortOrder || 'desc'
  load()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.filters { display: flex; align-items: center; flex-wrap: wrap; gap: 0; }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
