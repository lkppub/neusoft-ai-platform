import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listTickets, createTicket, getTicket, updateTicket,
  addTicketMessage, classifyTicket, suggestReply, resolveTicket, rateTicket, getTicketMessages,
} from '@/api/tickets'

export const useTicketStore = defineStore('ticket', () => {
  const tickets = ref([])
  const activeTicketId = ref(null)
  const ticketDetail = ref(null)
  const ticketMessages = ref([])
  const filters = ref({ status: '', priority: '', category: '', search: '', sortBy: 'updated_at', sortOrder: 'desc' })
  const ticketsTotal = ref(0)

  const activeTicket = computed(() => ticketDetail.value)
  const filteredTickets = computed(() => tickets.value)
  const ticketStats = computed(() => {
    const stats = { open: 0, in_progress: 0, waiting_customer: 0, resolved: 0, closed: 0 }
    tickets.value.forEach(t => {
      if (stats[t.status] !== undefined) stats[t.status]++
    })
    return stats
  })

  async function fetchTickets(page = 1, pageSize = 20) {
    const f = filters.value
    const res = await listTickets(page, pageSize, f.status, f.priority, f.category, f.search, f.sortBy, f.sortOrder)
    tickets.value = res.items
    ticketsTotal.value = res.total
    return res
  }

  async function createNewTicket(data) {
    return await createTicket(data)
  }

  async function fetchTicketDetail(id) {
    ticketDetail.value = await getTicket(id)
    activeTicketId.value = id
    return ticketDetail.value
  }

  async function updateTicketInfo(id, data) {
    const updated = await updateTicket(id, data)
    ticketDetail.value = updated
    const idx = tickets.value.findIndex(t => t.id === id)
    if (idx !== -1) tickets.value[idx] = updated
    return updated
  }

  async function addMessage(ticketId, content) {
    const msg = await addTicketMessage(ticketId, content)
    ticketMessages.value.push(msg)
    return msg
  }

  async function classifyTicketAction(id) {
    const result = await classifyTicket(id)
    if (ticketDetail.value && ticketDetail.value.id === id) {
      ticketDetail.value.problem_category = result.category
      ticketDetail.value.ai_classification = result
      ticketDetail.value.priority = result.priority
    }
    return result
  }

  async function suggestReplyAction(id) {
    const result = await suggestReply(id)
    if (ticketDetail.value && ticketDetail.value.id === id) {
      ticketDetail.value.ai_suggested_reply = result.suggested_reply
      ticketDetail.value.ai_reply_confidence = result.confidence
    }
    return result
  }

  async function resolveTicketAction(id, finalReply) {
    await resolveTicket(id, finalReply)
    if (ticketDetail.value && ticketDetail.value.id === id) {
      ticketDetail.value.status = 'resolved'
      ticketDetail.value.final_reply = finalReply
    }
  }

  async function rateTicketAction(id, rating, comment = '') {
    await rateTicket(id, rating, comment)
    if (ticketDetail.value && ticketDetail.value.id === id) {
      ticketDetail.value.satisfaction_rating = rating
      ticketDetail.value.satisfaction_comment = comment
    }
  }

  async function fetchMessages(ticketId) {
    ticketMessages.value = await getTicketMessages(ticketId)
    return ticketMessages.value
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  return {
    tickets, activeTicketId, ticketDetail, ticketMessages, filters, ticketsTotal,
    activeTicket, filteredTickets, ticketStats,
    fetchTickets, createNewTicket, fetchTicketDetail, updateTicketInfo,
    addMessage, classifyTicketAction, suggestReplyAction, resolveTicketAction, rateTicketAction,
    fetchMessages, setFilters,
  }
})
