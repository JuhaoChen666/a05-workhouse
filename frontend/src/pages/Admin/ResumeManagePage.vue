<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>简历列表</span>
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
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="用户ID" width="100">
          <template #default="{ row }">
            {{ row.userId ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="上传时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.uploadedAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="onView(row)">查看</el-button>
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

    <el-dialog v-model="previewVisible" title="简历在线预览" width="900px" append-to-body>
      <h4 class="dialog-title">{{ currentResume?.filename || '--' }}</h4>
      <div v-if="previewLoading" class="dialog-content">预览加载中...</div>
      <div v-else-if="previewError" class="dialog-content">{{ previewError }}</div>
      <ResumePdfPreview v-else-if="previewSrc" :src="previewSrc" variant="dialog" />
      <div v-else class="dialog-content">暂无可预览内容</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getAdminResumePageApi, deleteAdminResumeApi, type AdminResumeItem } from '@/api/admin';
import { getResumeItemApi } from '@/api/resume';
import ResumePdfPreview from '@/components/ResumePdfPreview.vue';
import { RESUME_FILE_PUBLIC_BASE_URL } from '@/config/resumeAssets';

const loading = ref(false);
const list = ref<AdminResumeItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const userIdInput = ref('');
const queryUserId = ref<number | undefined>(undefined);
const previewVisible = ref(false);
const currentResume = ref<AdminResumeItem | null>(null);
const previewLoading = ref(false);
const previewError = ref('');
const previewSrc = ref('');

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

async function fetchList() {
  loading.value = true;
  try {
    const res = await getAdminResumePageApi({
      page: page.value,
      pageSize: pageSize.value,
      userId: queryUserId.value,
    });
    list.value = res.list || [];
    total.value = Number(res.total || 0);
  } catch (e) {
    ElMessage.error((e as Error).message || '加载简历列表失败');
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
  page.value = 1;
  void fetchList();
}

function onPageSizeChange() {
  page.value = 1;
  void fetchList();
}

async function onView(row: AdminResumeItem) {
  currentResume.value = row;
  previewVisible.value = true;
  previewLoading.value = true;
  previewError.value = '';
  previewSrc.value = '';
  try {
    const detail = await getResumeItemApi(row.id);
    const uniqueFilename = String(detail?.unique_filename || '').trim();
    if (!uniqueFilename) {
      previewError.value = '未获取到简历唯一文件名，无法预览';
      return;
    }
    previewSrc.value = `${RESUME_FILE_PUBLIC_BASE_URL}${encodeURIComponent(uniqueFilename)}`;
  } catch (e) {
    previewError.value = (e as Error).message || '获取简历详情失败';
  } finally {
    previewLoading.value = false;
  }
}

async function onDelete(row: AdminResumeItem) {
  await ElMessageBox.confirm(`确定删除简历「${row.filename || `#${row.id}`}」吗？`, '提示', {
    type: 'warning',
  });
  await deleteAdminResumeApi(row.id);
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

.pager-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.dialog-title {
  margin: 0 0 10px;
  font-size: 16px;
  color: #111827;
  font-weight: 700;
}

.dialog-content {
  max-height: 420px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.75;
  color: #374151;
}
</style>
