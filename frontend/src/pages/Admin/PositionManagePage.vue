<template>
  <!-- 岗位管理：GET /positions/page 分页；POST /positions + /admin/positions/info 新建；PUT /admin/positions/info 更新；DELETE /admin/positions/:id -->
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>岗位列表</span>
          <el-button type="primary" @click="openDialog()">新增岗位</el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="searchName"
          clearable
          placeholder="按岗位名称模糊搜索"
          class="search-input"
          @keyup.enter="onSearch"
        />
        <el-button type="primary" @click="onSearch">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="岗位名称" min-width="140" />
        <el-table-column prop="sortOrder" label="排序" width="88" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">详情</el-button>
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="fetchList"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

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
        label-width="120px"
      >
        <el-form-item label="岗位名称" prop="name">
          <el-input v-model="form.name" placeholder="如：数据库架构师" />
        </el-form-item>
        <el-form-item label="排序" prop="sortOrder">
          <el-input-number v-model="form.sortOrder" :min="0" />
        </el-form-item>
        <el-form-item label="岗位职责" prop="responsibility">
          <el-input
            v-model="form.responsibility"
            type="textarea"
            :rows="3"
            placeholder="如：负责数据库架构设计与优化"
          />
        </el-form-item>
        <el-form-item label="薪资（初级）" prop="salaryJunior">
          <el-input v-model="form.salaryJunior" placeholder="如：15k-20k" />
        </el-form-item>
        <el-form-item label="薪资（中级）" prop="salaryMid">
          <el-input v-model="form.salaryMid" placeholder="如：20k-30k" />
        </el-form-item>
        <el-form-item label="薪资（高级）" prop="salarySenior">
          <el-input v-model="form.salarySenior" placeholder="如：30k-40k" />
        </el-form-item>
        <el-form-item label="薪资（专家）" prop="salaryExpert">
          <el-input v-model="form.salaryExpert" placeholder="如：40k+" />
        </el-form-item>
        <el-form-item label="技能要求" prop="skillRequirements">
          <el-input
            v-model="form.skillRequirements"
            type="textarea"
            :rows="4"
            placeholder="任职要求、技能栈等"
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
  getPositionPageApi,
  createPositionBasicApi,
  createPositionInfoApi,
  updatePositionInfoApi,
  deletePositionApi,
  getPositionDetailApi,
  parseCreatedPositionId,
  type AdminPositionRow,
  type AdminPositionInfoPayload,
} from '@/api/admin';

const router = useRouter();

const loading = ref(false);
const list = ref<AdminPositionRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const searchName = ref('');
const queryName = ref('');

const dialogVisible = ref(false);
const editId = ref<number | null>(null);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const dialogLoading = ref(false);

const form = reactive({
  name: '',
  sortOrder: 0,
  responsibility: '',
  salaryJunior: '',
  salaryMid: '',
  salarySenior: '',
  salaryExpert: '',
  skillRequirements: '',
});

const rules: FormRules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
};

function strField(d: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = d[k];
    if (v != null && String(v).trim()) return String(v);
  }
  return '';
}

function applyDetailToForm(d: Record<string, unknown>) {
  form.name = strField(d, 'name');
  form.sortOrder = pickSortOrder(d);
  form.responsibility = strField(d, 'responsibility', 'responsibilities');
  form.salaryJunior = strField(d, 'salary_junior', 'salaryJunior');
  form.salaryMid = strField(d, 'salary_mid', 'salaryMid');
  form.salarySenior = strField(d, 'salary_senior', 'salarySenior');
  form.salaryExpert = strField(d, 'salary_expert', 'salaryExpert');
  form.skillRequirements = strField(d, 'skill_requirements', 'requirements', 'skillRequirements');
}

function pickSortOrder(d: Record<string, unknown>): number {
  const v = d.sort_order ?? d.sortOrder;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function buildInfoPayload(id: number): AdminPositionInfoPayload {
  return {
    id,
    name: form.name.trim(),
    responsibility: form.responsibility.trim(),
    salary_junior: form.salaryJunior.trim(),
    salary_mid: form.salaryMid.trim(),
    salary_senior: form.salarySenior.trim(),
    salary_expert: form.salaryExpert.trim(),
    skill_requirements: form.skillRequirements.trim(),
  };
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await getPositionPageApi({
      name: queryName.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    });
    list.value = res.list;
    total.value = res.total;
  } catch (e) {
    ElMessage.error((e as Error).message || '加载列表失败');
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  queryName.value = searchName.value.trim();
  page.value = 1;
  void fetchList();
}

function onPageSizeChange() {
  page.value = 1;
  void fetchList();
}

function resetForm() {
  form.name = '';
  form.sortOrder = 0;
  form.responsibility = '';
  form.salaryJunior = '';
  form.salaryMid = '';
  form.salarySenior = '';
  form.salaryExpert = '';
  form.skillRequirements = '';
  formRef.value?.resetFields();
}

async function openDialog(row?: AdminPositionRow) {
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
    const detail = (await getPositionDetailApi(row.id)) as Record<string, unknown>;
    applyDetailToForm(detail);
  } catch (e) {
    ElMessage.error((e as Error).message || '获取岗位详情失败');
    form.name = row.name;
    form.sortOrder = row.sortOrder;
  } finally {
    dialogLoading.value = false;
  }
}

async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    submitLoading.value = true;
    try {
      if (editId.value != null) {
        await updatePositionInfoApi(buildInfoPayload(editId.value));
        ElMessage.success('更新成功');
      } else {
        const created = await createPositionBasicApi({
          name: form.name.trim(),
          sort_order: form.sortOrder,
        });
        const newId = parseCreatedPositionId(created);
        if (!Number.isFinite(newId)) {
          throw new Error('创建岗位成功但未返回有效 ID，无法写入详情');
        }
        await createPositionInfoApi(buildInfoPayload(newId));
        ElMessage.success('新增成功');
      }
      dialogVisible.value = false;
      await fetchList();
    } catch (e) {
      ElMessage.error((e as Error).message || '提交失败');
    } finally {
      submitLoading.value = false;
    }
  });
}

async function onDelete(row: AdminPositionRow) {
  await ElMessageBox.confirm(`确定删除岗位「${row.name}」吗？`, '提示', {
    type: 'warning',
  });
  await deletePositionApi(row.id);
  ElMessage.success('删除成功');
  await fetchList();
}

function goDetail(row: AdminPositionRow) {
  router.push({ name: 'AdminPositionDetail', params: { id: row.id } });
}

onMounted(() => {
  void fetchList();
});
</script>

<style scoped>
.page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
  align-items: center;
}

.search-input {
  width: min(100%, 280px);
}

.pager-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
