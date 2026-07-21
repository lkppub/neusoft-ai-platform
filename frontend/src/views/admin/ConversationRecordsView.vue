<template>
  <div class="conversation-records">
    <div class="page-header">
      <h2>对话记录</h2>
    </div>

    <!-- Stats bar -->
    <el-row :gutter="20" class="stats-row" v-if="convStats">
      <el-col :span="12">
        <el-card shadow="hover" class="mini-stat">
          <p class="mini-stat-label">总对话数</p>
          <h3 class="mini-stat-value">{{ convStats.total || 0 }}</h3>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="mini-stat">
          <p class="mini-stat-label">总消息数</p>
          <h3 class="mini-stat-value">{{ convStats.total_messages || 0 }}</h3>
        </el-card>
      </el-col>
    </el-row>

    <!-- Conversations table -->
    <el-card shadow="never">
      <el-table
        :data="adminStore.allConversations"
        stripe
        v-loading="loading"
        row-key="id"
        @expand-change="onExpandChange"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-messages" v-loading="row._loadingMessages">
              <div v-if="!row._messages || row._messages.length === 0" class="no-messages">
                暂无消息记录
              </div>
              <div
                v-for="msg in row._messages"
                :key="msg.id"
                class="message-item"
                :class="msg.role"
              >
                <div class="message-role">
                  <el-tag :type="msg.role === 'user' ? 'primary' : 'success'" size="small">
                    {{ msg.role === 'user' ? '用户' : msg.role === 'assistant' ? 'AI' : msg.role }}
                  </el-tag>
                  <span class="message-time">{{ formatDate(msg.created_at) }}</span>
                </div>
                <div class="message-content">{{ msg.content }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="model_name" label="模型" width="140" show-overflow-tooltip />
        <el-table-column prop="message_count" label="消息数" width="90" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后活跃" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="adminStore.convTotal"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { ElMessage } from 'element-plus'
import { getMessages } from '@/api/conversations'

const adminStore = useAdminStore()
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const convStats = ref(null)

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}

async function loadData(p) {
  if (p) page.value = p
  loading.value = true
  try {
    await adminStore.fetchAllConversations(page.value, pageSize.value)
    convStats.value = await adminStore.getConvStats()
  } finally {
    loading.value = false
  }
}

async function onExpandChange(row, expandedRows) {
  // Only fetch when expanding (not collapsing) and messages not yet loaded
  const isExpanding = expandedRows.some(r => r.id === row.id)
  if (!isExpanding || row._messages) return

  row._loadingMessages = true
  try {
    const res = await getMessages(row.id, 1, 100)
    row._messages = res.items || res || []
  } catch {
    ElMessage.warning('加载消息失败')
    row._messages = []
  } finally {
    row._loadingMessages = false
  }
}

onMounted(() => {
  loadData()
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
}

.stats-row {
  margin-bottom: 20px;
}
.mini-stat {
  text-align: center;
}
.mini-stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}
.mini-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.expand-messages {
  padding: 12px 24px;
  max-height: 400px;
  overflow-y: auto;
  background: #fafafa;
  border-radius: 4px;
}
.no-messages {
  text-align: center;
  color: #909399;
  padding: 20px 0;
  font-size: 14px;
}
.message-item {
  padding: 10px 0;
  border-bottom: 1px solid #ebeef5;
}
.message-item:last-child {
  border-bottom: none;
}
.message-role {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.message-time {
  font-size: 12px;
  color: #c0c4cc;
}
.message-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.message-item.assistant .message-content {
  background: #ecf5ff;
  padding: 10px 12px;
  border-radius: 6px;
}
.message-item.user .message-content {
  background: #f0f9eb;
  padding: 10px 12px;
  border-radius: 6px;
}
</style>
