<template>
  <div class="ai-config-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- AI Configurations -->
      <el-tab-pane label="AI配置" name="configs">
        <el-table :data="adminStore.aiConfigs" stripe v-loading="configLoading" class="mt-16">
          <el-table-column prop="key" label="配置键" width="220" />
          <el-table-column prop="value" label="当前值" min-width="280">
            <template #default="{ row }">
              <template v-if="editingConfigKey === row.key">
                <el-input
                  v-model="editingConfigValue"
                  :type="isSensitive(row.key) ? 'password' : 'text'"
                  show-password
                  size="small"
                />
              </template>
              <template v-else>
                <span v-if="isSensitive(row.key)">********</span>
                <span v-else>{{ row.value }}</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="200">
            <template #default="{ row }">
              <template v-if="editingConfigKey === row.key">
                <el-input v-model="editingConfigDescription" size="small" />
              </template>
              <template v-else>
                {{ row.description }}
              </template>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <template v-if="editingConfigKey === row.key">
                <el-button link type="primary" size="small" :loading="savingConfig" @click="saveInlineConfig(row)">保存</el-button>
                <el-button link type="info" size="small" @click="cancelInlineEdit">取消</el-button>
              </template>
              <template v-else>
                <el-button link type="primary" size="small" @click="startInlineEdit(row)">编辑</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Prompt Templates -->
      <el-tab-pane label="提示词模板" name="prompts">
        <div class="tab-header">
          <el-button type="primary" size="small" @click="openCreatePrompt">
            <el-icon><Plus /></el-icon>新建模板
          </el-button>
        </div>
        <el-table :data="adminStore.prompts" stripe v-loading="promptLoading" class="mt-16">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="name" label="名称" width="160" />
          <el-table-column prop="scenario" label="场景" width="140">
            <template #default="{ row }">
              <el-tag size="small">{{ scenarioLabel(row.scenario) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="system_prompt" label="系统提示词" min-width="240" show-overflow-tooltip />
          <el-table-column prop="updated_at" label="更新时间" width="170">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEditPrompt(row)">编辑</el-button>
              <el-button link type="success" size="small" @click="openTestPrompt(row)">测试</el-button>
              <el-button link type="danger" size="small" @click="handleDeletePrompt(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Prompt create/edit dialog -->
    <el-dialog
      v-model="promptDialogVisible"
      :title="editingPrompt ? '编辑提示词模板' : '新建提示词模板'"
      width="650px"
      top="5vh"
    >
      <el-form :model="promptForm" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="promptForm.name" placeholder="模板名称" />
        </el-form-item>
        <el-form-item label="场景" required>
          <el-select v-model="promptForm.scenario" placeholder="选择场景" style="width: 100%">
            <el-option label="客服对话" value="customer_service" />
            <el-option label="知识问答" value="knowledge_qa" />
            <el-option label="数据分析" value="data_analysis" />
            <el-option label="报告生成" value="report_generation" />
            <el-option label="通用对话" value="general" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="系统提示词" required>
          <el-input
            v-model="promptForm.system_prompt"
            type="textarea"
            :rows="6"
            placeholder="系统提示词内容，支持 {{ variable }} 变量"
          />
        </el-form-item>
        <el-form-item label="用户提示词模板">
          <el-input
            v-model="promptForm.user_prompt_template"
            type="textarea"
            :rows="4"
            placeholder="用户提示词模板，支持 {{ variable }} 变量"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="promptDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPrompt" @click="savePrompt">保存</el-button>
      </template>
    </el-dialog>

    <!-- Test prompt dialog -->
    <el-dialog v-model="testDialogVisible" title="测试提示词" width="650px" top="5vh">
      <el-form v-if="testingPrompt" label-width="100px">
        <el-form-item label="模板名称">
          <span>{{ testingPrompt.name }}</span>
        </el-form-item>
        <el-form-item label="场景">
          <el-tag size="small">{{ scenarioLabel(testingPrompt.scenario) }}</el-tag>
        </el-form-item>
        <el-form-item label="变量（JSON）">
          <el-input
            v-model="testVariablesJson"
            type="textarea"
            :rows="6"
            placeholder='输入 JSON 变量，例如: {"question": "什么是AI？", "context": "..."}'
          />
          <div v-if="jsonParseError" class="json-error">{{ jsonParseError }}</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="testLoading" @click="runTest">发送测试</el-button>
        </el-form-item>
      </el-form>
      <div v-if="testResult" class="test-result">
        <h4>AI 响应</h4>
        <div class="test-output">{{ testResult }}</div>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { ElMessage, ElMessageBox } from 'element-plus'

const adminStore = useAdminStore()
const activeTab = ref('configs')
const configLoading = ref(false)
const promptLoading = ref(false)

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}

function isSensitive(key) {
  return /(api_key|secret|password|token)/i.test(key)
}

function scenarioLabel(s) {
  const map = {
    customer_service: '客服对话',
    knowledge_qa: '知识问答',
    data_analysis: '数据分析',
    report_generation: '报告生成',
    general: '通用对话',
    other: '其他'
  }
  return map[s] || s || ''
}

// ─── Configs - inline edit ───
const editingConfigKey = ref(null)
const editingConfigValue = ref('')
const editingConfigDescription = ref('')
const savingConfig = ref(false)

async function loadConfigs() {
  configLoading.value = true
  try {
    await adminStore.fetchAIConfigs()
  } finally {
    configLoading.value = false
  }
}

function startInlineEdit(row) {
  editingConfigKey.value = row.key
  editingConfigValue.value = row.value
  editingConfigDescription.value = row.description || ''
}

function cancelInlineEdit() {
  editingConfigKey.value = null
  editingConfigValue.value = ''
  editingConfigDescription.value = ''
}

async function saveInlineConfig(row) {
  savingConfig.value = true
  try {
    await adminStore.editAIConfig(row.key, editingConfigValue.value, editingConfigDescription.value)
    ElMessage.success('配置已更新')
    cancelInlineEdit()
    await loadConfigs()
  } catch {
    /* handled in interceptor */
  } finally {
    savingConfig.value = false
  }
}

// ─── Prompts ───
const promptDialogVisible = ref(false)
const savingPrompt = ref(false)
const editingPrompt = ref(null)
const promptForm = reactive({
  name: '',
  scenario: '',
  system_prompt: '',
  user_prompt_template: ''
})

// Test
const testDialogVisible = ref(false)
const testingPrompt = ref(null)
const testVariablesJson = ref('')
const jsonParseError = ref('')
const testLoading = ref(false)
const testResult = ref('')

async function loadPrompts() {
  promptLoading.value = true
  try {
    await adminStore.fetchPrompts()
  } finally {
    promptLoading.value = false
  }
}

function openCreatePrompt() {
  editingPrompt.value = null
  Object.assign(promptForm, {
    name: '',
    scenario: '',
    system_prompt: '',
    user_prompt_template: ''
  })
  promptDialogVisible.value = true
}

function openEditPrompt(row) {
  editingPrompt.value = row
  Object.assign(promptForm, {
    name: row.name || '',
    scenario: row.scenario || '',
    system_prompt: row.system_prompt || '',
    user_prompt_template: row.user_prompt_template || ''
  })
  promptDialogVisible.value = true
}

async function savePrompt() {
  savingPrompt.value = true
  try {
    const payload = {
      name: promptForm.name,
      scenario: promptForm.scenario,
      system_prompt: promptForm.system_prompt,
      user_prompt_template: promptForm.user_prompt_template
    }
    if (editingPrompt.value) {
      await adminStore.editPrompt(editingPrompt.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await adminStore.addPrompt(payload)
      ElMessage.success('创建成功')
    }
    promptDialogVisible.value = false
    await loadPrompts()
  } catch {
    /* handled in interceptor */
  } finally {
    savingPrompt.value = false
  }
}

async function handleDeletePrompt(row) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${row.name}」吗？`, '确认删除', { type: 'warning' })
    await adminStore.removePrompt(row.id)
    ElMessage.success('已删除')
    await loadPrompts()
  } catch {
    /* cancelled */
  }
}

function openTestPrompt(row) {
  testingPrompt.value = row
  testResult.value = ''
  testVariablesJson.value = '{}'
  jsonParseError.value = ''
  testDialogVisible.value = true
}

async function runTest() {
  if (!testingPrompt.value) return

  let vars = {}
  try {
    vars = JSON.parse(testVariablesJson.value || '{}')
    if (typeof vars !== 'object' || vars === null || Array.isArray(vars)) {
      throw new Error('变量必须是 JSON 对象')
    }
    jsonParseError.value = ''
  } catch (e) {
    jsonParseError.value = 'JSON 格式错误：' + e.message
    return
  }

  testLoading.value = true
  testResult.value = ''
  try {
    const res = await adminStore.testPromptById(testingPrompt.value.id, vars)
    testResult.value = typeof res === 'string' ? res : (res.result || res.output || res.content || JSON.stringify(res, null, 2))
  } catch {
    /* handled in interceptor */
  } finally {
    testLoading.value = false
  }
}

onMounted(() => {
  loadConfigs()
  loadPrompts()
})
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}

.tab-header {
  margin-bottom: 0;
}

.json-error {
  margin-top: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.test-result {
  margin-top: 20px;
}

.test-result h4 {
  margin-bottom: 8px;
  color: #303133;
  font-size: 15px;
}

.test-output {
  background: #f5f7fa;
  padding: 14px;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.7;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
}
</style>
