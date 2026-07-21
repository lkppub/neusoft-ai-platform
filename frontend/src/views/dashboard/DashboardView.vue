<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>数据大屏</h2>
      <el-tag size="large" type="info">{{ currentTime }}</el-tag>
    </div>

    <!-- Top row: 4 StatsCard components -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :lg="6" v-for="stat in statCards" :key="stat.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <p class="stat-label">{{ stat.label }}</p>
              <h3 class="stat-value">
                <span class="counter">{{ stat.displayValue }}</span>
                <span v-if="stat.suffix" class="stat-suffix">{{ stat.suffix }}</span>
              </h3>
              <p class="stat-sub">{{ stat.sub }}</p>
            </div>
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon :size="28"><component :is="stat.icon" /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Middle row: CategoryPieChart (left 50%) + SatisfactionTrend line chart (right 50%) -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="chart-card">
          <template #header><span>问题分类分布</span></template>
          <div v-if="!hasCategoryData" class="chart-empty">
            <el-empty description="暂无分类数据" :image-size="80" />
          </div>
          <div ref="pieChartRef" class="chart-box" v-show="hasCategoryData"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="chart-card">
          <template #header><span>满意度趋势（近30天）</span></template>
          <div v-if="!hasSatisfactionData" class="chart-empty">
            <el-empty description="暂无满意度数据" :image-size="80" />
          </div>
          <div ref="lineChartRef" class="chart-box" v-show="hasSatisfactionData"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Bottom row: 4 InsightCards -->
    <el-row :gutter="20" class="insights-row">
      <el-col :xs="24" :sm="12" :lg="6" v-for="(card, idx) in insightCards" :key="idx">
        <el-card shadow="hover" class="insight-card">
          <div class="insight-card-inner">
            <div class="insight-icon" :style="{ background: card.color }">
              <el-icon :size="22"><component :is="card.icon" /></el-icon>
            </div>
            <div class="insight-body">
              <p class="insight-title">{{ card.title }}</p>
              <p class="insight-desc">{{ card.description }}</p>
              <p class="insight-meta">{{ card.meta }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useDashboardStore } from '@/stores/dashboard'
import { Document, ChatDotRound, CircleCheck, Star, TrendCharts, DataAnalysis, Platform, Opportunity } from '@element-plus/icons-vue'

const store = useDashboardStore()

// ---- Clock ----
const currentTime = ref('')
let timeTimer = null

function updateClock() {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

// ---- Animated counter ----
const animated = ref({
  inquiries: 0,
  tickets: 0,
  resolution: 0,
  satisfaction: 0
})

function animateValue(key, target, duration = 800) {
  const start = animated.value[key]
  if (start === target) {
    animated.value[key] = target
    return
  }
  const startTime = performance.now()
  function step(now) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    // easeOutCubic
    const eased = 1 - Math.pow(1 - progress, 3)
    const current = start + (target - start) * eased
    if (key === 'resolution' || key === 'satisfaction') {
      animated.value[key] = Math.round(current * 10) / 10
    } else {
      animated.value[key] = Math.round(current)
    }
    if (progress < 1) {
      requestAnimationFrame(step)
    } else {
      animated.value[key] = target
    }
  }
  requestAnimationFrame(step)
}

function triggerAnimations(overview) {
  if (!overview) return
  animateValue('inquiries', overview.total_inquiries ?? overview.totalInquiries ?? overview.inquiries ?? 0)
  animateValue('tickets', overview.total_tickets ?? overview.totalTickets ?? overview.today_tickets ?? overview.tickets ?? 0)
  animateValue('resolution', overview.resolution_rate ?? overview.resolutionRate ?? overview.rate ?? overview.resolved_rate ?? 0)
  animateValue('satisfaction', overview.satisfaction_score ?? overview.satisfactionScore ?? overview.satisfaction_rate ?? 0)
}

// ---- Stat cards ----
const statCards = computed(() => [
  {
    label: '总咨询量',
    displayValue: animated.value.inquiries.toLocaleString(),
    sub: '累计咨询总数',
    icon: ChatDotRound,
    color: '#409eff',
    suffix: ''
  },
  {
    label: '总工单数',
    displayValue: animated.value.tickets.toLocaleString(),
    sub: '累计工单总数',
    icon: Document,
    color: '#67c23a',
    suffix: ''
  },
  {
    label: '解决率',
    displayValue: animated.value.resolution,
    sub: '工单解决比例',
    icon: CircleCheck,
    color: '#e6a23c',
    suffix: '%'
  },
  {
    label: '满意度评分',
    displayValue: animated.value.satisfaction,
    sub: '客户满意度均分',
    icon: Star,
    color: '#f56c6c',
    suffix: '%'
  }
])

// ---- Category Pie Chart ----
const pieChartRef = ref(null)
const lineChartRef = ref(null)
let pieChartInstance = null
let lineChartInstance = null

const hasCategoryData = computed(() => {
  const cat = store.categories
  if (!cat) return false
  if (Array.isArray(cat)) return cat.length > 0
  if (cat.values && Array.isArray(cat.values)) return cat.values.length > 0
  return false
})

const hasSatisfactionData = computed(() => {
  const sat = store.satisfaction
  if (!sat) return false
  if (Array.isArray(sat)) return sat.length > 0
  if (sat.values && Array.isArray(sat.values)) return sat.values.length > 0
  if (sat.dates && Array.isArray(sat.dates)) return sat.dates.length > 0
  return false
})

function getCategoryChartData() {
  const cat = store.categories
  if (!cat) return []
  // Array of { name, value } or { label, count }
  if (Array.isArray(cat)) {
    return cat.map(c => ({
      name: c.name ?? c.label ?? c.topic ?? '未知',
      value: c.value ?? c.count ?? c.total ?? 0
    }))
  }
  // Object with names + values arrays
  if (cat.names && cat.values) {
    return cat.names.map((name, i) => ({
      name,
      value: cat.values[i] ?? 0
    }))
  }
  return []
}

function getSatisfactionChartData() {
  const sat = store.satisfaction
  if (!sat) return { dates: [], values: [] }
  if (sat.dates && sat.values) return { dates: sat.dates, values: sat.values }
  if (sat.labels && sat.data) return { dates: sat.labels, values: sat.data }
  if (Array.isArray(sat)) {
    return {
      dates: sat.map(s => s.date ?? s.label ?? s.month ?? ''),
      values: sat.map(s => s.value ?? s.score ?? s.rate ?? 0)
    }
  }
  return { dates: [], values: [] }
}

function initPieChart() {
  if (!pieChartRef.value) return
  if (pieChartInstance) pieChartInstance.dispose()

  const rawData = getCategoryChartData()
  if (rawData.length === 0) return

  pieChartInstance = echarts.init(pieChartRef.value, 'dark')
  pieChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(20,25,40,0.92)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#94a3b8', fontSize: 12 }
    },
    series: [{
      type: 'pie',
      radius: ['48%', '78%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#1a202c',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' },
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,0.5)' }
      },
      data: rawData
    }]
  })
}

function initLineChart() {
  if (!lineChartRef.value) return
  if (lineChartInstance) lineChartInstance.dispose()

  const { dates, values } = getSatisfactionChartData()
  if (dates.length === 0) return

  lineChartInstance = echarts.init(lineChartRef.value, 'dark')
  lineChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(20,25,40,0.92)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
      formatter: (params) => {
        const p = params[0]
        return `${p.axisValue}<br/>满意度: <b>${p.value}%</b>`
      }
    },
    grid: { left: '3%', right: '4%', top: '8%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#4a5568' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#94a3b8', formatter: '{value}%' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#48bb78', width: 3 },
      itemStyle: { color: '#48bb78' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(72,187,120,0.35)' },
          { offset: 1, color: 'rgba(72,187,120,0.02)' }
        ])
      }
    }]
  })
}

// ---- Insight cards ----
const insightIcons = [DataAnalysis, Platform, TrendCharts, Opportunity]
const insightColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c']

const insightCards = computed(() => {
  const raw = store.insights
  let items = []
  if (Array.isArray(raw)) {
    items = raw
  } else if (raw && typeof raw === 'object') {
    items = raw.insights ?? raw.items ?? raw.list ?? []
  }

  const defaults = [
    { title: '暂无洞察', description: '数据收集中...', meta: '' },
    { title: '暂无洞察', description: '数据收集中...', meta: '' },
    { title: '暂无洞察', description: '数据收集中...', meta: '' },
    { title: '暂无洞察', description: '数据收集中...', meta: '' }
  ]

  return defaults.map((def, i) => {
    const item = items[i]
    if (!item) {
      return {
        ...def,
        icon: insightIcons[i],
        color: insightColors[i]
      }
    }
    if (typeof item === 'string') {
      return {
        title: item.length > 20 ? item.slice(0, 20) + '...' : item,
        description: item,
        meta: '',
        icon: insightIcons[i],
        color: insightColors[i]
      }
    }
    return {
      title: item.title ?? item.label ?? item.name ?? def.title,
      description: item.description ?? item.desc ?? item.content ?? item.summary ?? '',
      meta: item.meta ?? item.trend ?? item.change ?? item.time ?? '',
      icon: insightIcons[i],
      color: insightColors[i]
    }
  })
})

// ---- Watchers ----
watch(() => store.overview, (val) => {
  if (val) triggerAnimations(val)
}, { immediate: true })

watch(() => store.categories, () => {
  nextTick(() => { initPieChart() })
})

watch(() => store.satisfaction, () => {
  nextTick(() => { initLineChart() })
})

// ---- Resize ----
function handleResize() {
  pieChartInstance?.resize()
  lineChartInstance?.resize()
}

// ---- Lifecycle ----
onMounted(async () => {
  updateClock()
  timeTimer = setInterval(updateClock, 1000)
  window.addEventListener('resize', handleResize)

  await store.fetchAll()
  store.startPolling(30000)

  await nextTick()
  initPieChart()
  initLineChart()
})

onBeforeUnmount(() => {
  clearInterval(timeTimer)
  window.removeEventListener('resize', handleResize)
  store.stopPolling()
  pieChartInstance?.dispose()
  lineChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

/* ---- Header ---- */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

/* ---- Stats Row ---- */
.stats-row {
  margin-bottom: 20px;
}
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
.stat-card :deep(.el-card__body) {
  padding: 20px;
}
.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stat-label {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 6px 0;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 4px 0;
  font-variant-numeric: tabular-nums;
}
.stat-suffix {
  font-size: 18px;
  font-weight: 500;
  color: #94a3b8;
  margin-left: 2px;
}
.stat-sub {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}
.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

/* ---- Charts Row ---- */
.charts-row {
  margin-bottom: 20px;
}
.chart-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}
.chart-card :deep(.el-card__header) {
  color: #e2e8f0;
  font-weight: 500;
  border-bottom-color: rgba(255, 255, 255, 0.08);
  padding: 14px 20px;
}
.chart-card :deep(.el-card__body) {
  padding: 12px;
}
.chart-box {
  width: 100%;
  height: 340px;
}
.chart-empty {
  width: 100%;
  height: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ---- Insights Row ---- */
.insights-row {
  margin-bottom: 20px;
}
.insight-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  transition: border-color 0.3s, transform 0.2s;
}
.insight-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}
.insight-card :deep(.el-card__body) {
  padding: 20px;
}
.insight-card-inner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.insight-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.insight-body {
  flex: 1;
  min-width: 0;
}
.insight-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 6px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.insight-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 8px 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.insight-meta {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

/* ---- Element Plus overrides ---- */
:deep(.el-empty__description) {
  color: #64748b;
}
</style>
