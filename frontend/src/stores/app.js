import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref(localStorage.getItem('app-theme') || 'light')
  const globalLoading = ref(false)
  const breadcrumbs = ref([])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(t) {
    theme.value = t
    localStorage.setItem('app-theme', t)
    document.documentElement.setAttribute('data-theme', t)
  }

  function setLoading(val) {
    globalLoading.value = val
  }

  function setBreadcrumbs(items) {
    breadcrumbs.value = items
  }

  return {
    sidebarCollapsed, theme, globalLoading, breadcrumbs,
    toggleSidebar, setTheme, setLoading, setBreadcrumbs,
  }
})
