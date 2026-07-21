<template>
  <div class="knowledge-management">
    <div class="page-header">
      <h2>知识库管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openUploadDialog">
          <el-icon><Upload /></el-icon>上传文档
        </el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="knowledgeStore.documents" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="文档名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="file_type" label="文件类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.file_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="文件大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" />
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleUploadMore">上传</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="docPage"
          :page-size="docPageSize"
          :total="knowledgeStore.documentsTotal"
          layout="total, prev, pager, next"
          @current-change="loadDocs"
        />
      </div>
    </el-card>

    <!-- Upload dialog -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="520px" @closed="resetUploadForm">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="文档标题">
          <el-input v-model="uploadForm.title" placeholder="请输入文档标题（留空则使用文件名）" />
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.pptx"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="upload-tip">支持 PDF、Word、Excel、PPT、TXT、Markdown、CSV 格式</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number v-model="uploadForm.chunkSize" :min="100" :max="2000" :step="100" />
        </el-form-item>
        <el-form-item label="重叠大小">
          <el-input-number v-model="uploadForm.chunkOverlap" :min="0" :max="500" :step="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="handleUpload">
          开始上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'

const knowledgeStore = useKnowledgeStore()
const loading = ref(false)
const docPage = ref(1)
const docPageSize = ref(20)
const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const selectedFile = ref(null)
const fileList = ref([])
const uploadForm = reactive({ title: '', chunkSize: 500, chunkOverlap: 50 })

// ─── Helpers ───

function statusLabel(s) {
  const map = {
    uploading: '上传中',
    processing: '处理中',
    ready: '就绪',
    error: '错误',
    failed: '失败'
  }
  return map[s] || s || '-'
}

function statusTagType(s) {
  const map = {
    uploading: 'warning',
    processing: 'warning',
    ready: 'success',
    error: 'danger',
    failed: 'danger'
  }
  return map[s] || 'info'
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

function formatSize(bytes) {
  if (bytes == null || bytes === '') return '-'
  const n = Number(bytes)
  if (Number.isNaN(n)) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / (1024 * 1024)).toFixed(1) + ' MB'
}

// ─── Data loading ───

async function loadDocs(p) {
  if (p) docPage.value = p
  loading.value = true
  try {
    await knowledgeStore.fetchDocuments(docPage.value, docPageSize.value)
  } finally {
    loading.value = false
  }
}

// ─── Upload ───

function openUploadDialog() {
  resetUploadForm()
  showUploadDialog.value = true
}

function resetUploadForm() {
  uploadForm.title = ''
  uploadForm.chunkSize = 500
  uploadForm.chunkOverlap = 50
  selectedFile.value = null
  fileList.value = []
}

function handleFileChange(file) {
  selectedFile.value = file.raw
  fileList.value = [file]
}

function handleFileRemove() {
  selectedFile.value = null
  fileList.value = []
}

function handleUploadMore() {
  openUploadDialog()
}

async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  uploading.value = true
  try {
    await knowledgeStore.uploadDocumentFile(
      selectedFile.value,
      uploadForm.title,
      uploadForm.chunkSize,
      uploadForm.chunkOverlap
    )
    ElMessage.success('文档上传成功，正在后台处理...')
    showUploadDialog.value = false
    resetUploadForm()
    await loadDocs()
  } catch {
    // error handled by store / interceptor
  } finally {
    uploading.value = false
  }
}

// ─── Delete ───

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档「${row.title}」吗？删除后相关的知识分块也会被清除，此操作不可撤销。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await knowledgeStore.removeDocument(row.id)
    ElMessage.success('文档已删除')
    await loadDocs()
  } catch {
    // user cancelled or error handled by store
  }
}

onMounted(() => {
  loadDocs()
})
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
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
</style>
