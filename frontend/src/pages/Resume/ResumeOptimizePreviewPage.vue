<template>
  <section class="preview-page theme-page-shell fade-in-up delay-1">
    <div class="toolbar theme-card">
      <div class="toolbar-text">
        <h3>简历优化</h3>
        <p>简历来源已在「我的简历」页确认。请核对预览无误后点击「开始优化」；需要更换可点「重新选择」。</p>
      </div>
      <div class="toolbar-actions">
        <el-button class="back-btn" @click="goResumeList">返回我的简历</el-button>
        <el-button v-if="draft.hasPreview" :disabled="goingRun" @click="rechoose">重新选择简历</el-button>
        <el-button
          v-if="draft.hasPreview"
          type="primary"
          class="theme-primary-btn"
          :loading="goingRun"
          @click="goRunOptimize"
        >
          开始优化
        </el-button>
      </div>
    </div>

    <div v-if="draft.hasPreview" class="preview-panel theme-card">
      <h4>简历预览</h4>
      <p class="preview-meta">来源文件名：{{ draft.originalFilename }}</p>
      <ResumePdfPreview
        v-if="draft.previewKind === 'pdf' && draft.previewPdfObjectUrl"
        :src="draft.previewPdfObjectUrl"
        variant="optimize"
      />
      <div v-else-if="draft.previewKind === 'text'" class="text-preview">{{ draft.previewText }}</div>
      <el-empty v-else description="暂无可预览内容" />
    </div>

    <div v-else class="empty-wrap theme-card">
      <el-empty description="请从「我的简历」页点击「简历优化」，在弹窗中确认简历后再进入本页" :image-size="72">
        <el-button type="primary" @click="goResumeList">去我的简历</el-button>
      </el-empty>
    </div>

    <ResumeOptimizeUploadDialog v-model="dialogVisible" context="preview" />
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import ResumePdfPreview from '@/components/ResumePdfPreview.vue';
import ResumeOptimizeUploadDialog from '@/components/ResumeOptimizeUploadDialog.vue';
import { useResumeOptimizeDraftStore } from '@/store/resumeOptimizeDraft';

const router = useRouter();
const draft = useResumeOptimizeDraftStore();

const dialogVisible = ref(false);
const goingRun = ref(false);

onMounted(() => {
  draft.ensurePdfPreviewUrl();
  dialogVisible.value = !draft.hasPreview;
});

watch(
  () => draft.hasPreview,
  (has) => {
    if (!has) {
      dialogVisible.value = true;
    }
  }
);

onBeforeUnmount(() => {
  draft.revokePdfPreviewUrl();
});

function goResumeList() {
  draft.reset();
  router.push({ name: 'HomeResume' });
}

function rechoose() {
  draft.reset();
  dialogVisible.value = true;
}

async function goRunOptimize() {
  if (!draft.payloadFile) {
    return;
  }
  goingRun.value = true;
  try {
    await router.push({ name: 'HomeResumeOptimizeRun' });
  } finally {
    goingRun.value = false;
  }
}
</script>

<style scoped>
.preview-page {
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
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
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
.preview-panel {
  padding: clamp(14px, 1.2vw, 18px);
}
.preview-panel h4 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #111827;
  font-weight: 700;
}
.preview-meta {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
}
.text-preview {
  max-height: min(72vh, 720px);
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  padding: 14px;
  background: #f9fafb;
  border-radius: 10px;
  font-size: 13px;
  color: #374151;
}
.empty-wrap {
  padding: 24px;
}
</style>
