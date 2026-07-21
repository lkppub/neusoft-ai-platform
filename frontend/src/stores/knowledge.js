import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  uploadDocument, listDocuments, getDocument, deleteDocument,
  queryKnowledge as apiQueryKnowledge,
  listFAQs, createFAQ, updateFAQ, deleteFAQ, getFAQ, getFAQCategories,
} from '@/api/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref([])
  const faqs = ref([])
  const faqsTotal = ref(0)
  const allCategories = ref([])  // 独立存储全部分类，不受当前筛选影响
  const searchResults = ref(null)
  const isSearching = ref(false)
  const documentsTotal = ref(0)

  const readyDocuments = computed(() => documents.value.filter(d => d.status === 'ready'))
  const documentsByType = computed(() => {
    const grouped = {}
    documents.value.forEach(d => {
      const type = d.file_type || 'unknown'
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(d)
    })
    return grouped
  })
  const faqCategories = computed(() => {
    const cats = new Set(faqs.value.map(f => f.category))
    return [...cats]
  })

  async function uploadDocumentFile(file, title = '', chunkSize = 500, chunkOverlap = 50) {
    return await uploadDocument(file, title || file.name, chunkSize, chunkOverlap)
  }

  async function fetchDocuments(page = 1, pageSize = 20, status = null) {
    const res = await listDocuments(page, pageSize, status)
    documents.value = res.items
    documentsTotal.value = res.total
  }

  async function fetchDocument(id) {
    return await getDocument(id)
  }

  async function removeDocument(id) {
    await deleteDocument(id)
    documents.value = documents.value.filter(d => d.id !== id)
  }

  async function queryKnowledge(question, topK = 5, scoreThreshold = 0.5) {
    isSearching.value = true
    try {
      const res = await apiQueryKnowledge(question, topK, scoreThreshold)
      searchResults.value = res
      return res
    } finally {
      isSearching.value = false
    }
  }

  async function fetchFAQs(page = 1, pageSize = 20, category = null, includeDrafts = true) {
    const res = await listFAQs(page, pageSize, category, includeDrafts)
    faqs.value = res.items
    faqsTotal.value = res.total
    return res
  }

  async function fetchFAQ(id) {
    return await getFAQ(id)
  }

  async function addFAQ(data) {
    const faq = await createFAQ(data)
    faqs.value.unshift(faq)
    return faq
  }

  async function editFAQ(id, data) {
    const faq = await updateFAQ(id, data)
    const idx = faqs.value.findIndex(f => f.id === id)
    if (idx !== -1) faqs.value[idx] = faq
    return faq
  }

  async function removeFAQ(id) {
    await deleteFAQ(id)
    faqs.value = faqs.value.filter(f => f.id !== id)
  }

  async function fetchFAQCategoriesList() {
    return await getFAQCategories()
  }

  // 加载全部分类（不受当前 faq 筛选影响）
  async function fetchAllCategories() {
    try {
      const cats = await getFAQCategories(true)
      allCategories.value = cats.map(c => c.category)
    } catch {
      allCategories.value = []
    }
  }

  return {
    documents, faqs, faqsTotal, allCategories, searchResults, isSearching, documentsTotal,
    readyDocuments, documentsByType, faqCategories,
    uploadDocumentFile, fetchDocuments, fetchDocument, removeDocument,
    queryKnowledge, fetchFAQs, fetchFAQ, addFAQ, editFAQ, removeFAQ, fetchFAQCategoriesList,
    fetchAllCategories,
  }
})
