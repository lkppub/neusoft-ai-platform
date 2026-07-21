import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listTemplates, createTemplate, updateTemplate, deleteTemplate,
  useTemplate, renderTemplate,
} from '@/api/templates'

export const useTemplateStore = defineStore('templates', () => {
  const templates = ref([])
  const loading = ref(false)

  const categories = computed(() => {
    const cats = new Set(templates.value.map(t => t.category))
    return [...cats]
  })

  const activeTemplates = computed(() =>
    templates.value.filter(t => t.is_active)
  )

  async function fetchTemplates(category = null, includeInactive = false) {
    loading.value = true
    try {
      templates.value = await listTemplates(category || '', includeInactive)
    } finally {
      loading.value = false
    }
  }

  async function addTemplate(data) {
    const tpl = await createTemplate(data)
    templates.value.unshift(tpl)
    return tpl
  }

  async function editTemplate(id, data) {
    const tpl = await updateTemplate(id, data)
    const idx = templates.value.findIndex(t => t.id === id)
    if (idx !== -1) templates.value[idx] = tpl
    return tpl
  }

  async function removeTemplate(id) {
    await deleteTemplate(id)
    templates.value = templates.value.filter(t => t.id !== id)
  }

  async function useTemplateAction(id) {
    await useTemplate(id)
    const tpl = templates.value.find(t => t.id === id)
    if (tpl) tpl.usage_count += 1
  }

  async function renderTemplateAction(id, ticketId) {
    return await renderTemplate(id, ticketId)
  }

  return {
    templates, loading, categories, activeTemplates,
    fetchTemplates, addTemplate, editTemplate, removeTemplate,
    useTemplateAction, renderTemplateAction,
  }
})
