<template>
  <div class="forbidden">
    <div class="forbidden-content">
      <h1>403</h1>
      <p>权限不足</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function goHome() {
  // Redirect to the first accessible page based on role
  const role = authStore.userRole
  if (role === 'customer_service') {
    router.push('/tickets')
  } else if (role === 'decision_maker') {
    router.push('/dashboard')
  } else {
    router.push('/conversations')
  }
}
</script>

<style scoped>
.forbidden {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f7fa;
}
.forbidden-content {
  text-align: center;
}
.forbidden-content h1 {
  font-size: 96px;
  color: #e6a23c;
  margin-bottom: 16px;
}
.forbidden-content p {
  font-size: 18px;
  color: #606266;
  margin-bottom: 32px;
}
</style>
