<template>
  <!-- 学习资源管理页：支持增删改查学习资源链接 -->
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>学习资源</span>
          <el-button type="primary" @click="openDialog()">新增资源</el-button>
        </div>
      </template>

      <!-- 学习资源表格 -->
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="link" label="链接" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <a :href="row.link" target="_blank" rel="noopener">{{ row.link }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 新增 / 编辑学习资源对话框 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑资源' : '新增资源'" width="500px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="资源标题" />
        </el-form-item>
        <el-form-item label="链接" prop="link">
          <el-input v-model="form.link" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="标签" prop="tags">
          <el-input v-model="form.tags" placeholder="逗号分隔，如：Vue, 面试" />
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
  getLearningResourceListApi,
  createLearningResourceApi,
  updateLearningResourceApi,
  deleteLearningResourceApi,
  type AdminLearningResourceItem,
} from '@/api/admin';

// 加载状态与表格数据
const loading = ref(false);
const list = ref<AdminLearningResourceItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

// 弹窗状态
const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

// 表单数据
const form = reactive({
  title: '',
  link: '',
  tags: '',
});

// 表单校验规则
const formRules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  link: [{ required: true, message: '请输入链接', trigger: 'blur' }],
};

/** 拉取学习资源列表 */
async function fetchList() {
  loading.value = true;
  try {
    const res = await getLearningResourceListApi({
      page: page.value,
      pageSize: pageSize.value,
    });
    list.value = res.list;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

/** 打开新增 / 编辑弹窗 */
function openDialog(row?: AdminLearningResourceItem) {
  editId.value = row ? row.id : null;
  form.title = row ? row.title : '';
  form.link = row ? row.link : '';
  form.tags = row ? row.tags ?? '' : '';
  dialogVisible.value = true;
}

/** 关闭弹窗时重置表单 */
function resetForm() {
  form.title = '';
  form.link = '';
  form.tags = '';
  formRef.value?.resetFields();
}

/** 提交表单，新增或更新资源 */
async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editId.value) {
        await updateLearningResourceApi(editId.value, {
          title: form.title,
          link: form.link,
          tags: form.tags || undefined,
        });
        ElMessage.success('更新成功');
      } else {
        await createLearningResourceApi({
          title: form.title,
          link: form.link,
          tags: form.tags || undefined,
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

/** 删除单条学习资源 */
async function onDelete(row: AdminLearningResourceItem) {
  await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '提示', { type: 'warning' });
  await deleteLearningResourceApi(row.id);
  ElMessage.success('删除成功');
  fetchList();
}

// 页面加载时获取列表
onMounted(fetchList);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

a {
  color: #409eff;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>

