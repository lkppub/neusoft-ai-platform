<template>
  <div class="ticket-detail-page" v-loading="loading">
    <el-page-header @back="$router.push('/tickets')" :content="ticket?.subject || '工单详情'" />

    <el-row :gutter="20" style="margin-top:20px" v-if="ticket">
      <el-col :span="16" class="left-panel">
        <el-card>
          <template #header><span>对话记录</span></template>
          <div class="message-list" ref="msgListRef">
            <div v-for="msg in store.ticketMessages" :key="msg.id" :class="['message-item', msg.message_type === 'agent' ? 'agent' : msg.message_type === 'system' ? 'system' : 'customer']">
              <div class="msg-header"><span class="msg-sender">{{ msg.message_type === 'customer' ? '客户' : msg.message_type === 'agent' ? '客服' : '系统' }}</span><span class="msg-time">{{ formatDate(msg.created_at) }}</span></div>
              <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
            </div>
            <el-empty v-if="store.ticketMessages.length === 0" description="暂无消息" />
          </div>
          <div class="reply-area" v-if="ticket.status !== 'resolved' && ticket.status !== 'closed'">
            <div v-if="!authStore.isEnterprise" style="margin-bottom:8px">
              <el-select v-model="selectedTemplate" placeholder="📋 选择回复模板..." clearable
                @change="onTemplateSelect" style="width:280px" :disabled="loadingTemplates">
                <el-option v-for="tpl in templateStore.activeTemplates" :key="tpl.id"
                  :label="`${tpl.title} (${tpl.category})`" :value="tpl.id" />
              </el-select>
            </div>
            <div style="display:flex;align-items:flex-start;gap:8px">
              <el-input v-model="replyText" type="textarea" :rows="3" placeholder="输入回复或使用语音..." style="flex:1" />
              <VoiceInput @transcribed="onVoiceReplyTranscribed" style="margin-top:2px" />
            </div>
            <el-button type="primary" @click="sendReply" :loading="sending" style="margin-top:8px">发送</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8" class="right-panel">
        <el-card><template #header><span>工单信息</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="状态"><el-tag :type="statusType(ticket.status)">{{ statusMap[ticket.status] }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="优先级"><el-tag :type="priorityType(ticket.priority)">{{ priorityMap[ticket.priority] }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="分类">{{ ticket.problem_category || '未分类' }}</el-descriptions-item>
            <el-descriptions-item label="发布者">{{ ticket.creator_name || '未知用户' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(ticket.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card style="margin-top:12px" v-if="authStore.isEnterprise && ticket.status === 'resolved'">
          <template #header><span>服务评价</span></template>
          <div v-if="ticket.satisfaction_rating" class="rating-done">
            <div class="rating-stars-done">
              <span v-for="i in 5" :key="i" :class="i <= ticket.satisfaction_rating ? 'star active' : 'star'">★</span>
            </div>
            <p v-if="ticket.satisfaction_comment" class="rating-comment">{{ ticket.satisfaction_comment }}</p>
          </div>
          <div v-else class="rating-form">
            <p class="rating-prompt">请为本次服务评分</p>
            <div class="rating-stars">
              <span v-for="i in 5" :key="i"
                :class="i <= ratingValue ? 'star active' : 'star'"
                @click="ratingValue = i"
                style="cursor:pointer;font-size:28px;transition:0.15s;"
              >★</span>
            </div>
            <el-input v-model="ratingComment" placeholder="留言（选填）" size="small" style="margin:8px 0" />
            <el-button type="primary" size="small" :loading="ratingSubmitting" @click="submitRating" style="width:100%">提交评价</el-button>
          </div>
        </el-card>

        <el-card style="margin-top:12px" v-if="!authStore.isEnterprise">
          <template #header><span>AI辅助</span></template>
          <div class="ai-actions">
            <el-button @click="classify" :loading="classifying">🤖 分类</el-button>
            <el-button @click="suggestReply" :loading="suggesting">💡 建议回复</el-button>
            <el-button @click="resolve" :loading="resolving" type="success" v-if="ticket.status!=='resolved'">✅ 解决</el-button>
          </div>

          <!-- AI分类结果 -->
          <div v-if="ticket.ai_classification" class="ai-result">
            <el-divider />
            <div class="ai-result-row"><span class="ai-label">分类</span><span>{{ ticket.ai_classification.category }}</span></div>
            <div class="ai-result-row"><span class="ai-label">情绪</span><span>{{ ticket.ai_classification.sentiment }}</span></div>
            <div class="ai-result-row"><span class="ai-label">摘要</span><span>{{ ticket.ai_classification.key_details }}</span></div>
          </div>

          <!-- AI建议回复 -->
          <div v-if="ticket.ai_suggested_reply" class="ai-result">
            <el-divider />
            <div class="ai-reply-text" v-html="renderMarkdown(ticket.ai_suggested_reply)"></div>
            <p class="ai-confidence">置信度 {{ (ticket.ai_reply_confidence * 100).toFixed(0) }}%</p>
            <div class="ai-reply-actions">
              <el-button type="primary" size="small" @click="replyText = ticket.ai_suggested_reply">使用此回复</el-button>
              <el-button v-if="!ttsPlaying" size="small" @click="playTTS(ticket.ai_suggested_reply)" :icon="Headset">播放</el-button>
              <el-button v-if="ttsPlaying" size="small" @click="pauseTTS" :icon="VideoPause">暂停</el-button>
              <el-button v-if="ttsPaused" type="warning" size="small" @click="resumeTTS" :icon="VideoPlay">继续</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTicketStore } from '@/stores/ticket'
import { useAuthStore } from '@/stores/auth'
import { useTemplateStore } from '@/stores/templates'
import { ElMessage } from 'element-plus'
import { Headset, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { marked } from 'marked'
import VoiceInput from '@/components/voice/VoiceInput.vue'
import { useTTS } from '@/composables/useTTS'

const route = useRoute(); const router = useRouter(); const store = useTicketStore(); const authStore = useAuthStore(); const templateStore = useTemplateStore()
const loading = ref(false); const replyText = ref(''); const sending = ref(false)
const classifying = ref(false); const suggesting = ref(false); const resolving = ref(false)
const selectedTemplate = ref(null); const loadingTemplates = ref(false)
const ratingValue = ref(0); const ratingComment = ref(''); const ratingSubmitting = ref(false)
const { play: playTTS, pause: pauseTTS, resume: resumeTTS, stop: stopTTS, isPlaying: ttsPlaying, isPaused: ttsPaused } = useTTS()

function renderMarkdown(text) {
  if (!text) return ''
  return marked(text, { breaks: true })
}

const ticket = computed(() => store.ticketDetail)
const statusMap = { open: '待处理', in_progress: '处理中', waiting_customer: '等待客户', resolved: '已解决', closed: '已关闭' }
const priorityMap = { low: '低', medium: '中', high: '高', urgent: '紧急' }
function statusType(s) { return { open: 'danger', in_progress: 'warning', waiting_customer: 'info', resolved: 'success', closed: 'info' }[s] || 'info' }
function priorityType(p) { return { low: 'info', medium: 'info', high: 'warning', urgent: 'danger' }[p] || 'info' }
function formatDate(d) { if (!d) return ''; return new Date(d).toLocaleString('zh-CN') }

async function load() {
  loading.value = true
  try {
    await store.fetchTicketDetail(route.params.id)
    await store.fetchMessages(route.params.id)
  } finally { loading.value = false }
}
async function sendReply() {
  if (!replyText.value.trim()) return
  sending.value = true
  try { await store.addMessage(ticket.value.id, replyText.value); replyText.value = ''; await store.fetchMessages(route.params.id) }
  catch { ElMessage.error('发送失败') }
  finally { sending.value = false }
}
async function classify() { classifying.value = true; try { await store.classifyTicketAction(ticket.value.id); await load(); ElMessage.success('分类完成') } catch { ElMessage.error('分类失败') } finally { classifying.value = false } }
async function suggestReply() { suggesting.value = true; try { const r = await store.suggestReplyAction(ticket.value.id); replyText.value = r.suggested_reply; await load() } catch { ElMessage.error('建议生成失败') } finally { suggesting.value = false } }
async function resolve() { resolving.value = true; try { await store.resolveTicketAction(ticket.value.id, replyText.value || ticket.value.ai_suggested_reply || '已解决'); ElMessage.success('工单已解决') } catch { ElMessage.error('操作失败') } finally { resolving.value = false } }

async function onTemplateSelect(tplId) {
  if (!tplId) return
  try {
    const result = await templateStore.renderTemplateAction(tplId, ticket.value.id)
    replyText.value = result.content
    templateStore.useTemplateAction(tplId)
    selectedTemplate.value = null  // reset selector
    ElMessage.success('模板已应用')
  } catch {
    ElMessage.error('模板加载失败')
  }
}

function onVoiceReplyTranscribed(text) {
  replyText.value = replyText.value ? replyText.value + ' ' + text : text
}

async function submitRating() {
  if (!ratingValue.value) return ElMessage.warning('请选择评分')
  ratingSubmitting.value = true
  try {
    await store.rateTicketAction(ticket.value.id, ratingValue.value, ratingComment.value)
    ElMessage.success('评价已提交')
    ticket.value.satisfaction_rating = ratingValue.value
    ticket.value.satisfaction_comment = ratingComment.value
  } catch { ElMessage.error('评价提交失败') }
  finally { ratingSubmitting.value = false }
}

onMounted(() => { load(); if (!authStore.isEnterprise) templateStore.fetchTemplates() })
onBeforeUnmount(() => { stopTTS() })
</script>

<style scoped>
.ai-actions {
  display: flex;
  gap: 8px;
}
.ai-actions .el-button {
  flex: 1;
}

.ai-result {
  margin-top: 4px;
}

.ai-result-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.8;
}
.ai-label {
  color: #909399;
  flex-shrink: 0;
  min-width: 32px;
}

.ai-reply-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  max-height: 160px;
  overflow-y: auto;
  margin: 0 0 4px 0;
}

.ai-confidence {
  color: #999;
  font-size: 12px;
  margin: 0 0 8px 0;
}

.ai-reply-actions {
  display: flex;
  gap: 6px;
}

/* ── 评分 ── */
.rating-form { text-align: center; }
.rating-prompt { font-size: 14px; color: #606266; margin: 0 0 8px 0; }
.rating-stars { display: flex; justify-content: center; gap: 4px; }
.rating-stars .star { color: #c0c4cc; transition: 0.15s; }
.rating-stars .star.active { color: #f7ba2a; }
.rating-stars .star:hover { color: #f7ba2a; transform: scale(1.15); }

.rating-done { text-align: center; }
.rating-stars-done { font-size: 20px; }
.rating-stars-done .star { color: #c0c4cc; }
.rating-stars-done .star.active { color: #f7ba2a; }
.rating-comment { font-size: 13px; color: #909399; margin: 8px 0 0 0; }

.ticket-detail-page {
  height: calc(100vh - 60px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

:deep(.el-page-header) { flex-shrink: 0; }

.ticket-detail-page > .el-row {
  flex: 1;
  overflow: hidden;
  margin-top: 12px !important;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}

.right-panel .el-card { flex-shrink: 0; }

.left-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.left-panel > .el-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel .message-list {
  flex: 1;
  overflow-y: auto;
  max-height: none;
}

.left-panel .reply-area {
  flex-shrink: 0;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.message-item { padding: 12px; margin-bottom: 8px; border-radius: 8px; }
.message-item.customer { background: #eff6ff; }
.message-item.agent { background: #f0fdf4; }
.message-item.system { background: #fefce8; text-align: center; }
.msg-header { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; color: #666; }
.msg-content { white-space: pre-wrap; }
</style>
