<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>面试会话列表</span>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model.trim="userIdInput"
          clearable
          placeholder="按用户 ID 查询（可选）"
          class="search-input"
          @keyup.enter="onSearch"
        />
        <el-select
          v-model="sortMode"
          class="sort-select"
          placeholder="排序方式"
          @change="onSortModeChange"
        >
          <el-option label="按更新时间倒序" value="updated_desc" />
          <el-option label="按创建时间正序" value="created_asc" />
        </el-select>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column type="expand" width="44">
          <template #default="{ row }">
            <div class="expand-content">
              <div><strong>岗位：</strong>{{ row.position || '-' }}</div>
              <div><strong>当前话题：</strong>{{ row.currentTopic || '-' }}</div>
              <div><strong>当前问题：</strong>{{ row.currentQuestion || '-' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sessionId" label="会话ID" min-width="280" show-overflow-tooltip />
        <el-table-column label="用户ID" width="100">
          <template #default="{ row }">
            {{ row.userId ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="position" label="岗位" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="100" />
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.updatedAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="onViewResume(row)">查看简历</el-button>
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

    <el-dialog v-model="resumeDialogVisible" title="简历内容" width="760px" append-to-body>
      <div class="resume-dialog-meta">
        <span>会话ID：{{ currentResumeSessionId || '--' }}</span>
      </div>
      <el-input
        v-model="resumeDialogContent"
        type="textarea"
        :rows="16"
        readonly
        resize="none"
        class="resume-dialog-textarea"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getAdminSessionPageApi, deleteAdminSessionApi, type AdminSessionItem } from '@/api/admin';

const loading = ref(false);
const list = ref<AdminSessionItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const userIdInput = ref('');
const queryUserId = ref<number | undefined>(undefined);
const sortMode = ref<'updated_desc' | 'created_asc'>('updated_desc');
const resumeDialogVisible = ref(false);
const resumeDialogContent = ref('');
const currentResumeSessionId = ref('');

function parseUserIdInput(raw: string): number | undefined {
  const text = String(raw || '').trim();
  if (!text) return undefined;
  const n = Number(text);
  if (!Number.isInteger(n) || n <= 0) return NaN;
  return n;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-';
  return String(value);
}

function statusLabel(status: string | null): string {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'completed') return '已完成';
  if (s === 'ended') return '已结束';
  if (s === 'questioning') return '进行中';
  return status || '-';
}

function statusTagType(status: string | null): 'success' | 'warning' | 'info' {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'completed') return 'success';
  if (s === 'questioning') return 'warning';
  return 'info';
}

async function fetchList() {
  loading.value = true;
  try {
    const sortBy = sortMode.value === 'updated_desc' ? 'updated_at' : 'created_at';
    const order = sortMode.value === 'updated_desc' ? 'desc' : 'asc';
    const res = await getAdminSessionPageApi({
      page: page.value,
      pageSize: pageSize.value,
      userId: queryUserId.value,
      order,
      sortBy,
    });
    list.value = res.list || [];
    total.value = Number(res.total || 0);
  } catch (e) {
    ElMessage.error((e as Error).message || '加载会话列表失败');
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  const userId = parseUserIdInput(userIdInput.value);
  if (Number.isNaN(userId)) {
    ElMessage.warning('用户ID需为正整数');
    return;
  }
  queryUserId.value = userId;
  page.value = 1;
  void fetchList();
}

function onReset() {
  userIdInput.value = '';
  queryUserId.value = undefined;
  sortMode.value = 'updated_desc';
  page.value = 1;
  void fetchList();
}

function onPageSizeChange() {
  page.value = 1;
  void fetchList();
}

function onSortModeChange() {
  page.value = 1;
  void fetchList();
}

function onViewResume(row: AdminSessionItem) {
  currentResumeSessionId.value = String(row.sessionId || '');
  resumeDialogContent.value = String(row.resume || '').trim() || '暂无简历内容';
  resumeDialogVisible.value = true;
}

async function onDelete(row: AdminSessionItem) {
  const sid = String(row.sessionId || '').trim();
  if (!sid) {
    ElMessage.warning('会话ID为空，无法删除');
    return;
  }
  await ElMessageBox.confirm(`确定删除会话「${sid}」吗？`, '提示', { type: 'warning' });
  await deleteAdminSessionApi(sid);
  ElMessage.success('删除成功');
  await fetchList();
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

.sort-select {
  width: min(100%, 220px);
}

.pager-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.expand-content {
  display: grid;
  gap: 8px;
  color: #374151;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.resume-dialog-meta {
  margin-bottom: 10px;
  color: #6b7280;
  font-size: 13px;
}

.resume-dialog-textarea :deep(.el-textarea__inner) {
  line-height: 1.6;
}
</style>
