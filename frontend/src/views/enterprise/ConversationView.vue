<template>
  <div class="conversation-view">
    <!-- Left Panel: Conversation List (300px) -->
    <div class="left-panel">
      <div class="panel-header">
        <h3>对话列表</h3>
        <el-button type="primary" size="small" @click="handleNewConversation">
          新建对话
        </el-button>
      </div>

      <div class="conversation-list" v-loading="listLoading">
        <el-empty
          v-if="store.sortedConversations.length === 0 && !listLoading"
          description="暂无对话"
          :image-size="80"
        />

        <div
          v-for="conv in store.sortedConversations"
          :key="conv.id"
          class="conversation-item"
          :class="{ active: conv.id === store.activeConversationId }"
          @click="selectConversation(conv)"
        >
          <div class="conv-avatar">
            <el-icon :size="18"><User /></el-icon>
          </div>
          <div class="conv-info">
            <div class="conv-title">{{ conv.title || '新对话' }}</div>
            <div class="conv-time">{{ formatDate(conv.updated_at || conv.created_at) }}</div>
          </div>
          <el-popconfirm
            title="确定删除该对话？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDeleteConversation(conv)"
          >
            <template #reference>
              <el-button
                link
                type="danger"
                :icon="Delete"
                class="conv-delete-btn"
                @click.stop
              />
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>

    <!-- Right Panel: Chat Window -->
    <div class="right-panel">
      <!-- Empty state when no active conversation -->
      <el-empty
        v-if="!store.activeConversationId"
        description="选择或创建一个对话开始交流"
        :image-size="120"
      />

      <!-- Active chat -->
      <template v-else>
        <div class="chat-messages" ref="messagesContainer">
          <div v-if="messagesLoading" class="messages-loading">
            <el-icon class="is-loading" :size="20"><Loading /></el-icon>
            <span>加载消息中...</span>
          </div>

          <el-empty
            v-else-if="store.messages.length === 0"
            description="发送第一条消息开始对话"
            :image-size="80"
          />

          <!-- Message bubbles -->
          <div
            v-for="msg in store.messages"
            :key="msg.id"
            class="message-wrapper"
            :class="'msg-row-' + msg.role"
          >
            <!-- Assistant avatar -->
            <el-avatar
              v-if="msg.role === 'assistant'"
              :size="36"
              class="msg-avatar msg-avatar-left"
              :icon="Cpu"
            />
            <!-- Spacer for alignment when user messages are right-aligned -->
            <div
              class="message-bubble"
              :class="'bubble-' + msg.role"
            >
              <div
                v-if="msg.content"
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <!-- LangGraph pipeline status (processing, no content yet) -->
              <div
                v-if="msg.isStreaming && !msg.content && statusMessage"
                class="pipeline-status"
              >
                <el-icon class="is-loading" :size="14"><Loading /></el-icon>
                <span>{{ statusMessage }}</span>
              </div>
              <!-- Typing indicator (no content yet, streaming has started) -->
              <div
                v-if="msg.isStreaming && !msg.content && !statusMessage"
                class="typing-indicator"
              >
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
              <!-- Cursor indicator when streaming has content -->
              <span
                v-if="msg.isStreaming && msg.content"
                class="streaming-cursor"
              >|</span>
            </div>
            <!-- User avatar -->
            <el-avatar
              v-if="msg.role === 'user'"
              :size="36"
              class="msg-avatar msg-avatar-right"
              :icon="User"
            />
          </div>
        </div>

        <!-- Input area -->
        <div class="chat-input-area">
          <div style="display:flex;align-items:flex-start;gap:8px">
            <el-input
              v-model="inputContent"
              type="textarea"
              :rows="3"
              :maxlength="4000"
              show-word-limit
              placeholder="输入您的问题或使用语音... (Enter 发送，Shift+Enter 换行)"
              :disabled="store.isStreaming"
              @keydown.enter.exact.prevent="handleSend"
              resize="none"
              style="flex:1"
            />
            <VoiceInput @transcribed="onVoiceTranscribed" :disabled="store.isStreaming" style="margin-top:2px" />
          </div>
          <div class="input-actions">
            <span class="input-hint">Enter 发送 / Shift+Enter 换行</span>
            <el-button
              type="primary"
              :loading="store.isStreaming"
              :disabled="!inputContent.trim() || store.isStreaming"
              @click="handleSend"
            >
              {{ store.isStreaming ? '回复中...' : '发送' }}
            </el-button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Cpu, Delete, Loading } from '@element-plus/icons-vue'
import { useConversationStore } from '@/stores/conversation'
import { useAuthStore } from '@/stores/auth'
import { useSSE } from '@/composables/useSSE'
import { marked } from 'marked'
import VoiceInput from '@/components/voice/VoiceInput.vue'

const store = useConversationStore()
const authStore = useAuthStore()
const { streamMessage, streamingContent, statusMessage } = useSSE()

const listLoading = ref(false)
const messagesLoading = ref(false)
const inputContent = ref('')
const messagesContainer = ref(null)

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(content) {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch {
    return content
  }
}

// Format date as Chinese locale string: "YYYY年MM月DD日 HH:mm"
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const targetDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.floor((today - targetDay) / 86400000)

  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const time = `${hh}:${mm}`

  if (diffDays === 0) {
    return `今天 ${time}`
  } else if (diffDays === 1) {
    return `昨天 ${time}`
  } else if (diffDays === 2) {
    return `前天 ${time}`
  } else {
    const y = date.getFullYear()
    const m = date.getMonth() + 1
    const d = date.getDate()
    if (y === now.getFullYear()) {
      return `${m}月${d}日 ${time}`
    }
    return `${y}年${m}月${d}日 ${time}`
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Watch for new messages
watch(() => store.messages.length, () => {
  scrollToBottom()
})

// Watch streaming content for live scroll
watch(streamingContent, () => {
  scrollToBottom()
})

// On mount: fetch conversations, select first one if exists
onMounted(async () => {
  listLoading.value = true
  try {
    await store.fetchConversations()
    if (store.sortedConversations.length > 0) {
      selectConversation(store.sortedConversations[0])
    } else {
      // No conversations — ensure state is clean (prevents cross-user leakage)
      store.clearActiveConversation()
    }
  } catch {
    store.clearActiveConversation()
  } finally {
    listLoading.value = false
  }
})

// Select a conversation and load its messages
async function selectConversation(conv) {
  if (store.activeConversationId === conv.id) return
  store.setActiveConversation(conv.id)
  messagesLoading.value = true
  try {
    const res = await store.fetchMessages(conv.id)
    // 后端返回 JSON 数组 [{...}]，axios 拦截器提取 response.data 后仍是数组
    // 兼容两种格式：数组直接用，对象取 .items 或 .data 字段
    store.messages = Array.isArray(res)
      ? res
      : Array.isArray(res?.items)
        ? res.items
        : Array.isArray(res?.data)
          ? res.data
          : []
    scrollToBottom()
  } catch {
    store.messages = []
  } finally {
    messagesLoading.value = false
  }
}

// Create a new conversation
async function handleNewConversation() {
  try {
    const conv = await store.createNewConversation('新对话')
    await store.fetchConversations()
    selectConversation(conv)
  } catch {
    // Handled by interceptor
  }
}

// Delete a conversation
async function handleDeleteConversation(conv) {
  try {
    await store.removeConversation(conv.id)
    ElMessage.success('对话已删除')
  } catch {
    // Handled by interceptor
  }
}

function onVoiceTranscribed(text) {
  inputContent.value = inputContent.value
    ? inputContent.value + '\n' + text
    : text
}

// Send a message with SSE streaming
async function handleSend() {
  const content = inputContent.value.trim()
  if (!content || store.isStreaming) return

  let conversationId = store.activeConversationId
  if (!conversationId) {
    try {
      const conv = await store.createNewConversation('新对话')
      conversationId = conv.id
      store.setActiveConversation(conversationId)
      await store.fetchConversations()
    } catch {
      return
    }
  }

  inputContent.value = ''

  // Push user message
  store.messages.push({
    id: Date.now().toString(),
    conversation_id: conversationId,
    role: 'user',
    content,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()

  // Create assistant placeholder
  const assistantMsgId = (Date.now() + 1).toString()
  store.messages.push({
    id: assistantMsgId,
    conversation_id: conversationId,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
    isStreaming: true,
  })

  store.isStreaming = true

  // Live-update streaming content into the assistant message
  const stopWatch = watch(streamingContent, (newContent) => {
    const idx = store.messages.findIndex((m) => m.id === assistantMsgId)
    if (idx !== -1) {
      store.messages[idx].content = newContent
    }
  })

  try {
    const result = await streamMessage(
      `/api/v1/conversations/${conversationId}/messages`,
      { content },
      authStore.accessToken
    )
    const idx = store.messages.findIndex((m) => m.id === assistantMsgId)
    if (idx !== -1) {
      store.messages[idx] = {
        ...store.messages[idx],
        content: result.fullContent || store.messages[idx].content,
        isStreaming: false,
      }
    }
    await store.fetchConversations()
  } catch (err) {
    const idx = store.messages.findIndex((m) => m.id === assistantMsgId)
    if (idx !== -1) {
      const msg = err?.message || '抱歉，回复生成失败。请重试。'
      store.messages[idx].content = msg
      store.messages[idx].isStreaming = false
      store.messages[idx].isError = true
    }
  } finally {
    stopWatch()
    store.isStreaming = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.conversation-view {
  display: flex;
  height: calc(100vh - 132px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* ======== Left Panel: 300px ======== */
.left-panel {
  width: 300px;
  min-width: 300px;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.conversation-item:hover {
  background: #e8f4fd;
}

.conversation-item.active {
  background: #d9ecff;
}

.conv-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e8f4fd;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  flex-shrink: 0;
  margin-right: 10px;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.conv-time {
  font-size: 12px;
  color: #909399;
}

.conv-delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
  margin-left: 4px;
}

.conversation-item:hover .conv-delete-btn {
  opacity: 1;
}

/* ======== Right Panel: Chat Window ======== */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ======== Chat Messages ======== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}

.messages-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
  gap: 8px;
  font-size: 14px;
}

/* ======== Message Row ======== */
.message-wrapper {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 10px;
}

.msg-row-user {
  flex-direction: row-reverse;
}

.msg-row-assistant {
  flex-direction: row;
}

.msg-avatar {
  flex-shrink: 0;
}

.msg-avatar-left {
  background: #3b82f6;
  color: #fff;
}

.msg-avatar-right {
  background: #6366f1;
  color: #fff;
}

/* ======== Message Bubble ======== */
.message-bubble {
  position: relative;
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.bubble-user {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-assistant {
  background: #fff;
  color: #303133;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* Markdown styles */
.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.markdown-body :deep(li) {
  margin: 2px 0;
}

.bubble-user .markdown-body :deep(pre) {
  background: rgba(255, 255, 255, 0.15);
}

.bubble-user .markdown-body :deep(code) {
  color: #fff;
}

/* ======== Typing indicator ======== */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 0;
}

.typing-indicator .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
  animation: typing-bounce 1.4s infinite both;
}

.typing-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ======== Pipeline status ======== */
.pipeline-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  color: #409eff;
  white-space: nowrap;
}

/* ======== Streaming cursor ======== */
.streaming-cursor {
  display: inline;
  color: #409eff;
  font-weight: 700;
  animation: blink-cursor 0.8s infinite;
}

@keyframes blink-cursor {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ======== Chat Input Area ======== */
.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.chat-input-area :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.input-hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
