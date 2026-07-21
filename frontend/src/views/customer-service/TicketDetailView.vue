<template>
  <div class="ticket-detail-page" v-loading="loading">
    <el-page-header @back="$router.push('/tickets')" :content="ticket?.subject || '工单详情'" />

    <el-row :gutter="20" style="margin-top:20px" v-if="ticket">
      <el-col :span="16">
        <el-card>
          <template #header><span>对话记录</span></template>
          <div class="message-list" ref="msgListRef">
            <div v-for="msg in store.ticketMessages" :key="msg.id" :class="['message-item', msg.message_type === 'agent' ? 'agent' : msg.message_type === 'system' ? 'system' : 'customer']">
              <div class="msg-header"><span class="msg-sender">{{ msg.message_type === 'customer' ? '客户' : msg.message_type === 'agent' ? '客服' : '系统' }}</span><span class="msg-time">{{ formatDate(msg.created_at) }}</span></div>
              <div class="msg-content">{{ msg.content }}</div>
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

      <el-col :span="8">
        <el-card><template #header><span>工单信息</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="状态"><el-tag :type="statusType(ticket.status)">{{ statusMap[ticket.status] }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="优先级"><el-tag :type="priorityType(ticket.priority)">{{ priorityMap[ticket.priority] }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="分类">{{ ticket.problem_category || '未分类' }}</el-descriptions-item>
            <el-descriptions-item label="发布者">{{ ticket.creator_name || '未知用户' }}</el-descriptions-item>
            <el-descriptions-item label="分配客服">{{ ticket.assignee_name || '未分配' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(ticket.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card style="margin-top:16px" v-if="!authStore.isEnterprise">
          <template #header><span>AI辅助</span></template>
          <el-button @click="classify" :loading="classifying" style="width:100%;margin-bottom:8px">🤖 AI分类</el-button>
          <el-button @click="suggestReply" :loading="suggesting" style="width:100%;margin-bottom:8px">💡 AI建议回复</el-button>
          <el-button @click="resolve" :loading="resolving" type="success" style="width:100%" v-if="ticket.status!=='resolved'">✅ 解决工单</el-button>
        </el-card>

        <el-card v-if="!authStore.isEnterprise && ticket.ai_classification" style="margin-top:16px">
          <template #header><span>AI分类结果</span></template>
          <p>分类: {{ ticket.ai_classification.category }}</p>
          <p>情绪: {{ ticket.ai_classification.sentiment }}</p>
          <p>关键信息: {{ ticket.ai_classification.key_details }}</p>
        </el-card>

        <el-card v-if="!authStore.isEnterprise && ticket.ai_suggested_reply" style="margin-top:16px">
          <template #header><span>AI建议回复</span></template>
          <p style="white-space:pre-wrap">{{ ticket.ai_suggested_reply }}</p>
          <p style="color:#999">置信度: {{ (ticket.ai_reply_confidence * 100).toFixed(0) }}%</p>
          <el-button type="primary" size="small" @click="replyText = ticket.ai_suggested_reply">使用此回复</el-button>
          <el-button v-if="!ttsPlaying && !ttsPaused" size="small" @click="playTTS(ticket.ai_suggested_reply)" :icon="Headset">语音播放</el-button>
          <el-button v-if="ttsPlaying" size="small" @click="pauseTTS" :icon="VideoPause">暂停</el-button>
          <el-button v-if="ttsPaused" type="warning" size="small" @click="resumeTTS" :icon="VideoPlay">继续播放</el-button>
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
import VoiceInput from '@/components/voice/VoiceInput.vue'
import { useTTS } from '@/composables/useTTS'

const route = useRoute(); const router = useRouter(); const store = useTicketStore(); const authStore = useAuthStore(); const templateStore = useTemplateStore()
const loading = ref(false); const replyText = ref(''); const sending = ref(false)
const classifying = ref(false); const suggesting = ref(false); const resolving = ref(false)
const selectedTemplate = ref(null); const loadingTemplates = ref(false)
const { play: playTTS, pause: pauseTTS, resume: resumeTTS, stop: stopTTS, isPlaying: ttsPlaying, isPaused: ttsPaused } = useTTS()

const ticket = computed(() => store.ticketDetail)
const statusMap = { open: '待处理', in_progress: '处理中', waiting_customer: '等待客户', resolved: '已解决', closed: '已关闭' }
const priorityMap = { low: '低', medium: '中', high: '高', urgent: '紧急' }
function statusType(s) { return { open: 'danger', in_progress: 'warning', waiting_customer: 'info', resolved: 'success', closed: 'info' }[s] || 'info' }
function priorityType(p) { return { low: 'info', medium: '', high: 'warning', urgent: 'danger' }[p] || '' }
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
async function classify() { classifying.value = true; try { await store.classifyTicketAction(ticket.value.id); ElMessage.success('分类完成') } catch { ElMessage.error('分类失败') } finally { classifying.value = false } }
async function suggestReply() { suggesting.value = true; try { const r = await store.suggestReplyAction(ticket.value.id); replyText.value = r.suggested_reply } catch { ElMessage.error('建议生成失败') } finally { suggesting.value = false } }
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

onMounted(() => { load(); if (!authStore.isEnterprise) templateStore.fetchTemplates() })
onBeforeUnmount(() => { stopTTS() })
</script>

<style scoped>
.message-item { padding: 12px; margin-bottom: 8px; border-radius: 8px; }
.message-item.customer { background: #eff6ff; }
.message-item.agent { background: #f0fdf4; }
.message-item.system { background: #fefce8; text-align: center; }
.msg-header { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; color: #666; }
.msg-content { white-space: pre-wrap; }
.reply-area { margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e7eb; }
.message-list { max-height: 500px; overflow-y: auto; }
</style>
