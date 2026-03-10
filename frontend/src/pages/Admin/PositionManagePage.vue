<template>
  <!-- 岗位管理页：支持新增、编辑、删除岗位 -->
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>岗位列表</span>
          <el-button type="primary" @click="openDialog()">新增岗位</el-button>
        </div>
      </template>

      <!-- 岗位表格 -->
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="岗位名称" min-width="120" />
        <el-table-column prop="sortOrder" label="排序" width="80" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">详情</el-button>
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑岗位对话框
         关闭行为：不允许点击遮罩或按 ESC 关闭，只能通过“取消”或“确定”按钮关闭 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editId ? '编辑岗位' : '新增岗位'"
      width="720px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      @close="resetForm"
    >
      <el-form
        v-loading="dialogLoading"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：Java后端" />
        </el-form-item>
        <el-form-item label="排序" prop="sortOrder">
          <el-input-number v-model="form.sortOrder" :min="0" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="城市" prop="city">
              <el-input v-model="form.city" placeholder="如：北京 / 上海" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工作经验" prop="workExperience">
              <el-input v-model="form.workExperience" placeholder="如：3-5 年" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="学历要求" prop="education">
              <el-input v-model="form.education" placeholder="如：本科及以上" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="薪资范围" required>
              <div class="salary-range">
                <el-input-number
                  v-model="form.salaryMin"
                  :min="0"
                  :step="1000"
                  placeholder="最小"
                />
                <span class="salary-sep">-</span>
                <el-input-number
                  v-model="form.salaryMax"
                  :min="0"
                  :step="1000"
                  placeholder="最大"
                />
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="职位标签" prop="tags">
          <el-input
            v-model="form.tags"
            placeholder="逗号分隔，如：前端, 高薪, 面试"
          />
        </el-form-item>
        <el-form-item label="职责描述" prop="responsibilities">
          <el-input
            v-model="form.responsibilities"
            type="textarea"
            :rows="3"
            placeholder="岗位主要职责，可多条，以 1. 2. 形式列出image.png"
          />
        </el-form-item>
        <el-form-item label="任职要求" prop="requirements">
          <el-input
            v-model="form.requirements"
            type="textarea"
            :rows="3"
            placeholder="候选人需要具备的技能与经验"
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
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import {
  getPositionListApi,
  createPositionApi,
  updatePositionApi,
  deletePositionApi,
  getPositionDetailApi,
  type AdminPositionItem,
} from '@/api/admin';

// 路由实例，用于跳转详情页
const router = useRouter();
// 加载状态与岗位数据
const loading = ref(false);
const list = ref<AdminPositionItem[]>([]);

// 对话框与表单相关状态
const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
// 编辑弹窗内的加载状态（用于从后端拉取岗位详情时）
const dialogLoading = ref(false);

// 表单数据模型
const form = reactive({
  name: '',
  sortOrder: 0,
  city: '',
  workExperience: '',
  education: '',
  salaryMin: 20000,
  salaryMax: 40000,
  responsibilities: '',
  requirements: '',
  tags: '',
});

// 表单校验规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
};

/** 拉取岗位列表 */
async function fetchList() {
  loading.value = true;
  try {
    list.value = await getPositionListApi();
  } finally {
    loading.value = false;
  }
}

/** 打开新增 / 编辑对话框
 *  新增时使用默认表单值；
 *  编辑时从后端拉取最新岗位详情并填入表单，保证表单字段与接口完全一致。
 */
async function openDialog(row?: AdminPositionItem) {
  if (!row) {
    // 新增岗位：重置表单为默认值
    editId.value = null;
    resetForm();
    dialogVisible.value = true;
    return;
  }

  // 编辑岗位：先打开弹窗并展示 loading，再根据 id 拉详情
  editId.value = row.id;
  dialogVisible.value = true;
  dialogLoading.value = true;
  try {
    const detail = await getPositionDetailApi(row.id);
    form.name = detail.name || '';
    form.sortOrder = detail.sortOrder ?? 0;
    form.city = (detail.city as string) || '';
    form.workExperience = (detail.workExperience as string) || '';
    form.education = (detail.education as string) || '';
    form.salaryMin = (detail.salaryMin as number) ?? 20000;
    form.salaryMax = (detail.salaryMax as number) ?? 40000;
    form.responsibilities = (detail.responsibilities as string) || '';
    form.requirements = (detail.requirements as string) || '';
    const tagField = detail.tags;
    form.tags = Array.isArray(tagField) ? tagField.join(',') : (tagField as string) || '';
  } catch (e) {
    ElMessage.error((e as Error).message || '获取岗位详情失败');
  } finally {
    dialogLoading.value = false;
  }
}

/** 关闭弹窗时重置表单 */
function resetForm() {
  form.name = '';
  form.sortOrder = 0;
  form.city = '';
  form.workExperience = '';
  form.education = '';
  form.salaryMin = 20000;
  form.salaryMax = 40000;
  form.responsibilities = '';
  form.requirements = '';
  form.tags = '';
  formRef.value?.resetFields();
}

/** 提交表单：根据是否有 editId 决定新增或更新 */
async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editId.value) {
        await updatePositionApi(editId.value, {
          name: form.name,
          sortOrder: form.sortOrder,
          city: form.city || undefined,
          workExperience: form.workExperience || undefined,
          education: form.education || undefined,
          salaryMin: form.salaryMin || undefined,
          salaryMax: form.salaryMax || undefined,
          responsibilities: form.responsibilities || undefined,
          requirements: form.requirements || undefined,
          tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
        });
        ElMessage.success('更新成功');
      } else {
        await createPositionApi({
          name: form.name,
          sortOrder: form.sortOrder,
          city: form.city || undefined,
          workExperience: form.workExperience || undefined,
          education: form.education || undefined,
          salaryMin: form.salaryMin || undefined,
          salaryMax: form.salaryMax || undefined,
          responsibilities: form.responsibilities || undefined,
          requirements: form.requirements || undefined,
          tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
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

/** 删除单条岗位数据 */
async function onDelete(row: AdminPositionItem) {
  await ElMessageBox.confirm(`确定删除岗位「${row.name}」吗？`, '提示', {
    type: 'warning',
  });
  await deletePositionApi(row.id);
  ElMessage.success('删除成功');
  fetchList();
}

/** 跳转到岗位详情页，展示更完整的岗位信息结构 */
function goDetail(row: AdminPositionItem) {
  router.push({ name: 'AdminPositionDetail', params: { id: row.id } });
}

// 页面加载时获取岗位列表
onMounted(fetchList);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.salary-range {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.salary-sep {
  padding: 0 4px;
}

/* 让两个数字输入框按比例平分可用宽度，总体与上方输入框对齐 */
.salary-range :deep(.el-input-number) {
  flex: 1 1 0;
  max-width: 100%;
}

/* 隐藏薪资范围输入框左右的加减按钮，仅保留数字输入区域 */
.salary-range :deep(.el-input-number__decrease),
.salary-range :deep(.el-input-number__increase) {
  display: none;
}

.salary-range :deep(.el-input__inner) {
  text-align: left;
}
</style>

