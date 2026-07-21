import axios from 'axios'
import { ElMessage } from 'element-plus'

// Token refresh state management
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  failedQueue = []
}

// Create axios instance
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle 401 and token refresh
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config

    // If the error is not 401, or it's a login/register/refresh request, reject immediately
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url === '/auth/login' ||
      originalRequest.url === '/auth/register' ||
      originalRequest.url === '/auth/refresh'
    ) {
      // Extract error message from response
      const message =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        '网络请求失败，请稍后再试'

      // Don't show silent requests (optional flag)
      if (!originalRequest?.silent) {
        ElMessage.error(message)
      }

      return Promise.reject(error)
    }

    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
        .catch((err) => {
          return Promise.reject(err)
        })
    }

    originalRequest._retry = true
    isRefreshing = true

    const refreshTokenValue = localStorage.getItem('refreshToken')

    if (!refreshTokenValue) {
      // No refresh token, redirect to login
      isRefreshing = false
      handleForceLogout('登录已过期，请重新登录')
      return Promise.reject(error)
    }

    try {
      const response = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshTokenValue
      })

      const { access_token, refresh_token: newRefreshToken } = response.data

      // Store new tokens
      localStorage.setItem('accessToken', access_token)
      if (newRefreshToken) {
        localStorage.setItem('refreshToken', newRefreshToken)
      }

      // Update authorization header for the original request
      originalRequest.headers.Authorization = `Bearer ${access_token}`

      // Process queued requests
      processQueue(null, access_token)

      // Retry the original request
      return api(originalRequest)
    } catch (refreshError) {
      // Refresh failed - log out
      processQueue(refreshError, null)
      handleForceLogout('登录已过期，请重新登录')
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

/**
 * Force logout - clear tokens and redirect to login
 */
function handleForceLogout(message) {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
  localStorage.removeItem('user')

  // Avoid showing duplicate messages for simultaneous failed requests
  if (!handleForceLogout._showing) {
    handleForceLogout._showing = true
    ElMessage.warning(message)

    // Use setTimeout to allow other interceptors to finish before redirect
    setTimeout(() => {
      handleForceLogout._showing = false
      const currentPath = window.location.pathname
      if (currentPath !== '/login') {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
      }
    }, 100)
  }
}

export default api
