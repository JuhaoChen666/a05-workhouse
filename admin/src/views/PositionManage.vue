<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>岗位列表</span>
          <el-button type="primary" @click="openDialog()">新增岗位</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="岗位名称" min-width="120" />
        <el-table-column prop="sortOrder" label="排序" width="80" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑岗位' : '新增岗位'" width="400px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：Java后端" />
        </el-form-item>
        <el-form-item label="排序" prop="sortOrder">
          <el-input-number v-model="form.sortOrder" :min="0" />
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
  getPositionListApi,
  createPositionApi,
  updatePositionApi,
  deletePositionApi,
} from '@/api/admin';
import type { PositionItem } from '@/api/admin';

const loading = ref(false);
const list = ref<PositionItem[]>([]);
const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

const form = reactive({
  name: '',
  sortOrder: 0,
});

const rules: FormRules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
};

async function fetchList() {
  loading.value = true;
  try {
    list.value = await getPositionListApi();
  } finally {
    loading.value = false;
  }
}

function openDialog(row?: PositionItem) {
  editId.value = row ? row.id : null;
  form.name = row ? row.name : '';
  form.sortOrder = row ? row.sortOrder : 0;
  dialogVisible.value = true;
}

function resetForm() {
  form.name = '';
  form.sortOrder = 0;
  formRef.value?.resetFields();
}

async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editId.value) {
        await updatePositionApi(editId.value, { name: form.name, sortOrder: form.sortOrder });
        ElMessage.success('更新成功');
      } else {
        await createPositionApi({ name: form.name, sortOrder: form.sortOrder });
        ElMessage.success('新增成功');
      }
      dialogVisible.value = false;
      fetchList();
    } finally {
      submitLoading.value = false;
    }
  });
}

async function onDelete(row: PositionItem) {
  await ElMessageBox.confirm(`确定删除岗位「${row.name}」吗？`, '提示', {
    type: 'warning',
  });
  await deletePositionApi(row.id);
  ElMessage.success('删除成功');
  fetchList();
}

onMounted(fetchList);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
