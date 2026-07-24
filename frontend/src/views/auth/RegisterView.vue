<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>创建账号</h1>
        <p>加入东软智慧商务AI助手平台</p>
      </div>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        :closable="true"
        @close="errorMessage = ''"
        class="register-alert"
      />

      <el-alert
        v-if="successMessage"
        :title="successMessage"
        type="success"
        show-icon
        :closable="true"
        @close="successMessage = ''"
        class="register-alert"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="register-form"
        size="default"
        label-position="top"
      >
        <el-form-item prop="username" label="用户名">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="email" label="邮箱">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱地址"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item prop="full_name" label="姓名">
          <el-input
            v-model="form.full_name"
            placeholder="请输入您的姓名"
            :prefix-icon="UserFilled"
          />
        </el-form-item>

        <el-form-item prop="role" label="角色">
          <el-select
            v-model="form.role"
            placeholder="请选择您的角色"
            class="role-select"
          >
            <el-option label="企业用户" value="enterprise" />
            <el-option label="客服人员" value="customer_service" />
            <el-option label="决策者" value="decision_maker" />
          </el-select>
        </el-form-item>

        <el-form-item prop="password" label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（至少6位）"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword" label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="register-btn"
            :loading="loading"
            :disabled="loading"
            @click="handleRegister"
          >
            {{ loading ? '注册中...' : '注册' }}
          </el-button>
        </el-form-item>

        <div class="register-footer">
          <router-link to="/login">已有账号？立即登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const form = reactive({
  username: '',
  email: '',
  full_name: '',
  role: 'enterprise',
  password: '',
  confirmPassword: '',
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  full_name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 1, max: 50, message: '姓名长度在 1 到 50 个字符', trigger: 'blur' },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码长度不能少于 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

const handleRegister = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await authStore.register({
      username: form.username,
      email: form.email,
      full_name: form.full_name,
      role: form.role,
      password: form.password,
    })
    successMessage.value = '注册成功！即将跳转到登录页面...'
    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } catch (err) {
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.message ||
      '注册失败，请稍后再试'
    errorMessage.value = detail
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(160deg, #e8f4fd 0%, #dceefb 30%, #f0f7ff 60%, #e3edf5 100%);
}

.register-card {
  width: 460px;
  padding: 24px 44px 20px;
}

/* 压缩表单间距 */
.register-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.register-form :deep(.el-form-item__label) {
  padding-bottom: 2px;
  font-size: 13px;
}

.register-header {
  text-align: center;
  margin-bottom: 20px;
}

.register-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: #1a3a5c;
  margin: 0 0 8px 0;
}

.register-header p {
  font-size: 14px;
  color: #7a8fa0;
  margin: 0;
}

.register-alert {
  margin-bottom: 16px;
}

.role-select {
  width: 100%;
}

/* ── 按钮 ── */
.register-btn {
  width: 100%;
  height: 46px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  margin-top: 4px;
}

.register-footer {
  text-align: center;
  font-size: 14px;
  margin-top: 4px;
}

.register-footer a {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}

.register-footer a:hover {
  color: #337ecc;
}
</style>
