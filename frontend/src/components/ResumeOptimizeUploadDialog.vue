<template>
  <el-dialog
    :model-value="modelValue"
    title="上传简历"
    width="620px"
    align-center
    destroy-on-close
    append-to-body
    :close-on-click-modal="false"
    :before-close="beforeDialogClose"
    @update:model-value="onDialogModelUpdate"
  >
    <el-radio-group v-model="uploadMode" class="mode-radios">
      <el-radio-button label="file">上传文件</el-radio-button>
      <el-radio-button label="text">文字简历</el-radio-button>
      <el-radio-button label="library">我的简历</el-radio-button>
    </el-radio-group>

    <div class="dialog-body">
      <div v-show="uploadMode === 'file'" class="mode-block">
        <p class="mode-tip">支持 PDF、Word（doc / docx）、txt；非 PDF 将在本地转为 PDF 后再提交。可拖入文件或点击选择。</p>
        <el-upload
          class="resume-drop-upload"
          drag
          :show-file-list="false"
          :auto-upload="false"
          :limit="1"
          :disabled="confirmLoading"
          accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          :on-change="onResumeFileChange"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="el-upload__text">将简历拖到此处，或 <em>点击选择</em></div>
        </el-upload>
        <span v-if="pendingFileName" class="picked-name">已选：{{ pendingFileName }}</span>
      </div>

      <div v-show="uploadMode === 'text'" class="mode-block">
        <p class="mode-tip">简历名称将用于保存时的「原名」；正文将在本地排版并转为 PDF 后提交。</p>
        <el-input v-model="textTitle" class="title-input" placeholder="例如：张三-Java开发" clearable />
        <el-input
          v-model="resumePlainText"
          type="textarea"
          :rows="12"
          placeholder="在此粘贴或输入简历全文…"
          maxlength="200000"
          show-word-limit
        />
      </div>

      <div v-show="uploadMode === 'library'" class="mode-block">
        <p class="mode-tip">选择与「我的简历」列表一致的文件，将按静态地址拉取后用于优化。</p>
        <el-select
          v-model="libraryId"
          class="library-select"
          placeholder="选择已上传的简历"
          filterable
          clearable
          :loading="resumeListLoading"
        >
          <el-option v-for="opt in resumeOptions" :key="opt.id" :label="opt.name" :value="opt.id" />
        </el-select>
      </div>
    </div>

    <template #footer>
      <el-button @click="onDialogCancel" :disabled="confirmLoading">取消</el-button>
      <el-button type="primary" :loading="confirmLoading" @click="onDialogConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import type { UploadFile } from 'element-plus';
import { getResumeItemApi, getResumeListApi } from '@/api/resume';
import { RESUME_FILE_PUBLIC_BASE_URL } from '@/config/resumeAssets';
import { useResumeOptimizeDraftStore } from '@/store/resumeOptimizeDraft';
import { useUserStore } from '@/store/user';
import { plainTextResumeToPdfFile, resumeUploadToPdfFile } from '@/utils/resumeFileToPdf';

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    /** manage：简历管理页，取消仅关窗；preview：优化预览页，放弃时回列表 */
    context?: 'manage' | 'preview';
  }>(),
  { context: 'preview' }
);

const emit = defineEmits<{
  'update:modelValue': [boolean];
  /** 已成功写入草稿（PDF/文本/库） */
  confirmed: [];
}>();

const router = useRouter();
const userStore = useUserStore();
const draft = useResumeOptimizeDraftStore();

const uploadMode = ref<'file' | 'text' | 'library'>('file');
const pendingFile = ref<File | null>(null);
const pendingFileName = ref('');
const resumePlainText = ref('');
const textTitle = ref('');
const libraryId = ref<number | null>(null);
const resumeOptions = ref<{ id: number; name: string }[]>([]);
const resumeListLoading = ref(false);
const confirmLoading = ref(false);

function resetLocalForm() {
  uploadMode.value = 'file';
  pendingFile.value = null;
  pendingFileName.value = '';
  resumePlainText.value = '';
  textTitle.value = '';
  libraryId.value = null;
}

function isAllowedResumeFile(file: File): boolean {
  const n = (file.name || '').toLowerCase();
  if (/\.(pdf|docx?|txt)$/i.test(n)) return true;
  const t = file.type || '';
  if (
    t === 'application/pdf' ||
    t === 'application/msword' ||
    t === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    t === 'text/plain'
  ) {
    return true;
  }
  return false;
}

async function fileFromMyResume(resumeId: number): Promise<{ file: File; displayName: string }> {
  const item = await getResumeItemApi(resumeId);
  const fileKey = String(item?.unique_filename || item?.filename || '').trim();
  if (!fileKey) {
    throw new Error('未获取到简历文件路径，无法下载');
  }
  const url = `${RESUME_FILE_PUBLIC_BASE_URL}${encodeURIComponent(fileKey)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`下载简历失败（HTTP ${res.status}）`);
  }
  const blob = await res.blob();
  const baseName = String(item.filename || fileKey).split(/[/\\]/).pop() || 'resume.pdf';
  const mime = blob.type && blob.type !== 'application/octet-stream' ? blob.type : 'application/pdf';
  const file = new File([blob], baseName, { type: mime });
  const displayName = String(item.filename || baseName);
  return { file, displayName };
}

async function loadMyResumeOptions() {
  const uid = userStore.userInfo?.id;
  if (!uid) return;
  resumeListLoading.value = true;
  try {
    const res = await getResumeListApi(uid, 1, 100);
    const list = Array.isArray(res?.items) ? res.items : [];
    resumeOptions.value = list.map((it) => ({
      id: Number(it.id),
      name: String(it.filename || '未命名简历'),
    }));
  } catch {
    /* 忽略 */
  } finally {
    resumeListLoading.value = false;
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    if (props.context === 'manage') {
      draft.reset();
      resetLocalForm();
    }
    void loadMyResumeOptions();
  }
);

function onDialogModelUpdate(v: boolean) {
  emit('update:modelValue', v);
}

function onResumeFileChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw;
  if (!raw) return;
  if (!isAllowedResumeFile(raw)) {
    ElMessage.error('请上传 PDF、Word（doc / docx）或 txt 文件');
    return;
  }
  pendingFile.value = raw;
  pendingFileName.value = raw.name;
}

async function onDialogConfirm() {
  if (uploadMode.value === 'file') {
    const f = pendingFile.value;
    if (!f) {
      ElMessage.warning('请先选择或拖入简历文件');
      return;
    }
    confirmLoading.value = true;
    try {
      const pdfFile = await resumeUploadToPdfFile(f);
      draft.setFromPdfFile(pdfFile);
      emit('update:modelValue', false);
      emit('confirmed');
    } catch (e: unknown) {
      ElMessage.error((e as Error).message || '文件处理失败');
    } finally {
      confirmLoading.value = false;
    }
    return;
  }
  if (uploadMode.value === 'text') {
    const t = resumePlainText.value.trim();
    if (!t) {
      ElMessage.warning('请输入简历文本');
      return;
    }
    confirmLoading.value = true;
    try {
      const baseTitle = (textTitle.value || '文本简历').trim() || '文本简历';
      const pdfFile = await plainTextResumeToPdfFile(resumePlainText.value, baseTitle);
      draft.setFromPdfFile(pdfFile);
      emit('update:modelValue', false);
      emit('confirmed');
    } catch (e: unknown) {
      ElMessage.error((e as Error).message || '生成 PDF 失败');
    } finally {
      confirmLoading.value = false;
    }
    return;
  }
  const id = libraryId.value;
  if (id == null) {
    ElMessage.warning('请从「我的简历」中选择一份简历');
    return;
  }
  confirmLoading.value = true;
  try {
    const { file, displayName } = await fileFromMyResume(id);
    const pdfFile = await resumeUploadToPdfFile(file);
    draft.setFromPdfFile(pdfFile, displayName);
    emit('update:modelValue', false);
    emit('confirmed');
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '获取简历失败');
  } finally {
    confirmLoading.value = false;
  }
}

function onDialogCancel() {
  if (props.context === 'manage') {
    emit('update:modelValue', false);
    resetLocalForm();
    return;
  }
  if (draft.hasPreview) {
    emit('update:modelValue', false);
    return;
  }
  void ElMessageBox.confirm('尚未确认简历来源，是否返回我的简历？', '提示', {
    type: 'warning',
    confirmButtonText: '返回',
    cancelButtonText: '继续编辑',
  })
    .then(() => {
      draft.reset();
      emit('update:modelValue', false);
      router.push({ name: 'HomeResume' });
    })
    .catch(() => {});
}

function beforeDialogClose(done: (cancel?: boolean) => void) {
  if (confirmLoading.value) {
    done(false);
    return;
  }
  if (props.context === 'manage') {
    resetLocalForm();
    done();
    return;
  }
  if (draft.hasPreview) {
    done();
    return;
  }
  void ElMessageBox.confirm('尚未确认简历来源，是否返回我的简历？', '提示', {
    type: 'warning',
    confirmButtonText: '返回',
    cancelButtonText: '留在本页',
  })
    .then(() => {
      draft.reset();
      emit('update:modelValue', false);
      router.push({ name: 'HomeResume' });
      done();
    })
    .catch(() => {
      done(false);
    });
}
</script>

<style scoped>
.mode-radios {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.dialog-body {
  min-height: 200px;
}
.mode-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mode-tip {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}
.resume-drop-upload {
  width: 100%;
}
.resume-drop-upload :deep(.el-upload) {
  width: 100%;
}
.resume-drop-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 28px 16px;
  border-radius: 12px;
}
.upload-icon {
  font-size: 42px;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}
.picked-name {
  font-size: 13px;
  color: #4b5563;
  word-break: break-all;
}
.title-input {
  max-width: 100%;
}
.library-select {
  width: 100%;
  max-width: 400px;
}
</style>
