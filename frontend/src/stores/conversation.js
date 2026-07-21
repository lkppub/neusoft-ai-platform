import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listConversations, createConversation, getConversation,
  deleteConversation, getMessages,
} from '@/api/conversations'
import { useSSE } from '@/composables/useSSE'
import { useAuthStore } from './auth'

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref([])
  const activeConversationId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)
  const streamingContent = ref('')

  const activeConversation = computed(() =>
    conversations.value.find(c => c.id === activeConversationId.value)
  )
  const sortedConversations = computed(() =>
    [...conversations.value].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
  )

  async function fetchConversations(page = 1, pageSize = 20) {
    const res = await listConversations(page, pageSize)
    conversations.value = res.items
    return res
  }

  async function createNewConversation(title = '新对话') {
    const res = await createConversation({ title })
    conversations.value.unshift(res)
    return res
  }

  async function fetchConversation(id) {
    return await getConversation(id)
  }

  async function removeConversation(id) {
    await deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeConversationId.value === id) {
      activeConversationId.value = null
      messages.value = []
    }
  }

  async function fetchMessages(conversationId, page = 1) {
    return await getMessages(conversationId, page)
  }

  async function sendMessage(conversationId, content) {
    const authStore = useAuthStore()
    messages.value.push({
      id: Date.now().toString(),
      conversation_id: conversationId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    })

    isStreaming.value = true
    streamingContent.value = ''
    // Add a placeholder for the assistant message
    const assistantMsgId = (Date.now() + 1).toString()
    messages.value.push({
      id: assistantMsgId,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
    })

    const { streamMessage } = useSSE()
    try {
      const result = await streamMessage(
        `/api/v1/conversations/${conversationId}/messages`,
        { content },
        authStore.accessToken
      )
      // Update the assistant message with final content
      const idx = messages.value.findIndex(m => m.id === assistantMsgId)
      if (idx !== -1) {
        messages.value[idx] = {
          ...messages.value[idx],
          content: result.fullContent,
          isStreaming: false,
        }
      }
      isStreaming.value = false
      // Refresh conversation list
      await fetchConversations()
      return result
    } catch (e) {
      isStreaming.value = false
      // Mark the assistant message as error
      const idx = messages.value.findIndex(m => m.id === assistantMsgId)
      if (idx !== -1) {
        messages.value[idx].content = '抱歉，回复生成失败。请重试。'
        messages.value[idx].isStreaming = false
      }
      throw e
    }
  }

  function setActiveConversation(id) {
    activeConversationId.value = id
  }

  function clearActiveConversation() {
    activeConversationId.value = null
    messages.value = []
  }

  return {
    conversations, activeConversationId, messages, isStreaming, streamingContent,
    activeConversation, sortedConversations,
    fetchConversations, createNewConversation, fetchConversation, removeConversation,
    fetchMessages, sendMessage, setActiveConversation, clearActiveConversation,
  }
})
