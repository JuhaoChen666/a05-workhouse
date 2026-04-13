<template>
  <section class="resume-page theme-page-shell fade-in-up delay-1">
    <div class="resume-toolbar theme-card">
      <div class="toolbar-text">
        <h3>我的简历</h3>
        <p>支持上传、在线预览与管理，简历将用于后续面试配置。</p>
      </div>
      <div class="resume-upload-area">
        <el-button class="optimize-btn" @click="openOptimizeDialog">简历优化</el-button>
        <el-upload
          :show-file-list="false"
          :auto-upload="false"
          accept=".pdf,application/pdf"
          :on-change="handleResumeFileChange"
        >
          <el-button type="primary" class="theme-primary-btn">上传简历</el-button>
        <span class="resume-upload-tip">*仅支持pdf格式文件</span>

        </el-upload>
      </div>
    </div>

    <div class="table-wrap theme-card">
      <el-table :data="resumeList" stripe>
        <el-table-column prop="name" label="简历名称" min-width="280" show-overflow-tooltip />
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
        <el-table-column prop="content" label="摘要">
          <template #default="{ row }">
            {{ row.content.slice(0, 60) || '暂无内容' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewResume(row)">查看</el-button>
            <el-button link type="danger" @click="removeResume(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-if="total > 0" class="pagination-wrap theme-card">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :page-sizes="[5, 10, 20, 50]"
        @current-change="onCurrentPageChange"
        @size-change="onPageSizeChange"
      />
    </div>
    <el-empty v-if="resumeList.length === 0" description="暂无简历，请先上传" :image-size="72" />

    <el-dialog v-model="previewVisible" title="简历在线预览" width="900px" append-to-body>
      <h4 class="dialog-title">{{ currentResume?.name || '--' }}</h4>
      <div v-if="previewLoading" class="dialog-content">预览加载中...</div>
      <div v-else-if="previewError" class="dialog-content">{{ previewError }}</div>
      <ResumePdfPreview v-else-if="previewSrc" :src="previewSrc" variant="dialog" />
      <div v-else class="dialog-content">暂无可预览内容</div>
    </el-dialog>

    <ResumeOptimizeUploadDialog
      v-model="optimizeUploadDialogVisible"
      context="manage"
      @confirmed="onOptimizeUploadConfirmed"
    />

    <el-dialog v-model="uploadPreviewVisible" title="上传前预览" width="900px" append-to-body>
      <h4 class="dialog-title">{{ pendingUploadName || '--' }}</h4>
      <ResumePdfPreview v-if="uploadPreviewSrc" :src="uploadPreviewSrc" variant="dialog" />
      <div v-else class="dialog-content">暂无可预览内容</div>
      <template #footer>
        <el-button @click="cancelPendingUpload">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmUploadResume">确认上传</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import { deleteResumeApi, getResumeItemApi, getResumeListApi, uploadResumeApi } from '@/api/resume';
import { RESUME_FILE_PUBLIC_BASE_URL } from '@/config/resumeAssets';
import { useUserStore } from '@/store/user';
import ResumePdfPreview from '@/components/ResumePdfPreview.vue';
import ResumeOptimizeUploadDialog from '@/components/ResumeOptimizeUploadDialog.vue';

type ResumeItem = { id: number; name: string; content: string; updatedAt: string };
const resumeList = ref<ResumeItem[]>([]);
const router = useRouter();
const userStore = useUserStore();
const previewVisible = ref(false);
const currentResume = ref<ResumeItem | null>(null);
const previewLoading = ref(false);
const previewError = ref('');
const previewSrc = ref('');
let previewObjectUrl = '';
const uploadPreviewVisible = ref(false);
const uploading = ref(false);
const pendingUploadFile = ref<File | null>(null);
const pendingUploadName = ref('');
const uploadPreviewSrc = ref('');
let uploadPreviewObjectUrl = '';
const currentPage = ref(1);
const pageSize = ref(5);
const total = ref(0);
const optimizeUploadDialogVisible = ref(false);

function openOptimizeDialog() {
  optimizeUploadDialogVisible.value = true;
}

function onOptimizeUploadConfirmed() {
  void router.push({ name: 'HomeResumeOptimize' });
}

function nowText() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatUploadedAt(input?: string) {
  if (!input) return nowText();
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return nowText();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function fetchResumeList() {
  const userId = userStore.userInfo?.id;
  if (!userId) return;
  try {
    const res = await getResumeListApi(userId, currentPage.value, pageSize.value);
    const list = Array.isArray(res?.items) ? res.items : [];
    total.value = Number(res?.total || 0);
    resumeList.value = list.map((it) => ({
      id: Number(it.id),
      name: String(it.filename || '未命名简历'),
      content: '',
      updatedAt: formatUploadedAt(it.uploaded_at),
    }));
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '获取简历列表失败');
  }
}

function clearUploadPreviewObjectUrl() {
  if (!uploadPreviewObjectUrl) return;
  URL.revokeObjectURL(uploadPreviewObjectUrl);
  uploadPreviewObjectUrl = '';
}

function handleResumeFileChange(file: { name?: string; raw?: File }) {
  const raw = file.raw;
  const filename = String(file?.name || '').trim().toLowerCase();
  const isPdf = filename.endsWith('.pdf') || raw?.type === 'application/pdf';
  if (!isPdf) {
    ElMessage.error('仅支持上传 PDF 格式简历');
    return;
  }
  if (!raw) {
    ElMessage.error('上传文件无效');
    return;
  }
  clearUploadPreviewObjectUrl();
  uploadPreviewObjectUrl = URL.createObjectURL(raw);
  uploadPreviewSrc.value = uploadPreviewObjectUrl;
  pendingUploadFile.value = raw;
  pendingUploadName.value = String(file?.name || raw.name || '未命名简历');
  uploadPreviewVisible.value = true;
}

function cancelPendingUpload() {
  uploadPreviewVisible.value = false;
  pendingUploadFile.value = null;
  pendingUploadName.value = '';
  uploadPreviewSrc.value = '';
  clearUploadPreviewObjectUrl();
}

async function confirmUploadResume() {
  const userId = userStore.userInfo?.id;
  const file = pendingUploadFile.value;
  if (!userId) {
    ElMessage.error('未获取到用户信息，请重新登录后重试');
    return;
  }
  if (!file) {
    ElMessage.error('上传文件无效');
    return;
  }
  uploading.value = true;
  try {
    await uploadResumeApi(userId, file);
    currentPage.value = 1;
    await fetchResumeList();
    cancelPendingUpload();
    ElMessage.success('简历上传成功');
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '简历上传失败');
  } finally {
    uploading.value = false;
  }
}

async function removeResume(id: number) {
  const userId = userStore.userInfo?.id;
  const target = resumeList.value.find((r) => r.id === id);
  if (!userId || !target) return;
  try {
    await ElMessageBox.confirm(
      `确认删除简历「${target.name}」吗？此操作不可撤销。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      }
    );
    await deleteResumeApi({
      id,
      user_id: userId,
      filename: target.name,
    });
    await fetchResumeList();
    if (resumeList.value.length === 0 && currentPage.value > 1) {
      currentPage.value -= 1;
      await fetchResumeList();
    }
    ElMessage.success('简历已删除');
  } catch (e: unknown) {
    if (e === 'cancel' || e === 'close') return;
    ElMessage.error((e as Error).message || '删除简历失败');
  }
}

function onCurrentPageChange(page: number) {
  currentPage.value = page;
  void fetchResumeList();
}

function onPageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
  void fetchResumeList();
}

function clearPreviewObjectUrl() {
  if (!previewObjectUrl) return;
  URL.revokeObjectURL(previewObjectUrl);
  previewObjectUrl = '';
}

async function viewResume(row: ResumeItem) {
  currentResume.value = row;
  previewVisible.value = true;
  previewLoading.value = true;
  previewError.value = '';
  previewSrc.value = '';
  clearPreviewObjectUrl();
  try {
    const item = await getResumeItemApi(row.id);
    const fileKey = String(item?.unique_filename || item?.filename || '').trim();
    if (!fileKey) {
      previewError.value = '未获取到简历文件名，无法预览';
      return;
    }
    previewSrc.value = `${RESUME_FILE_PUBLIC_BASE_URL}${encodeURIComponent(fileKey)}`;
  } catch (e: unknown) {
    previewError.value = (e as Error).message || '获取简历详情失败';
  } finally {
    previewLoading.value = false;
  }
}

onMounted(() => {
  void fetchResumeList();
});

onBeforeUnmount(() => {
  clearPreviewObjectUrl();
  clearUploadPreviewObjectUrl();
});
</script>

<style scoped>
.resume-page { display: grid; gap: clamp(12px, 1.1vw, 18px); }
.resume-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: clamp(14px, 1.2vw, 18px);
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-text h3 {
  margin: 0 0 6px;
  color: #111827;
  font-size: clamp(16px, 1.2vw, 18px);
  font-weight: 700;
}
.toolbar-text p {
  margin: 0;
  color: #6b7280;
  font-size: clamp(12px, 0.9vw, 14px);
  line-height: 1.6;
}
.resume-upload-area {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-direction: column;
  gap: 8px;
}
.optimize-btn {
  border-color: #d1d5db !important;
  color: #374151 !important;
  background: #ffffff !important;
  border-radius: 10px !important;
}
.optimize-btn:hover {
  border-color: #c4b5fd !important;
  color: #6d28d9 !important;
  background: #f5f3ff !important;
}
.resume-upload-tip {
  width: max-content;
  position: absolute;
  font-size: clamp(10px, 0.8vw, 11px);
  color: #909399;
  top: 105%;
}
.table-wrap {
  padding: 8px;
}
:deep(.table-wrap .el-table) {
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #f8f7ff;
  border-radius: 12px;
}
:deep(.table-wrap .el-table th.el-table__cell) {
  color: #4b5563;
  font-weight: 700;
}
:deep(.table-wrap .el-table td.el-table__cell) {
  color: #1f2937;
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
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 10px 12px;
}
:deep(.pagination-wrap .el-pagination) {
  width: 100%;
  justify-content: flex-end;
}
@media (max-width: 768px) {
  .resume-toolbar {
    align-items: stretch;
  }
  .resume-upload-area {
    width: 100%;
    align-items: flex-start;
    flex-direction:row;
  }
  .resume-upload-tip {
    position: static;
    margin-top: -4px;
  }
}
</style>
