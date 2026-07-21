import api from './index'

/**
 * Conversations API module
 */

const BASE = '/conversations'

// List conversations with pagination
export function listConversations(page = 1, pageSize = 20) {
  return api.get(BASE, { params: { page, page_size: pageSize } })
}

// Create a new conversation
export function createConversation(data) {
  return api.post(BASE, data)
}

// Get a single conversation by ID
export function getConversation(id) {
  return api.get(`${BASE}/${id}`)
}

// Delete a conversation
export function deleteConversation(id) {
  return api.delete(`${BASE}/${id}`)
}

// Get messages for a conversation
export function getMessages(id, page = 1, pageSize = 50) {
  return api.get(`${BASE}/${id}/messages`, {
    params: { page, page_size: pageSize }
  })
}

/**
 * Send a message and receive SSE stream response.
 * Returns the fetch Response object so the caller can read the ReadableStream.
 *
 * @param {number|string} conversationId - The conversation ID
 * @param {string} content - The message content
 * @param {object} [options] - Additional options
 * @param {AbortSignal} [options.signal] - AbortSignal for cancellation
 * @returns {Promise<Response>} Fetch Response with a ReadableStream body
 */
export function sendMessage(conversationId, content, options = {}) {
  const token = localStorage.getItem('accessToken')
  const url = `/api/v1${BASE}/${conversationId}/messages`

  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ content }),
    signal: options.signal
  })
}
