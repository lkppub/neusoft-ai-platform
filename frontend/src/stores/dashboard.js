import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getOverview, getCategories, getSatisfactionTrend,
  getVolumeTrend, getInsights, getHotTopics, getRealtime,
} from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref(null)
  const categories = ref([])
  const satisfaction = ref([])
  const volume = ref([])
  const insights = ref([])
  const hotTopics = ref([])
  const realtime = ref(null)
  let pollingTimer = null

  async function fetchOverview() { overview.value = await getOverview() }
  async function fetchCategories() { categories.value = await getCategories() }
  async function fetchSatisfaction(days = 7) { satisfaction.value = await getSatisfactionTrend(days) }
  async function fetchVolume(days = 7) { volume.value = await getVolumeTrend(days) }
  async function fetchInsights() { insights.value = await getInsights() }
  async function fetchHotTopics() { hotTopics.value = await getHotTopics() }
  async function fetchRealtime() { realtime.value = await getRealtime() }

  async function fetchAll() {
    await Promise.all([
      fetchOverview(), fetchCategories(), fetchSatisfaction(),
      fetchVolume(), fetchInsights(), fetchHotTopics(), fetchRealtime(),
    ])
  }

  function startPolling(intervalMs = 30000) {
    stopPolling()
    pollingTimer = setInterval(() => {
      fetchOverview(); fetchRealtime()
    }, intervalMs)
  }

  function stopPolling() {
    if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
  }

  return {
    overview, categories, satisfaction, volume, insights, hotTopics, realtime,
    fetchOverview, fetchCategories, fetchSatisfaction, fetchVolume,
    fetchInsights, fetchHotTopics, fetchRealtime, fetchAll,
    startPolling, stopPolling,
  }
})
