import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getMe, refreshToken as apiRefreshToken, updateProfile } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('accessToken') || '')
  const refreshTokenVal = ref(localStorage.getItem('refreshToken') || '')
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  const userRole = computed(() => user.value?.role || '')
  const isAdmin = computed(() => userRole.value === 'admin')
  const isCustomerService = computed(() => userRole.value === 'customer_service')
  const isEnterprise = computed(() => userRole.value === 'enterprise')
  const isDecisionMaker = computed(() => userRole.value === 'decision_maker')

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshTokenVal.value = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
  }

  function clearAuth() {
    user.value = null
    accessToken.value = ''
    refreshTokenVal.value = ''
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  async function login(credentials) {
    const res = await apiLogin(credentials)
    setTokens(res.access_token, res.refresh_token)
    await fetchUser()
    return res
  }

  async function register(data) {
    const res = await apiRegister(data)
    return res
  }

  async function fetchUser() {
    try {
      const res = await getMe()
      user.value = res
    } catch (e) {
      clearAuth()
      throw e
    }
  }

  async function refreshAccessToken() {
    if (!refreshTokenVal.value) throw new Error('No refresh token')
    const res = await apiRefreshToken(refreshTokenVal.value)
    setTokens(res.access_token, res.refresh_token)
    return res.access_token
  }

  async function updateUserProfile(data) {
    const res = await updateProfile(data)
    user.value = res
    return res
  }

  function logout() {
    clearAuth()
    router.push('/login')
  }

  return {
    user, accessToken, refreshTokenVal, isAuthenticated,
    userRole, isAdmin, isCustomerService, isEnterprise, isDecisionMaker,
    login, register, fetchUser, refreshAccessToken, updateUserProfile, logout,
    setTokens, clearAuth,
  }
})
