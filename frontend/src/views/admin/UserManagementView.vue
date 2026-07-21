<template>
  <div class="user-management">
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="header-actions">
        <el-select
          v-model="roleFilter"
          placeholder="角色筛选"
          clearable
          @change="loadUsers"
          style="width: 140px; margin-right: 12px"
        >
          <el-option label="管理员" value="admin" />
          <el-option label="企业用户" value="enterprise" />
          <el-option label="客服" value="customer_service" />
          <el-option label="决策者" value="decision_maker" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon style="margin-right: 4px"><Plus /></el-icon>新增用户
        </el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="adminStore.users" stripe v-loading="loading">
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="company_name" label="公司" width="160" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column prop="is_active" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="handleResetPwd(row)">重置密码</el-button>
            <el-button
              link
              :type="row.is_active ? 'info' : 'success'"
              size="small"
              @click="handleToggleActive(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="adminStore.usersTotal"
          layout="total, prev, pager, next"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 新增 / 编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingUser ? '编辑用户' : '新增用户'"
      width="520px"
    >
      <el-form :model="userForm" label-width="80px">
        <el-form-item v-if="!editingUser" label="用户名" required>
          <el-input v-model="userForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item v-if="!editingUser" label="密码" required>
          <el-input v-model="userForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.full_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="userForm.company_name" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option label="企业用户" value="enterprise" />
            <el-option label="客服人员" value="customer_service" />
            <el-option label="决策者" value="decision_maker" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const adminStore = useAdminStore()
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const roleFilter = ref('')
const dialogVisible = ref(false)
const saving = ref(false)
const editingUser = ref(null)
const userForm = reactive({
  username: '',
  password: '',
  email: '',
  full_name: '',
  company_name: '',
  department: '',
  role: 'enterprise',
})

const roleLabelMap = {
  admin: '管理员',
  enterprise: '企业用户',
  customer_service: '客服人员',
  decision_maker: '决策者',
}

const roleTagTypeMap = {
  admin: 'danger',
  enterprise: '',
  customer_service: 'success',
  decision_maker: 'warning',
}

function roleLabel(role) {
  return roleLabelMap[role] || role
}

function roleTagType(role) {
  return roleTagTypeMap[role] || 'info'
}

async function loadUsers(p) {
  if (p) page.value = p
  loading.value = true
  try {
    await adminStore.fetchUsers(page.value, pageSize.value, roleFilter.value || null)
  } finally {
    loading.value = false
  }
}

function resetUserForm() {
  Object.assign(userForm, {
    username: '',
    password: '',
    email: '',
    full_name: '',
    company_name: '',
    department: '',
    role: 'enterprise',
  })
}

function openCreateDialog() {
  editingUser.value = null
  resetUserForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingUser.value = row
  Object.assign(userForm, {
    username: row.username,
    password: '',
    email: row.email || '',
    full_name: row.full_name || '',
    company_name: row.company_name || '',
    department: row.department || '',
    role: row.role,
  })
  dialogVisible.value = true
}

async function saveUser() {
  saving.value = true
  try {
    if (editingUser.value) {
      await adminStore.editUser(editingUser.value.id, {
        email: userForm.email,
        full_name: userForm.full_name,
        company_name: userForm.company_name,
        department: userForm.department,
        role: userForm.role,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await adminStore.addUser({ ...userForm })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch {
    /* 错误由拦截器统一处理 */
  } finally {
    saving.value = false
  }
}

async function handleResetPwd(row) {
  try {
    await ElMessageBox.confirm(
      `确定要将用户「${row.username}」的密码重置为默认密码吗？`,
      '确认重置密码',
      { type: 'warning' }
    )
    await adminStore.resetPassword(row.id)
    ElMessage.success('密码已重置为默认密码')
  } catch {
    /* 取消操作 */
  }
}

async function handleToggleActive(row) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.username}」吗？`,
      `确认${action}`,
      { type: 'warning' }
    )
    await adminStore.editUser(row.id, { is_active: !row.is_active })
    ElMessage.success(`用户已${action}`)
    loadUsers()
  } catch {
    /* 取消操作 */
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要永久删除用户「${row.username}」吗？此操作不可恢复！`,
      '确认删除',
      { type: 'error', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await adminStore.removeUser(row.id)
    ElMessage.success('用户已删除')
    loadUsers()
  } catch {
    /* 取消操作 */
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  color: #303133;
}
.header-actions {
  display: flex;
  align-items: center;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
