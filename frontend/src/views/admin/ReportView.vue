<template>
  <div class="report-page">
    <div class="page-header">
      <h2>分析报告</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showGenerateDialog = true">
          <el-icon><DataAnalysis /></el-icon>生成报告
        </el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table
        :data="adminStore.reports"
        stripe
        v-loading="loading"
        @expand-change="handleExpandChange"
        row-key="id"
        :expand-row-keys="expandedRows"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-loading="expandingId === row.id">
              <div class="expand-section" v-if="expandData[row.id]">
                <div class="expand-item">
                  <span class="expand-label">完整摘要</span>
                  <p class="expand-value">{{ expandData[row.id].summary || row.summary || '暂无' }}</p>
                </div>
                <div class="expand-item">
                  <span class="expand-label">结果数据</span>
                  <pre class="expand-json">{{ formatResultData(expandData[row.id].result_data) }}</pre>
                </div>
              </div>
              <el-empty v-else-if="expandingId !== row.id" description="暂无详细数据" :image-size="60" />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="report_type" label="报告类型" width="150">
          <template #default="{ row }">
            <el-tag size="small">{{ reportTypeLabel(row.report_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="280" show-overflow-tooltip />
        <el-table-column prop="created_at" label="生成时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && adminStore.reports.length === 0" description="暂无报告" />
    </el-card>

    <!-- Generate dialog -->
    <el-dialog v-model="showGenerateDialog" title="生成报告" width="500px" @closed="resetGenerateForm">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="报告类型" required>
          <el-select v-model="generateForm.type" style="width: 100%">
            <el-option label="每周总结" value="weekly_summary" />
            <el-option label="满意度分析" value="satisfaction_analysis" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="generateForm.type === 'weekly_summary'" label="周期范围">
          <el-date-picker
            v-model="generateForm.week"
            type="week"
            format="[第]ww[周] YYYY"
            placeholder="选择周"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="generateForm.type === 'satisfaction_analysis'" label="日期范围">
          <el-date-picker
            v-model="generateForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { ElMessage, ElMessageBox } from 'element-plus'

const adminStore = useAdminStore()
const loading = ref(false)

function reportTypeLabel(type) {
  const map = {
    weekly_summary: '每周总结',
    satisfaction_analysis: '满意度分析',
  }
  return map[type] || type
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}

function formatResultData(data) {
  if (!data) return '暂无'
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) } catch { return data }
  }
  return JSON.stringify(data, null, 2)
}

async function loadReports() {
  loading.value = true
  try { await adminStore.fetchReports() } finally { loading.value = false }
}

// Expand row to view detail
const expandedRows = ref([])
const expandingId = ref(null)
const expandData = reactive({})

async function handleExpandChange(row, expandedRowsList) {
  expandedRows.value = expandedRowsList.map(r => r.id)
  if (expandedRowsList.some(r => r.id === row.id)) {
    if (!expandData[row.id]) {
      expandingId.value = row.id
      try {
        const res = await adminStore.fetchReport(row.id)
        expandData[row.id] = res
      } finally {
        expandingId.value = null
      }
    }
  }
}

// Generate
const showGenerateDialog = ref(false)
const generating = ref(false)
const generateForm = reactive({
  type: 'weekly_summary',
  week: null,
  dateRange: null,
})

function resetGenerateForm() {
  generateForm.type = 'weekly_summary'
  generateForm.week = null
  generateForm.dateRange = null
}

async function handleGenerate() {
  generating.value = true
  try {
    const params = {}
    if (generateForm.type === 'weekly_summary') {
      params.week = generateForm.week
    } else if (generateForm.type === 'satisfaction_analysis') {
      params.date_range = generateForm.dateRange
    }
    await adminStore.generateNewReport(generateForm.type, params)
    ElMessage.success('报告已生成')
    showGenerateDialog.value = false
    await loadReports()
  } catch {
    /* handled by interceptor */
  } finally {
    generating.value = false
  }
}

// Delete
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该报告吗？', '确认', { type: 'warning' })
    await adminStore.removeReport(row.id)
    ElMessage.success('已删除')
    loadReports()
  } catch {
    /* cancelled */
  }
}

onMounted(loadReports)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  color: #303133;
  margin: 0;
}
.header-actions {
  display: flex;
  align-items: center;
}

.expand-section {
  padding: 16px 24px;
  background: #fafafa;
}
.expand-item {
  margin-bottom: 16px;
}
.expand-item:last-child {
  margin-bottom: 0;
}
.expand-label {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  font-weight: 600;
}
.expand-value {
  margin: 0;
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
}
.expand-json {
  margin: 0;
  background: #f0f2f5;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
