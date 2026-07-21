<template>
  <div class="dashboard-layout">
    <div class="dashboard-header">
      <h1 class="dashboard-title">📊 东软智慧商务数据大屏</h1>
      <div class="dashboard-actions">
        <el-tag>{{ currentTime }}</el-tag>
        <el-button text @click="$router.push('/conversations')">返回主页</el-button>
      </div>
    </div>
    <div class="dashboard-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
const currentTime = ref('')
let timer = null
onMounted(() => {
  const update = () => { currentTime.value = new Date().toLocaleString('zh-CN') }
  update(); timer = setInterval(update, 1000)
})
onUnmounted(() => { clearInterval(timer) })
</script>

<style scoped>
.dashboard-layout {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
}
.dashboard-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 32px; border-bottom: 1px solid #334155;
}
.dashboard-title { font-size: 22px; font-weight: 700; margin: 0; }
.dashboard-actions { display: flex; align-items: center; gap: 16px; }
.dashboard-content { padding: 24px 32px; }
</style>
