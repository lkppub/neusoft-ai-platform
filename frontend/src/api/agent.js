import api from './index'

/**
 * AI Agent API module
 * Supports single-agent chat and multi-agent analysis
 */

const BASE = '/agent'

/**
 * Single-agent chat.
 * Sends a user message along with conversation history and returns the agent's reply.
 *
 * @param {string} message - The user's message
 * @param {Array<{role: string, content: string}>} [history=[]] - Conversation history
 * @returns {Promise} API response with the agent's reply
 */
export function singleAgentChat(message, history = []) {
  return api.post(`${BASE}/chat`, {
    message,
    history
  })
}

/**
 * Multi-agent analysis.
 * Sends input text for analysis by multiple specialized agents.
 *
 * @param {string} inputText - The input text to analyze
 * @returns {Promise} API response with analysis results from multiple agents
 */
export function multiAgentAnalyze(inputText) {
  return api.post(`${BASE}/analyze`, {
    input_text: inputText
  })
}
