import { ref } from 'vue'

const STATUS_TEXT = {
  analyzing: '🔍 正在分析您的问题...',
  classifying: '📋 正在识别问题类型...',
  retrieving: '📚 正在检索知识库...',
  generating: '✍️ 正在生成回复...',
  checking: '✅ 正在审核回复质量...',
}

const ERROR_MAP = {
  401: '登录已过期，请重新登录',
  429: '请求过于频繁，请稍后再试',
  500: 'AI 服务暂时不可用，请稍后重试',
  502: 'AI 服务正在启动中，请稍后重试',
  503: 'AI 服务繁忙，请稍后重试',
}

function getErrorMessage(status, body) {
  if (ERROR_MAP[status]) return ERROR_MAP[status]
  if (body?.detail) return body.detail
  if (body?.message) return body.message
  return `请求失败 (HTTP ${status})`
}

export function useSSE() {
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const statusMessage = ref('')
  const error = ref(null)

  async function streamMessage(url, body, token) {
    isStreaming.value = true
    streamingContent.value = ''
    statusMessage.value = ''
    error.value = null

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => null)
      throw new Error(getErrorMessage(response.status, errData))
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'token') {
                // Clear status message once streaming begins
                statusMessage.value = ''
                streamingContent.value += data.content
              } else if (data.type === 'status') {
                statusMessage.value = STATUS_TEXT[data.phase] || data.phase
              } else if (data.type === 'done') {
                isStreaming.value = false
                return { fullContent: streamingContent.value, messageId: data.message_id }
              } else if (data.type === 'error') {
                throw new Error(data.message || 'AI 服务返回错误')
              }
            } catch (e) {
              if (e.message && !e.message.includes('JSON')) throw e
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }

    isStreaming.value = false
    return { fullContent: streamingContent.value, messageId: null }
  }

  return { isStreaming, streamingContent, statusMessage, error, streamMessage }
}
