import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { guest: true },
    children: [
      { path: '', name: 'Login', component: () => import('@/views/auth/LoginView.vue') },
    ],
  },
  {
    path: '/register',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { guest: true },
    children: [
      { path: '', name: 'Register', component: () => import('@/views/auth/RegisterView.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/conversations' },
      { path: 'conversations', name: 'Conversations', component: () => import('@/views/enterprise/ConversationView.vue'), meta: { roles: ['enterprise', 'admin', 'customer_service', 'decision_maker'] } },
      { path: 'knowledge', name: 'KnowledgeQuery', component: () => import('@/views/enterprise/KnowledgeQueryView.vue'), meta: { roles: ['enterprise', 'customer_service', 'admin', 'decision_maker'] } },
      { path: 'tickets', name: 'Tickets', component: () => import('@/views/customer-service/TicketListView.vue'), meta: { roles: ['customer_service', 'admin', 'enterprise'] } },
      { path: 'tickets/:id', name: 'TicketDetail', component: () => import('@/views/customer-service/TicketDetailView.vue'), meta: { roles: ['customer_service', 'admin', 'enterprise'] } },
      { path: 'faq', name: 'FAQManagement', component: () => import('@/views/customer-service/FAQManagementView.vue'), meta: { roles: ['customer_service', 'admin'] } },
      { path: 'templates', name: 'Templates', component: () => import('@/views/customer-service/TemplateView.vue'), meta: { roles: ['customer_service', 'admin'] } },
      { path: 'admin/users', name: 'UserManagement', component: () => import('@/views/admin/UserManagementView.vue'), meta: { roles: ['admin'] } },
      { path: 'admin/knowledge', name: 'KnowledgeManagement', component: () => import('@/views/admin/KnowledgeManagementView.vue'), meta: { roles: ['admin'] } },
      { path: 'admin/ai-config', name: 'AIConfig', component: () => import('@/views/admin/AIConfigView.vue'), meta: { roles: ['admin'] } },
      { path: 'admin/conversations', name: 'ConversationRecords', component: () => import('@/views/admin/ConversationRecordsView.vue'), meta: { roles: ['admin'] } },
      { path: 'admin/reports', name: 'Reports', component: () => import('@/views/admin/ReportView.vue'), meta: { roles: ['admin'] } },
      { path: 'profile', name: 'Profile', component: () => import('@/views/enterprise/ProfileView.vue') },
    ],
  },
  {
    path: '/dashboard',
    component: () => import('@/layouts/DashboardLayout.vue'),
    meta: { roles: ['decision_maker', 'admin'] },
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
    ],
  },
  { path: '/403', name: 'Forbidden', component: () => import('@/views/error/ForbiddenView.vue') },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/error/NotFoundView.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  if (authStore.accessToken && !authStore.user) {
    try { await authStore.fetchUser() } catch { authStore.clearAuth() }
  }
  if (to.meta.guest && authStore.isAuthenticated) return next('/conversations')
  if (to.meta.requiresAuth && !authStore.isAuthenticated) return next('/login')
  if (to.meta.roles && !to.meta.roles.includes(authStore.userRole)) return next('/403')
  if (to.path.startsWith('/dashboard') && !['decision_maker', 'admin'].includes(authStore.userRole)) return next('/403')
  next()
})

export default router
