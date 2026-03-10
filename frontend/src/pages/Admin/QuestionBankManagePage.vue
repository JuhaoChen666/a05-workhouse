<template>
  <!-- 题库管理页：支持按岗位筛选、增删改题目 -->
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>题库列表</span>
          <el-button type="primary" @click="openDialog()">新增题目</el-button>
        </div>
      </template>

      <!-- 筛选区域：按岗位筛选 -->
      <div class="filter">
        <el-select
          v-model="filterPositionId"
          placeholder="按岗位筛选"
          clearable
          style="width: 180px"
          @change="fetchList"
        >
          <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </div>

      <!-- 题库表格 -->
      <el-table v-loading="loading" :data="list" stripe max-height="500">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="positionName" label="岗位" width="100" />
        <el-table-column prop="question" label="题目" min-width="200" show-overflow-tooltip />
        <el-table-column prop="knowledgeTags" label="知识点标签" width="140" show-overflow-tooltip />
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

    <!-- 新增 / 编辑题目对话框 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑题目' : '新增题目'" width="560px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="岗位" prop="positionId">
          <el-select v-model="form.positionId" placeholder="请选择岗位" style="width: 100%">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="题目" prop="question">
          <el-input v-model="form.question" type="textarea" :rows="3" placeholder="面试题目内容" />
        </el-form-item>
        <el-form-item label="参考答案" prop="answer">
          <el-input v-model="form.answer" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="知识点标签" prop="knowledgeTags">
          <el-input v-model="form.knowledgeTags" placeholder="逗号分隔，如：Vue, 组件" />
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
  getQuestionBankListApi,
  createQuestionBankApi,
  updateQuestionBankApi,
  deleteQuestionBankApi,
  type AdminPositionItem,
  type AdminQuestionBankItem,
} from '@/api/admin';

// 加载状态与表格数据
const loading = ref(false);
const list = ref<AdminQuestionBankItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

// 岗位筛选与岗位下拉数据
const filterPositionId = ref<number | undefined>();
const positions = ref<AdminPositionItem[]>([]);

// 弹窗表单相关状态
const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

// 表单数据
const form = reactive({
  positionId: undefined as number | undefined,
  question: '',
  answer: '',
  knowledgeTags: '',
});

// 表单校验规则
const formRules: FormRules = {
  positionId: [{ required: true, message: '请选择岗位', trigger: 'change' }],
  question: [{ required: true, message: '请输入题目', trigger: 'blur' }],
};

/** 拉取题库列表 */
async function fetchList() {
  loading.value = true;
  try {
    const res = await getQuestionBankListApi({
      page: page.value,
      pageSize: pageSize.value,
      positionId: filterPositionId.value,
    });
    list.value = res.list;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

/** 加载岗位下拉数据 */
async function loadPositions() {
  positions.value = await getPositionListApi();
}

/** 打开新增 / 编辑对话框，并将行数据灌入表单 */
function openDialog(row?: AdminQuestionBankItem) {
  editId.value = row ? row.id : null;
  form.positionId = row ? row.positionId : undefined;
  form.question = row ? row.question : '';
  form.answer = row ? row.answer ?? '' : '';
  form.knowledgeTags = row ? row.knowledgeTags ?? '' : '';
  dialogVisible.value = true;
}

/** 关闭弹窗时重置表单 */
function resetForm() {
  form.positionId = undefined;
  form.question = '';
  form.answer = '';
  form.knowledgeTags = '';
  formRef.value?.resetFields();
}

/** 提交表单，新增或更新题目 */
async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid || form.positionId == null) return;
    submitLoading.value = true;
    try {
      if (editId.value) {
        await updateQuestionBankApi(editId.value, {
          positionId: form.positionId,
          question: form.question,
          answer: form.answer || undefined,
          knowledgeTags: form.knowledgeTags || undefined,
        });
        ElMessage.success('更新成功');
      } else {
        await createQuestionBankApi({
          positionId: form.positionId,
          question: form.question,
          answer: form.answer || undefined,
          knowledgeTags: form.knowledgeTags || undefined,
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

/** 删除单条题目 */
async function onDelete(row: AdminQuestionBankItem) {
  await ElMessageBox.confirm('确定删除该题目吗？', '提示', { type: 'warning' });
  await deleteQuestionBankApi(row.id);
  ElMessage.success('删除成功');
  fetchList();
}

// 页面加载时初始化岗位下拉与列表
onMounted(() => {
  loadPositions();
  fetchList();
});
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter {
  margin-bottom: 12px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>

