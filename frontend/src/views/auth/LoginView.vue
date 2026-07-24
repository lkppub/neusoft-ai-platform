<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-icon">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" rx="16" fill="currentColor" fill-opacity="0.15"/>
            <path d="M20 44V20l12 8-12 8 12 8-12 8z" fill="currentColor"/>
            <path d="M32 44V20l12 8-12 8 12 8-12 8z" fill="currentColor" fill-opacity="0.6"/>
          </svg>
        </div>
        <h1>东软智慧商务AI助手平台</h1>
        <p>融合大模型与智能体能力，为您的企业提供智能化商务服务</p>
        <div class="brand-features">
          <div class="feature-item">
            <span class="feature-dot"></span>AI 智能对话 · 意图识别 · 工具调用
          </div>
          <div class="feature-item">
            <span class="feature-dot"></span>知识库问答 · RAG 检索增强
          </div>
          <div class="feature-item">
            <span class="feature-dot"></span>智能客服 · 自动分类 · 语音交互
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录区 -->
    <div class="login-form-side">
      <div class="form-wrapper">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>请登录您的账号以继续</p>
        </div>

        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          :closable="true"
          @close="errorMessage = ''"
          class="login-alert"
        />

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              :prefix-icon="User"
              class="custom-input"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
              class="custom-input"
            />
          </el-form-item>

          <el-button
            type="primary"
            class="login-btn"
            :loading="loading"
            :disabled="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>

          <div class="form-footer">
            <span>还没有账号？</span>
            <router-link to="/register">立即注册</router-link>
          </div>
        </el-form>

        <!-- 测试账号提示 -->
        <div class="demo-hint">
          <el-collapse>
            <el-collapse-item title="查看演示账号" name="1">
              <div class="demo-accounts">
                <p><strong>管理员</strong>：admin / 123456</p>
                <p><strong>客服人员</strong>：cs_staff / 123456</p>
                <p><strong>企业用户</strong>：enterprise / 123456</p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码长度不能少于 6 个字符', trigger: 'blur' },
  ],
}

const handleLogin = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login({ username: form.username, password: form.password })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/conversations'
    router.push(redirect)
  } catch (err) {
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.message ||
      '登录失败，请检查用户名和密码'
    errorMessage.value = detail
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(160deg, #e8f4fd 0%, #dceefb 30%, #f0f7ff 60%, #e3edf5 100%);
}

/* ── 左侧品牌区 ── */
.login-brand {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5vh 4vw;
  overflow-y: auto;
}

.brand-content {
  max-width: 480px;
}

.brand-icon {
  width: 64px;
  height: 64px;
  color: #409eff;
  margin-bottom: 32px;
}

.brand-content h1 {
  font-size: 34px;
  font-weight: 700;
  margin: 0 0 16px 0;
  letter-spacing: 1px;
  line-height: 1.3;
  color: #1a3a5c;
}

.brand-content > p {
  font-size: 16px;
  color: #5a7a9a;
  margin: 0 0 48px 0;
  line-height: 1.6;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: #4a6d8c;
}

.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
}

/* ── 右侧登录区 ── */
.login-form-side {
  flex: 0 0 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5vh 4vw;
  overflow-y: auto;
}

.form-wrapper {
  width: 100%;
  max-width: 380px;
}

.form-header {
  margin-bottom: 40px;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1a3a5c;
  margin: 0 0 8px 0;
}

.form-header p {
  font-size: 15px;
  color: #7a8fa0;
  margin: 0;
}

.login-alert {
  margin-bottom: 20px;
}

/* ── 输入框 ── */
.custom-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: rgba(255,255,255,0.85);
  box-shadow: 0 0 0 1px #d4dfe8 inset;
  transition: all 0.2s;
}

.custom-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #a0b8d0 inset;
  background: rgba(255,255,255,0.95);
}

.custom-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #409eff inset;
  background: #fff;
}

/* ── 按钮 ── */
.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  margin-top: 12px;
  background: #409eff;
  border: none;
  transition: all 0.2s;
}

.login-btn:hover {
  background: #337ecc;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

/* ── 页脚 ── */
.form-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #7a8fa0;
}

.form-footer a {
  color: #409eff;
  text-decoration: none;
  margin-left: 4px;
  font-weight: 500;
}

.form-footer a:hover {
  color: #337ecc;
}

/* ── 演示账号 ── */
.demo-hint {
  margin-top: 32px;
  border-top: 1px solid #dce4ec;
  padding-top: 16px;
}

.demo-hint :deep(.el-collapse-item__header) {
  font-size: 13px;
  color: #8fa0b0;
  border: none;
  line-height: 32px;
  height: 32px;
  background: transparent;
}

.demo-hint :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
}

.demo-accounts {
  font-size: 13px;
  color: #5a7a9a;
  background: rgba(255,255,255,0.5);
  border-radius: 6px;
  padding: 12px 16px;
  line-height: 1.8;
}

.demo-accounts p {
  margin: 0;
}

.demo-accounts strong {
  color: #1a3a5c;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .login-brand {
    display: none;
  }

  .login-form-side {
    flex: 1;
    padding: 40px 24px;
  }
}
</style>
