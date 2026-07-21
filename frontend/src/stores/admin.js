import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listUsers, createUser, updateUser, deleteUser, resetUserPassword,
  listAIConfigs, updateAIConfig,
  listPrompts, createPrompt, updatePrompt, deletePrompt, testPrompt,
  listAllConversations, getConversationStats as apiGetConvStats,
  listReports, generateReport, getReport, deleteReport,
} from '@/api/admin'

export const useAdminStore = defineStore('admin', () => {
  const users = ref([]); const usersTotal = ref(0)
  const aiConfigs = ref([])
  const prompts = ref([])
  const reports = ref([])
  const allConversations = ref([]); const convTotal = ref(0)

  async function fetchUsers(page = 1, pageSize = 20, role = null) {
    const res = await listUsers(page, pageSize, role)
    users.value = res.items; usersTotal.value = res.total
  }
  async function addUser(data) { return await createUser(data) }
  async function editUser(id, data) { return await updateUser(id, data) }
  async function removeUser(id) { await deleteUser(id); users.value = users.value.filter(u => u.id !== id) }
  async function resetPassword(id) { return await resetUserPassword(id) }

  async function fetchAIConfigs() { aiConfigs.value = await listAIConfigs() }
  async function editAIConfig(key, value, desc) { return await updateAIConfig(key, value, desc) }

  async function fetchPrompts() { prompts.value = await listPrompts() }
  async function addPrompt(data) { return await createPrompt(data) }
  async function editPrompt(id, data) { return await updatePrompt(id, data) }
  async function removePrompt(id) { await deletePrompt(id); prompts.value = prompts.value.filter(p => p.id !== id) }
  async function testPromptById(id, vars) { return await testPrompt(id, vars) }

  async function fetchAllConversations(page = 1, pageSize = 20) {
    const res = await listAllConversations(page, pageSize)
    allConversations.value = res.items; convTotal.value = res.total
  }
  async function getConvStats() { return await apiGetConvStats() }

  async function fetchReports() { reports.value = await listReports() }
  async function generateNewReport(type, params) { return await generateReport(type, params) }
  async function fetchReport(id) { return await getReport(id) }
  async function removeReport(id) { await deleteReport(id); reports.value = reports.value.filter(r => r.id !== id) }

  return {
    users, usersTotal, aiConfigs, prompts, reports, allConversations, convTotal,
    fetchUsers, addUser, editUser, removeUser, resetPassword,
    fetchAIConfigs, editAIConfig, fetchPrompts, addPrompt, editPrompt, removePrompt, testPromptById,
    fetchAllConversations, getConvStats, fetchReports, generateNewReport, fetchReport, removeReport,
  }
})
