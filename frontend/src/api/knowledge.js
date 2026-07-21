import api from './index'

/**
 * Knowledge Base API module
 */

const BASE = '/knowledge'

// Upload a document to the knowledge base
export function uploadDocument(file, title, chunkSize = 500, chunkOverlap = 50) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', title)
  formData.append('chunk_size', chunkSize)
  formData.append('chunk_overlap', chunkOverlap)

  return api.post(`${BASE}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000 // 2 minutes for large files
  })
}

// List documents with pagination and optional status filter
export function listDocuments(page = 1, pageSize = 20, status = '') {
  const params = { page, page_size: pageSize }
  if (status) params.status = status
  return api.get(`${BASE}/documents`, { params })
}

// Get a single document by ID
export function getDocument(id) {
  return api.get(`${BASE}/documents/${id}`)
}

// Delete a document
export function deleteDocument(id) {
  return api.delete(`${BASE}/documents/${id}`)
}

// Query the knowledge base with semantic search
export function queryKnowledge(question, topK = 5, scoreThreshold = 0.7) {
  return api.post(`${BASE}/query`, {
    question,
    top_k: topK,
    score_threshold: scoreThreshold
  })
}

// List FAQs with pagination, optional category filter, and draft visibility
export function listFAQs(page = 1, pageSize = 20, category = '', includeDrafts = false) {
  const params = { page, page_size: pageSize }
  if (category) params.category = category
  if (includeDrafts) params.include_drafts = true
  return api.get(`${BASE}/faqs`, { params })
}

// Create a new FAQ entry
export function createFAQ(data) {
  return api.post(`${BASE}/faqs`, data)
}

// Update an existing FAQ entry
export function updateFAQ(id, data) {
  return api.put(`${BASE}/faqs/${id}`, data)
}

// Delete an FAQ entry
export function deleteFAQ(id) {
  return api.delete(`${BASE}/faqs/${id}`)
}

// Get a single FAQ by ID (also increments view count)
export function getFAQ(id) {
  return api.get(`${BASE}/faqs/${id}`)
}

// Get all FAQ categories (optionally include unpublished)
export function getFAQCategories(includeDrafts = false) {
  const params = {}
  if (includeDrafts) params.include_drafts = true
  return api.get(`${BASE}/faqs/categories`, { params })
}
