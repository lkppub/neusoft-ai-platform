<template>
  <div class="knowledge-query-view">
    <!-- Page Header -->
    <div class="page-header">
      <h2 class="page-title">知识库查询</h2>
      <p class="page-subtitle">基于 RAG 的知识库智能检索，获取 AI 驱动的精准回答</p>
    </div>

    <!-- Search Bar -->
    <div class="search-bar">
      <el-input
        v-model="question"
        placeholder="请输入您的问题，例如：公司的报销流程是什么？"
        size="large"
        clearable
        @keyup.enter="handleSearch"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button
        type="primary"
        size="large"
        :loading="searching"
        :disabled="!question.trim()"
        @click="handleSearch"
        class="search-button"
      >
        <el-icon v-if="!searching"><Search /></el-icon>
        <span>{{ searching ? '检索中...' : '查询' }}</span>
      </el-button>
    </div>

    <!-- Initial Empty State (before any search) -->
    <div v-if="!hasSearched" class="state-container">
      <el-empty description="请输入问题开始检索知识库">
        <template #image>
          <el-icon :size="80" color="#c0c4cc"><Document /></el-icon>
        </template>
      </el-empty>
    </div>

    <!-- Searching and Results Area -->
    <div
      v-if="hasSearched"
      v-loading="searching"
      element-loading-text="正在检索知识库，请稍候..."
      element-loading-background="rgba(255, 255, 255, 0.8)"
      class="results-area"
    >
      <!-- No Results After Search -->
      <div v-if="!searching && !hasResults" class="state-container">
        <el-empty description="未找到相关信息，请尝试换个问题或调整关键词">
          <template #image>
            <el-icon :size="80" color="#c0c4cc"><FolderOpened /></el-icon>
          </template>
        </el-empty>
      </div>

      <!-- Results -->
      <template v-if="!searching && hasResults">
        <!-- AI Answer Card -->
        <div v-if="knowledgeStore.searchResults.answer" class="answer-card">
          <div class="answer-card-header">
            <div class="answer-card-icon">
              <el-icon :size="24"><MagicStick /></el-icon>
            </div>
            <div class="answer-card-title-section">
              <h3 class="answer-card-title">AI 智能回答</h3>
              <span class="answer-card-badge">基于知识库生成</span>
            </div>
          </div>
          <div class="answer-card-body">
            <p class="answer-text">{{ knowledgeStore.searchResults.answer }}</p>
          </div>
        </div>

        <!-- Source Cards -->
        <div v-if="knowledgeStore.searchResults.sources?.length" class="sources-section">
          <div class="sources-section-header">
            <h3 class="sources-title">引用来源</h3>
            <span class="sources-count">共 {{ knowledgeStore.searchResults.sources.length }} 条</span>
          </div>

          <div class="sources-grid">
            <div
              v-for="(source, index) in knowledgeStore.searchResults.sources"
              :key="index"
              class="source-card"
            >
              <div class="source-card-top">
                <span class="source-rank">#{{ index + 1 }}</span>
                <div class="source-score">
                  <el-progress
                    :percentage="Math.round(source.score * 100)"
                    :stroke-width="6"
                    :color="scoreColor(source.score)"
                    :show-text="false"
                    class="source-score-bar"
                  />
                  <span class="source-score-text" :style="{ color: scoreColor(source.score) }">
                    {{ Math.round(source.score * 100) }}%
                  </span>
                </div>
              </div>
              <p class="source-content">
                {{ truncateContent(source.content) }}
              </p>
              <div class="source-card-footer">
                <el-icon :size="14"><FolderOpened /></el-icon>
                <span class="source-name">{{ source.metadata?.source || '未知来源' }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import { ElMessage } from 'element-plus'
import { Search, Document, FolderOpened, MagicStick } from '@element-plus/icons-vue'

const knowledgeStore = useKnowledgeStore()

const question = ref('')
const searching = ref(false)
const hasSearched = ref(false)

const hasResults = computed(() => {
  const results = knowledgeStore.searchResults
  return !!(results.answer || (results.sources && results.sources.length > 0))
})

function truncateContent(content) {
  if (!content) return ''
  if (content.length <= 300) return content
  return content.slice(0, 300) + '...'
}

function scoreColor(score) {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

async function handleSearch() {
  const trimmed = question.value.trim()
  if (!trimmed) return

  searching.value = true
  hasSearched.value = true

  try {
    await knowledgeStore.queryKnowledge(trimmed, 5, 0.5)
  } catch (error) {
    ElMessage.error('检索失败，请稍后重试')
    console.error('Knowledge query failed:', error)
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.knowledge-query-view {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

/* Page Header */
.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

/* Search Bar */
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 36px;
}

.search-input {
  flex: 1;
}

.search-button {
  flex-shrink: 0;
  min-width: 100px;
}

/* State Containers */
.state-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 320px;
}

/* Results Area */
.results-area {
  min-height: 200px;
}

/* Answer Card */
.answer-card {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 32px;
}

.answer-card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px 0;
}

.answer-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  flex-shrink: 0;
}

.answer-card-title-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.answer-card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.answer-card-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  color: #409eff;
  background: rgba(64, 158, 255, 0.12);
}

.answer-card-body {
  padding: 16px 24px 24px;
}

.answer-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.8;
  color: #4a4d52;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Sources Section */
.sources-section {
  margin-top: 8px;
}

.sources-section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}

.sources-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.sources-count {
  font-size: 13px;
  color: #909399;
}

.sources-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Source Card */
.source-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 20px 24px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.source-card:hover {
  border-color: #c0c4cc;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.source-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.source-rank {
  font-size: 14px;
  font-weight: 700;
  color: #909399;
}

.source-score {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 160px;
}

.source-score-bar {
  flex: 1;
}

.source-score-text {
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  min-width: 40px;
  text-align: right;
}

.source-content {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
  word-break: break-word;
}

.source-card-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
}

.source-name {
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Responsive */
@media (max-width: 640px) {
  .knowledge-query-view {
    padding: 16px 12px 32px;
  }

  .search-bar {
    flex-direction: column;
  }

  .search-button {
    width: 100%;
  }

  .source-score {
    width: 130px;
  }
}
</style>
