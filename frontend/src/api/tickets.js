import api from './index'

/**
 * Tickets API module
 */

const BASE = '/tickets'

// List tickets with pagination, filters, search, and sorting
export function listTickets(page = 1, pageSize = 20, status = '', priority = '', category = '', search = '', sortBy = 'updated_at', sortOrder = 'desc') {
  const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
  if (status) params.status = status
  if (priority) params.priority = priority
  if (category) params.category = category
  if (search) params.search = search
  return api.get(BASE, { params })
}

// Create a new ticket
export function createTicket(data) {
  return api.post(BASE, data)
}

// Get a single ticket by ID
export function getTicket(id) {
  return api.get(`${BASE}/${id}`)
}

// Update a ticket
export function updateTicket(id, data) {
  return api.put(`${BASE}/${id}`, data)
}

// Add a message to a ticket
export function addTicketMessage(id, content) {
  return api.post(`${BASE}/${id}/messages`, { content })
}

// Classify a ticket using AI
export function classifyTicket(id) {
  return api.post(`${BASE}/${id}/classify`)
}

// Get AI-suggested reply for a ticket
export function suggestReply(id) {
  return api.post(`${BASE}/${id}/suggest-reply`)
}

// Resolve/close a ticket
export function resolveTicket(id, finalReply) {
  return api.post(`${BASE}/${id}/resolve`, { final_reply: finalReply })
}

// Rate a resolved ticket (1-5)
export function rateTicket(id, rating, comment = '') {
  return api.post(`${BASE}/${id}/rate`, { rating, comment })
}

// Get all messages for a ticket
export function getTicketMessages(id) {
  return api.get(`${BASE}/${id}/messages`)
}
