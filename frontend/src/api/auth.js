import api from './index'

/**
 * Authentication API module
 */

// User login - accepts credentials object { username, password }
export function login(credentials) {
  return api.post('/auth/login', credentials)
}

// User registration
export function register(data) {
  return api.post('/auth/register', data)
}

// Refresh access token
export function refreshToken(refreshToken) {
  return api.post('/auth/refresh', { refresh_token: refreshToken })
}

// Get current user info
export function getMe() {
  return api.get('/auth/me')
}

// Update user profile
export function updateProfile(data) {
  return api.put('/auth/profile', data)
}

// Change password
export function changePassword(oldPassword, newPassword) {
  return api.put('/auth/password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}
