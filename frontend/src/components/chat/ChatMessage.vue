<template>
  <div class="message-wrapper" :class="'msg-row-' + role">
    <!-- Assistant avatar (left) -->
    <el-avatar
      v-if="role === 'assistant'"
      :size="36"
      class="msg-avatar msg-avatar-left"
      :icon="Cpu"
    />
    <div class="message-bubble" :class="'bubble-' + role">
      <!-- Markdown rendered content -->
      <div
        v-if="content"
        class="message-content markdown-body"
        v-html="renderedContent"
      ></div>
      <!-- Typing indicator -->
      <div v-if="isStreaming && !content" class="typing-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
      <!-- Streaming cursor -->
      <span v-if="isStreaming && content" class="streaming-cursor">|</span>
      <!-- Timestamp -->
      <div v-if="timestamp && !isStreaming" class="message-time">{{ formattedTime }}</div>
      <!-- Error state -->
      <div v-if="isError" class="message-error">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorText || '消息发送失败' }}</span>
      </div>
    </div>
    <!-- User avatar (right) -->
    <el-avatar
      v-if="role === 'user'"
      :size="36"
      class="msg-avatar msg-avatar-right"
      :icon="User"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Cpu, WarningFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'

const props = defineProps({
  role: { type: String, default: 'assistant', validator: v => ['user', 'assistant', 'system'].includes(v) },
  content: { type: String, default: '' },
  timestamp: { type: String, default: '' },
  isStreaming: { type: Boolean, default: false },
  isError: { type: Boolean, default: false },
  errorText: { type: String, default: '' },
})

const renderedContent = computed(() => {
  if (!props.content) return ''
  try {
    return marked.parse(props.content)
  } catch {
    return props.content
  }
})

const formattedTime = computed(() => {
  if (!props.timestamp) return ''
  const date = new Date(props.timestamp)
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
})
</script>

<style scoped>
.message-wrapper {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 10px;
}
.msg-row-user { flex-direction: row-reverse; }
.msg-row-assistant { flex-direction: row; }

.msg-avatar { flex-shrink: 0; }
.msg-avatar-left { background: #3b82f6; color: #fff; }
.msg-avatar-right { background: #6366f1; color: #fff; }

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
  background: #409eff; color: #fff;
  border-bottom-right-radius: 4px;
}
.bubble-assistant {
  background: #fff; color: #303133;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}

.message-time { font-size: 11px; color: #c0c4cc; margin-top: 4px; text-align: right; }
.bubble-user .message-time { color: rgba(255,255,255,.7); }

.message-error { display: flex; align-items: center; gap: 4px; color: #f56c6c; font-size: 12px; margin-top: 4px; }

/* Markdown */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(pre) { background: rgba(0,0,0,.05); padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.markdown-body :deep(code) { font-family: 'Consolas','Monaco','Courier New',monospace; font-size: 13px; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 4px 0; }
.bubble-user .markdown-body :deep(pre) { background: rgba(255,255,255,.15); }
.bubble-user .markdown-body :deep(code) { color: #fff; }

/* Typing */
.typing-indicator { display: flex; align-items: center; gap: 5px; padding: 4px 0; }
.typing-indicator .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #909399; animation: typing-bounce 1.4s infinite both; }
.typing-indicator .dot:nth-child(2) { animation-delay: .2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: .4s; }
@keyframes typing-bounce {
  0%,80%,100% { transform: scale(.6); opacity: .4; }
  40% { transform: scale(1); opacity: 1; }
}
.streaming-cursor { display: inline; color: #409eff; font-weight: 700; animation: blink-cursor .8s infinite; }
@keyframes blink-cursor {
  0%,50% { opacity: 1; }
  51%,100% { opacity: 0; }
}
</style>
