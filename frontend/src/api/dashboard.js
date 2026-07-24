import api from './index'

/**
 * Dashboard API module
 */

const BASE = '/dashboard'

// Get dashboard overview statistics
export function getOverview() {
  return api.get(`${BASE}/overview`)
}

// Get ticket category distribution
export function getCategories() {
  return api.get(`${BASE}/categories`)
}

// Get customer satisfaction trend over a number of days
export function getSatisfactionTrend(days = 30) {
  return api.get(`${BASE}/satisfaction`, { params: { days } })
}

// Get ticket volume trend over a number of days
export function getVolumeTrend(days = 30) {
  return api.get(`${BASE}/volume`, { params: { days } })
}

// Get AI-generated insights
export function getInsights() {
  return api.get(`${BASE}/insights`)
}

// Get hot topics / trending issues
export function getHotTopics() {
  return api.get(`${BASE}/hot-topics`)
}

// Get real-time dashboard data
export function getRealtime() {
  return api.get(`${BASE}/realtime`)
}
