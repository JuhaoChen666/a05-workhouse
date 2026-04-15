<template>
  <section class="optimize-run-page theme-page-shell fade-in-up delay-1">
    <div class="toolbar theme-card">
      <div class="toolbar-text">
        <h3>简历优化</h3>
        <p>正在基于「{{ draft.originalFilename || '简历' }}」进行 AI 优化，请等待进度完成。</p>
      </div>
      <div class="toolbar-actions">
        <el-button class="back-btn" @click="goPreview">返回预览</el-button>
        <el-button class="back-btn" @click="goResumeList">返回我的简历</el-button>
      </div>
    </div>

    <p v-if="errorMsg" class="error-banner theme-card">{{ errorMsg }}</p>

    <div v-if="showProgress" class="block theme-card">
      <h4>优化进度</h4>
      <el-progress :percentage="Math.min(100, Math.max(0, progress))" :status="progressStatus" />
      <p class="status-line">{{ statusHint }}</p>
    </div>

    <div v-if="showTextPreviewCard" class="block theme-card">
      <h4>解析预览</h4>
      <div class="preview-text">{{ textPreview }}</div>
    </div>

    <div v-if="resultMarkdown" class="block theme-card result-block">
      <h4>优化结果</h4>
      <div class="result-md">{{ resultMarkdown }}</div>
      <div class="result-actions">
        <el-button @click="downloadMarkdown">保存 Markdown 到本地</el-button>
        <el-button @click="downloadExport" :loading="exporting">导出简历文件</el-button>
        <el-button type="primary" class="theme-primary-btn" :loading="savingResume" @click="saveToMyResumes">
          保存到我的简历
        </el-button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  exportResumeOptimizeBlob,
  getResumeOptimizeStatusApi,
  importResumeOptimizeApi,
  startResumeOptimizeApi,
} from '@/api/resumeOptimize';
import { uploadResumeApi } from '@/api/resume';
import { useResumeOptimizeDraftStore } from '@/store/resumeOptimizeDraft';
import { useUserStore } from '@/store/user';
import {
  buildOptimizedResumeMarkdownFilename,
  buildOptimizedResumePdfFilename,
} from '@/utils/resumeOptimizeFilename';

const router = useRouter();
const userStore = useUserStore();
const draft = useResumeOptimizeDraftStore();

const busy = ref(false);
const errorMsg = ref('');
const sessionId = ref('');
const textPreview = ref('');
const progress = ref(0);
const pollStatus = ref('');
const resultMarkdown = ref('');
const exporting = ref(false);
const savingResume = ref(false);
const pipelineStarted = ref(false);

let pollTimer: ReturnType<typeof setInterval> | null = null;

const showProgress = computed(() => busy.value || (pollStatus.value && !resultMarkdown.value && !errorMsg.value));
const optimizeFinished = computed(
  () => (pollStatus.value === 'completed' && progress.value >= 100) || Boolean(resultMarkdown.value)
);
const showTextPreviewCard = computed(() => Boolean(textPreview.value) && !optimizeFinished.value);
const statusHint = computed(() => {
  if (pollStatus.value === 'completed') return '优化已完成';
  if (pollStatus.value === 'failed' || pollStatus.value === 'error') return '优化失败';
  if (busy.value && !sessionId.value) return '正在上传并解析简历…';
  if (sessionId.value && !resultMarkdown.value) return `当前状态：${pollStatus.value || '处理中'}…`;
  return '';
});
const progressStatus = computed(() => {
  if (pollStatus.value === 'failed' || pollStatus.value === 'error') return 'exception' as const;
  if (pollStatus.value === 'completed' && progress.value >= 100) return 'success' as const;
  return undefined;
});

function goPreview() {
  stopPolling();
  busy.value = false;
  void router.push({ name: 'HomeResumeOptimize' });
}

function goResumeList() {
  stopPolling();
  draft.reset();
  void router.push({ name: 'HomeResume' });
}

function stopPolling() {
  if (pollTimer != null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onBeforeUnmount(() => {
  stopPolling();
});

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function pollOnce() {
  if (!sessionId.value) return;
  try {
    const data = await getResumeOptimizeStatusApi(sessionId.value);
    progress.value = typeof data.progress === 'number' ? data.progress : 0;
    pollStatus.value = String(data.status || '');
    if (data.result_markdown) {
      resultMarkdown.value = data.result_markdown;
    }
    const failed = pollStatus.value === 'failed' || pollStatus.value === 'error';
    const done = pollStatus.value === 'completed' && progress.value >= 100;
    if (done || failed) {
      stopPolling();
      busy.value = false;
      if (failed) {
        errorMsg.value = '优化未成功完成，请稍后重试或更换文件。';
        ElMessage.error(errorMsg.value);
      } else {
        ElMessage.success('简历优化完成');
      }
    }
  } catch (e: unknown) {
    stopPolling();
    busy.value = false;
    errorMsg.value = (e as Error).message || '轮询状态失败';
    ElMessage.error(errorMsg.value);
  }
}

function startPolling() {
  stopPolling();
  void pollOnce();
  pollTimer = setInterval(() => void pollOnce(), 1600);
}

async function runPipelineFromDraft() {
  const uid = userStore.userInfo?.id;
  const file = draft.payloadFile;
  if (!uid || !file) {
    return;
  }

  errorMsg.value = '';
  textPreview.value = '';
  resultMarkdown.value = '';
  sessionId.value = '';
  progress.value = 0;
  pollStatus.value = '';
  busy.value = true;
  stopPolling();

  try {
    const imported = await importResumeOptimizeApi(uid, file);
    sessionId.value = imported.session_id;
    textPreview.value = imported.text_preview?.trim() || '';

    await startResumeOptimizeApi(sessionId.value);
    startPolling();
  } catch (e: unknown) {
    busy.value = false;
    errorMsg.value = (e as Error).message || '上传或启动优化失败';
    ElMessage.error(errorMsg.value);
  }
}

onMounted(() => {
  if (pipelineStarted.value) return;
  const uid = userStore.userInfo?.id;
  const file = draft.payloadFile;
  if (!uid || !file) {
    ElMessage.warning('请先完成简历选择与预览');
    void router.replace({ name: 'HomeResumeOptimize' });
    return;
  }
  pipelineStarted.value = true;
  void runPipelineFromDraft();
});

function downloadMarkdown() {
  const md = resultMarkdown.value;
  if (!md) {
    ElMessage.warning('暂无可下载内容');
    return;
  }
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  triggerDownload(blob, buildOptimizedResumeMarkdownFilename(draft.originalFilename));
  ElMessage.success('已开始下载');
}

async function downloadExport() {
  if (!sessionId.value) {
    ElMessage.warning('缺少会话，无法导出');
    return;
  }
  exporting.value = true;
  try {
    const { blob, filename } = await exportResumeOptimizeBlob(sessionId.value);
    const preferPdf = buildOptimizedResumePdfFilename(draft.originalFilename);
    const outName =
      blob.type === 'application/pdf' || /\.pdf$/i.test(filename) ? preferPdf : filename;
    triggerDownload(blob, outName);
    ElMessage.success('已开始下载');
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '导出失败');
  } finally {
    exporting.value = false;
  }
}

async function saveToMyResumes() {
  const uid = userStore.userInfo?.id;
  if (!uid) {
    ElMessage.warning('请先登录');
    return;
  }
  savingResume.value = true;
  try {
    let file: File | null = null;
    const orig = draft.originalFilename || '简历.pdf';
    if (sessionId.value) {
      try {
        const { blob, filename } = await exportResumeOptimizeBlob(sessionId.value);
        const isPdf = blob.type === 'application/pdf' || /\.pdf$/i.test(filename);
        if (isPdf) {
          const name = buildOptimizedResumePdfFilename(orig);
          file = new File([blob], name, { type: 'application/pdf' });
        }
      } catch {
        /* 改用 Markdown */
      }
    }
    if (!file && resultMarkdown.value) {
      const name = buildOptimizedResumeMarkdownFilename(orig);
      file = new File([resultMarkdown.value], name, { type: 'text/markdown' });
    }
    if (!file) {
      ElMessage.warning('没有可上传的优化结果');
      return;
    }
    await uploadResumeApi(uid, file);
    ElMessage.success('已保存到我的简历');
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '保存失败');
  } finally {
    savingResume.value = false;
  }
}
</script>

<style scoped>
.optimize-run-page {
  display: grid;
  gap: clamp(12px, 1.1vw, 18px);
}
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: clamp(14px, 1.2vw, 18px);
  gap: 14px;
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
  max-width: 640px;
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.back-btn {
  border-color: #d1d5db !important;
  color: #374151 !important;
  background: #ffffff !important;
  border-radius: 10px !important;
}
.back-btn:hover {
  border-color: #c4b5fd !important;
  color: #6d28d9 !important;
  background: #f5f3ff !important;
}
.error-banner {
  margin: 0;
  padding: 12px 16px;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
}
.block {
  padding: clamp(14px, 1.2vw, 18px);
}
.block h4 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #111827;
  font-weight: 700;
}
.preview-text,
.result-md {
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  color: #374151;
  font-size: 13px;
  background: #f9fafb;
  border-radius: 10px;
  padding: 12px 14px;
}
.result-block .result-md {
  max-height: min(55vh, 520px);
}
.status-line {
  margin: 10px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}
@media (max-width: 768px) {
  .toolbar-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
