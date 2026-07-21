import api from './index'

/**
 * Response Templates API module
 */

const BASE = '/templates'

// List templates with optional category filter and inactive visibility
export function listTemplates(category = '', includeInactive = false) {
  const params = {}
  if (category) params.category = category
  if (includeInactive) params.include_inactive = true
  return api.get(BASE, { params })
}

// Create a new template
export function createTemplate(data) {
  return api.post(BASE, data)
}

// Update an existing template
export function updateTemplate(id, data) {
  return api.put(`${BASE}/${id}`, data)
}

// Delete a template
export function deleteTemplate(id) {
  return api.delete(`${BASE}/${id}`)
}

// Increment usage count when a template is used
export function useTemplate(id) {
  return api.post(`${BASE}/${id}/use`)
}

// Render template with ticket context (variable replacement)
export function renderTemplate(id, ticketId) {
  return api.get(`${BASE}/${id}/render`, { params: { ticket_id: ticketId } })
}
