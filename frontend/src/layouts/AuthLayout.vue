<template>
  <div class="auth-layout">
    <div class="auth-container">
      <div class="auth-header">
        <h1 class="auth-title">东软智慧商务AI助手平台</h1>
        <p class="auth-subtitle">企业级AI智能应用平台</p>
      </div>
      <div class="auth-card">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.auth-container {
  width: 100%;
  max-width: 440px;
  padding: 20px;
}
.auth-header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
}
.auth-title { font-size: 24px; font-weight: 700; margin: 0 0 8px; }
.auth-subtitle { font-size: 14px; opacity: 0.85; margin: 0; }
.auth-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
</style>
