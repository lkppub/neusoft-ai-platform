<template>
  <el-card shadow="hover" class="stat-card">
    <div class="stat-content">
      <div class="stat-info">
        <p class="stat-label">{{ label }}</p>
        <h3 class="stat-value">
          <span class="counter">{{ displayValue }}</span>
          <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
        </h3>
        <p class="stat-sub">{{ sub }}</p>
      </div>
      <div class="stat-icon" :style="{ background: color }">
        <el-icon :size="28"><component :is="icon" /></el-icon>
      </div>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  displayValue: { type: [String, Number], required: true },
  suffix: { type: String, default: '' },
  sub: { type: String, default: '' },
  icon: { type: Object, required: true },
  color: { type: String, default: '#409eff' },
})
</script>

<style scoped>
.stat-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  transition: border-color 0.3s, transform 0.2s;
}
.stat-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}
.stat-card :deep(.el-card__body) { padding: 20px; }
.stat-content { display: flex; align-items: center; justify-content: space-between; }
.stat-label { font-size: 13px; color: #94a3b8; margin: 0 0 6px; }
.stat-value { font-size: 28px; font-weight: 700; color: #e2e8f0; margin: 0 0 4px; font-variant-numeric: tabular-nums; }
.stat-suffix { font-size: 18px; font-weight: 500; color: #94a3b8; margin-left: 2px; }
.stat-sub { font-size: 12px; color: #64748b; margin: 0; }
.stat-icon { width: 52px; height: 52px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
</style>
