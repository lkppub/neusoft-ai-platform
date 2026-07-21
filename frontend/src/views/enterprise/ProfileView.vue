<template>
  <div class="profile-page">
    <div class="page-header">
      <h2>个人中心</h2>
      <p class="page-desc">管理您的个人信息与账号安全</p>
    </div>

    <!-- Profile Information Card -->
    <el-card shadow="never" class="profile-card">
      <template #header>
        <div class="card-header">
          <el-icon><User /></el-icon>
          <span>基本信息</span>
          <el-button
            v-if="!editing"
            type="primary"
            size="small"
            :icon="Edit"
            @click="startEdit"
            class="edit-toggle-btn"
          >
            编辑
          </el-button>
          <template v-else>
            <div class="edit-actions">
              <el-button size="small" @click="cancelEdit">取消</el-button>
              <el-button type="primary" size="small" :loading="saving" @click="saveProfile">
                保存
              </el-button>
            </div>
          </template>
        </div>
      </template>

      <el-form :model="form" label-width="100px" label-position="right" :disabled="!editing">
        <el-form-item label="用户名">
          <el-input :model-value="user?.username" disabled />
        </el-form-item>

        <el-form-item label="邮箱">
          <el-input :model-value="user?.email" disabled />
        </el-form-item>

        <el-form-item label="角色">
          <el-tag :type="roleTagType" size="default">
            {{ roleLabel }}
          </el-tag>
        </el-form-item>

        <el-divider />

        <el-form-item label="姓名" prop="full_name">
          <el-input
            v-model="form.full_name"
            placeholder="请输入您的姓名"
            :class="{ 'readonly-field': !editing }"
          />
        </el-form-item>

        <el-form-item label="公司名称" prop="company_name">
          <el-input
            v-model="form.company_name"
            placeholder="请输入公司名称"
            :class="{ 'readonly-field': !editing }"
          />
        </el-form-item>

        <el-form-item label="部门" prop="department">
          <el-input
            v-model="form.department"
            placeholder="请输入所在部门"
            :class="{ 'readonly-field': !editing }"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Change Password Card -->
    <el-card shadow="never" class="password-card">
      <template #header>
        <div class="card-header">
          <el-icon><Lock /></el-icon>
          <span>修改密码</span>
        </div>
      </template>

      <el-form
        ref="passwordFormRef"
        :model="pwdForm"
        :rules="passwordRules"
        label-width="110px"
        label-position="right"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="pwdForm.old_password"
            type="password"
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="pwdForm.new_password"
            type="password"
            show-password
            placeholder="请输入新密码（至少6位）"
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="pwdForm.confirm_password"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="changingPwd"
            @click="handleChangePassword"
          >
            {{ changingPwd ? '修改中...' : '修改密码' }}
          </el-button>
          <el-button @click="resetPasswordForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changePassword as changePwdApi } from '@/api/auth'

const authStore = useAuthStore()
const user = computed(() => authStore.user)

const editing = ref(false)
const saving = ref(false)
const changingPwd = ref(false)
const passwordFormRef = ref(null)

const form = reactive({
  full_name: '',
  company_name: '',
  department: '',
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

// Role display
const roleMap = {
  enterprise: '企业用户',
  customer_service: '客服人员',
  decision_maker: '决策者',
  admin: '管理员',
}

const roleLabel = computed(() => roleMap[user.value?.role] || user.value?.role || '--')

const roleTagType = computed(() => {
  const map = { admin: 'danger', enterprise: 'primary', customer_service: 'success', decision_maker: 'warning' }
  return map[user.value?.role] || 'info'
})

// Password validation
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

// Edit mode
function startEdit() {
  form.full_name = user.value?.full_name || ''
  form.company_name = user.value?.company_name || ''
  form.department = user.value?.department || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function saveProfile() {
  saving.value = true
  try {
    await authStore.updateUserProfile({
      full_name: form.full_name,
      company_name: form.company_name,
      department: form.department,
    })
    editing.value = false
    ElMessage.success('个人信息保存成功')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存失败'
    ElMessage.error(detail)
  } finally {
    saving.value = false
  }
}

// Password change
function resetPasswordForm() {
  pwdForm.old_password = ''
  pwdForm.new_password = ''
  pwdForm.confirm_password = ''
  passwordFormRef.value?.resetFields()
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return
  try {
    await passwordFormRef.value.validate()
  } catch {
    return
  }

  changingPwd.value = true
  try {
    await changePwdApi(pwdForm.old_password, pwdForm.new_password)
    ElMessage.success('密码修改成功')
    resetPasswordForm()
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '密码修改失败'
    ElMessage.error(detail)
  } finally {
    changingPwd.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 680px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  color: #303133;
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: #909399;
}

.profile-card {
  margin-bottom: 24px;
}

.password-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.edit-toggle-btn {
  margin-left: auto;
}

.edit-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

/* Readonly field appearance */
.readonly-field :deep(.el-input__inner) {
  border-color: transparent;
  background: transparent;
  cursor: default;
}

.readonly-field :deep(.el-input__inner:focus) {
  border-color: transparent;
}
</style>
