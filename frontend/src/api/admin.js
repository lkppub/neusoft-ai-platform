import api from './index'

/**
 * Admin API module
 */

const BASE = '/admin'

// ─── User Management ───

// List users with pagination and optional role filter
export function listUsers(page = 1, pageSize = 20, role = '') {
  const params = { page, page_size: pageSize }
  if (role) params.role = role
  return api.get(`${BASE}/users`, { params })
}

// Create a new user
export function createUser(data) {
  return api.post(`${BASE}/users`, data)
}

// Update an existing user
export function updateUser(id, data) {
  return api.put(`${BASE}/users/${id}`, data)
}

// Delete a user
export function deleteUser(id) {
  return api.delete(`${BASE}/users/${id}`)
}

// Reset a user's password
export function resetUserPassword(id) {
  return api.post(`${BASE}/users/${id}/reset-password`)
}

// ─── AI Configuration ───

// List all AI configuration entries
export function listAIConfigs() {
  return api.get(`${BASE}/ai/configs`)
}

// Update an AI configuration value
export function updateAIConfig(key, value, description) {
  return api.put(`${BASE}/ai/configs/${key}`, { config_value: value, description })
}

// ─── Prompt Management ───

// List all prompts
export function listPrompts() {
  return api.get(`${BASE}/ai/prompts`)
}

// Create a new prompt
export function createPrompt(data) {
  return api.post(`${BASE}/ai/prompts`, data)
}

// Update an existing prompt
export function updatePrompt(id, data) {
  return api.put(`${BASE}/ai/prompts/${id}`, data)
}

// Delete a prompt
export function deletePrompt(id) {
  return api.delete(`${BASE}/ai/prompts/${id}`)
}

// Test a prompt with variables
export function testPrompt(id, variables) {
  return api.post(`${BASE}/ai/prompts/${id}/test`, { variables })
}

// ─── Conversation Management (Admin) ───

// List all conversations across all users
export function listAllConversations(page = 1, pageSize = 20) {
  return api.get(`${BASE}/conversations`, {
    params: { page, page_size: pageSize }
  })
}

// Get conversation statistics
export function getConversationStats() {
  return api.get(`${BASE}/conversations/stats`)
}

// ─── Reports ───

// List all reports
export function listReports() {
  return api.get(`${BASE}/reports`)
}

// Generate a new report
export function generateReport(type, params = {}) {
  return api.post(`${BASE}/reports/generate`, { type, params })
}

// Get a single report by ID
export function getReport(id) {
  return api.get(`${BASE}/reports/${id}`)
}

// Delete a report
export function deleteReport(id) {
  return api.delete(`${BASE}/reports/${id}`)
}
