<template>
  <el-container class="default-layout">
    <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="app-sidebar">
      <div class="sidebar-header">
        <span v-if="!sidebarCollapsed" class="sidebar-logo">🏢 东软AI</span>
        <span v-else class="sidebar-logo-collapsed">🏢</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="sidebarCollapsed"
        :router="true"
        background-color="#1f2937"
        text-color="#c9d1d9"
        active-text-color="#60a5fa"
      >
        <!-- AI Assistant (all roles) -->
        <template v-if="isEnterprise || isAdmin || isCustomerService || isDecisionMaker">
          <el-menu-item index="/conversations">
            <el-icon><ChatDotSquare /></el-icon>
            <span>AI对话助手</span>
          </el-menu-item>
          <el-menu-item index="/knowledge">
            <el-icon><Collection /></el-icon>
            <span>知识库问答</span>
          </el-menu-item>
        </template>

        <!-- Customer Service -->
        <template v-if="isCustomerService || isAdmin">
          <el-menu-item index="/tickets">
            <el-icon><Tickets /></el-icon>
            <span>工单管理</span>
          </el-menu-item>
          <el-menu-item index="/faq">
            <el-icon><EditPen /></el-icon>
            <span>FAQ管理</span>
          </el-menu-item>
          <el-menu-item index="/templates">
            <el-icon><Document /></el-icon>
            <span>回复模板</span>
          </el-menu-item>
        </template>

        <!-- Enterprise tickets (view own) -->
        <template v-if="isEnterprise && !isAdmin && !isCustomerService">
          <el-menu-item index="/tickets">
            <el-icon><Tickets /></el-icon>
            <span>我的工单</span>
          </el-menu-item>
        </template>

        <!-- Admin -->
        <template v-if="isAdmin">
          <el-sub-menu index="admin">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/admin/users">用户管理</el-menu-item>
            <el-menu-item index="/admin/knowledge">知识库管理</el-menu-item>
            <el-menu-item index="/admin/ai-config">AI配置管理</el-menu-item>
            <el-menu-item index="/admin/conversations">对话记录</el-menu-item>
            <el-menu-item index="/admin/reports">分析报告</el-menu-item>
          </el-sub-menu>
        </template>

        <!-- Dashboard link -->
        <template v-if="isDecisionMaker || isAdmin">
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据大屏</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-button @click="toggleSidebar" :icon="Fold" text />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute">{{ currentRoute }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click">
            <span class="user-info">
              <el-avatar :size="32">{{ user?.full_name?.charAt(0) || user?.username?.charAt(0) || 'U' }}</el-avatar>
              <span class="user-name">{{ user?.full_name || user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/profile')">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { Fold } from '@element-plus/icons-vue'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

const user = computed(() => authStore.user)
const isAdmin = computed(() => authStore.isAdmin)
const isCustomerService = computed(() => authStore.isCustomerService)
const isEnterprise = computed(() => authStore.isEnterprise)
const isDecisionMaker = computed(() => authStore.isDecisionMaker)
const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/admin')) return path
  if (path.startsWith('/tickets/')) return '/tickets'
  return path
})

const routeTitleMap = {
  '/conversations': 'AI对话助手', '/knowledge': '知识库问答',
  '/tickets': '工单管理', '/faq': 'FAQ管理', '/templates': '回复模板',
  '/admin/users': '用户管理', '/admin/knowledge': '知识库管理',
  '/admin/ai-config': 'AI配置', '/admin/conversations': '对话记录',
  '/admin/reports': '分析报告', '/profile': '个人中心',
  '/dashboard': '数据大屏',
}
const currentRoute = computed(() => routeTitleMap[route.path] || route.matched[1]?.meta?.title || '')

function toggleSidebar() { appStore.toggleSidebar() }
function handleLogout() { authStore.logout() }
</script>

<style scoped>
.default-layout { height: 100vh; }
.app-sidebar {
  background-color: #1f2937;
  overflow-y: auto;
  transition: width 0.3s;
}
.sidebar-header {
  height: 60px; display: flex; align-items: center; justify-content: center;
  border-bottom: 1px solid #374151;
}
.sidebar-logo { color: #fff; font-size: 16px; font-weight: 700; white-space: nowrap; }
.sidebar-logo-collapsed { font-size: 24px; }
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #e5e7eb; height: 60px; padding: 0 20px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; }
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.user-name { font-size: 14px; color: #374151; }
.app-main { background: #f3f4f6; padding: 24px; overflow-y: auto; }
</style>
