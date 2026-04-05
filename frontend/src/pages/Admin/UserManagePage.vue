<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <el-button type="primary" @click="openDialog()">新增用户</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="160" />
        <el-table-column prop="roleName" label="角色" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="fetchList"
        @size-change="fetchList"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editId ? '编辑用户' : '新增用户'"
      width="560px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        v-loading="dialogLoading"
        :model="form"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>
        <el-form-item label="角色" prop="roleId">
          <el-select v-model="form.roleId" placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="editId ? '新密码' : '密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editId ? '不修改可留空' : '请输入密码'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="onSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import {
  getRolesApi,
  getUserListApi,
  getUserDetailApi,
  createUserApi,
  updateUserApi,
  deleteUserApi,
  type AdminUserItem,
} from '@/api/admin';

const loading = ref(false);
const list = ref<AdminUserItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const roles = ref<{ id: number; name: string }[]>([]);

const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const dialogLoading = ref(false);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

const form = reactive({
  username: '',
  email: '',
  roleId: 1,
  password: '',
});

const formRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  roleId: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    {
      validator: (_rule, value, callback) => {
        if (!editId.value && !String(value || '').trim()) {
          callback(new Error('请输入密码'));
          return;
        }
        callback();
      },
      trigger: 'blur',
    },
  ],
};

async function fetchList() {
  loading.value = true;
  try {
    const res = await getUserListApi({ page: page.value, pageSize: pageSize.value });
    list.value = res.list;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

async function loadRoles() {
  roles.value = await getRolesApi();
}

async function openDialog(row?: AdminUserItem) {
  if (!row) {
    editId.value = null;
    resetForm();
    dialogVisible.value = true;
    return;
  }
  editId.value = row.id;
  dialogVisible.value = true;
  dialogLoading.value = true;
  try {
    const detail = await getUserDetailApi(row.id);
    form.username = detail.username || '';
    form.email = detail.email || '';
    form.roleId = detail.roleId || 1;
    form.password = '';
  } finally {
    dialogLoading.value = false;
  }
}

function resetForm() {
  form.username = '';
  form.email = '';
  form.roleId = 1;
  form.password = '';
  formRef.value?.resetFields();
}

async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editId.value) {
        await updateUserApi(editId.value, {
          username: form.username.trim(),
          email: form.email.trim() || undefined,
          roleId: form.roleId,
          password: form.password.trim() || undefined,
        });
        ElMessage.success('更新成功');
      } else {
        await createUserApi({
          username: form.username.trim(),
          password: form.password.trim(),
          email: form.email.trim() || undefined,
          roleId: form.roleId,
        });
        ElMessage.success('新增成功');
      }
      dialogVisible.value = false;
      fetchList();
    } finally {
      submitLoading.value = false;
    }
  });
}

async function onDelete(row: AdminUserItem) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' });
  await deleteUserApi(row.id);
  ElMessage.success('删除成功');
  fetchList();
}

onMounted(() => {
  loadRoles();
  fetchList();
});
</script>

<style scoped>
.page {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>

