<template>
  <div class="interview-settings-page theme-page-shell">
    <el-card class="settings-card theme-card fade-in-up delay-1" shadow="hover" v-loading="loading">
      <template #header>
      </template>

      <template v-if="job || !hasJobId">
        <p class="intro">请确认岗位并提供简历信息（文字输入或上传 PDF/Word），系统会自动匹配题库集合并开始面试。</p>

        <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px" class="settings-form">
          <el-form-item label="面试岗位" prop="positionName">
            <el-input v-model="form.positionName" placeholder="例如：移动端开发工程师(Android)" clearable />
          </el-form-item>

          <el-form-item label="面试模式">
            <el-radio-group v-model="interviewMode">
              <el-radio label="text">常规面试（文本+语音）</el-radio>
              <el-radio label="avatar">虚拟人面试</el-radio>
            </el-radio-group>
            <div class="mode-tip">
              常规面试内置文本与语音输入；虚拟人面试会在会话页展示虚拟人口播区域，鉴权由后端完成。
            </div>
          </el-form-item>

          <el-form-item v-if="interviewMode === 'avatar'" label="虚拟人形象">
            <el-select v-model="avatarId" placeholder="请选择虚拟人形象" class="avatar-select">
              <el-option label="虚拟人A（110592024）" value="110592024" />
              <el-option label="虚拟人B（110117005）" value="110117005" />
              <el-option label="虚拟人C（110017006）" value="110017006" />
            </el-select>
          </el-form-item>

          <el-form-item label="简历方式">
            <el-radio-group v-model="resumeInputMode">
              <el-radio label="text">文字输入</el-radio>
              <el-radio label="file">上传 PDF/Word</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="resumeInputMode === 'text'" label="简历内容" prop="resumeText">
            <el-input
              v-model="form.resumeText"
              type="textarea"
              :rows="7"
              placeholder="请输入简历摘要，例如：候选人张三，3年Android开发经验..."
            />
          </el-form-item>

          <el-form-item v-else label="简历文件" required>
            <el-upload
              class="upload-block"
              drag
              :show-file-list="true"
              :limit="1"
              :auto-upload="false"
              :file-list="fileList"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              accept=".pdf,.doc,.docx"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="el-upload__text">将文件拖到此处或 <em>点击上传</em></div>
              <div class="el-upload__tip">支持 PDF / Word（docx 优先，doc 视内容可能解析失败）</div>
            </el-upload>
          </el-form-item>
        </el-form>

        <div class="actions">
          <el-button @click="backToJobDetail">取消</el-button>
          <el-button type="primary" class="theme-primary-btn" :loading="starting" @click="onStartInterview">开始面试</el-button>
        </div>
      </template>

      <el-empty v-else-if="!loading" description="岗位不存在或已下线" :image-size="80" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue';
import type { FormInstance, FormRules, UploadFile, UploadFiles } from 'element-plus';
import { ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { useRoute, useRouter } from 'vue-router';
import mammoth from 'mammoth/mammoth.browser';
import * as pdfjsLib from 'pdfjs-dist';
import { getJobDetailApi, type HotJobItem } from '@/api/jobs';
import { useUserStore } from '@/store/user';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const loading = ref(true);
const starting = ref(false);
const job = ref<HotJobItem | null>(null);
const resumeInputMode = ref<'text' | 'file'>('text');
const fileList = ref<UploadFiles>([]);
const interviewMode = ref<'text' | 'avatar'>('text');
const avatarId = ref<'110592024' | '110117005' | '110017006'>('110592024');
const hasJobId = computed(() => {
  const id = Number(route.params.id);
  return Number.isFinite(id) && id > 0;
});

const formRef = ref<FormInstance>();
const form = reactive({
  positionName: '',
  resumeText: '',
});

const formRules: FormRules = {
  positionName: [{ required: true, message: '请填写面试岗位', trigger: 'blur' }],
  resumeText: [
    {
      validator: (_rule, value, cb) => {
        if (resumeInputMode.value === 'text' && !String(value || '').trim()) {
          cb(new Error('请填写简历内容'));
          return;
        }
        cb();
      },
      trigger: 'blur',
    },
  ],
};

function backToJobDetail() {
  const id = route.params.id;
  if (id) router.push({ name: 'JobDetail', params: { id: String(id) } });
  else router.push({ name: 'Home' });
}

function handleFileChange(_file: UploadFile, fileListInner: UploadFiles) {
  fileList.value = fileListInner.slice(-1);
}

function handleFileRemove(_file: UploadFile, fileListInner: UploadFiles) {
  fileList.value = fileListInner;
}

function inferCollectionNameByPosition(positionName: string) {
  const text = (positionName || '').toLowerCase();
  if (text.includes('android')) return 'android_engineer';
  if (text.includes('后端') || text.includes('backend')) return 'backend_engineer';
  return 'general_engineer';
}

async function extractPdfText(file: File) {
  const ab = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(ab) });
  const pdf = await loadingTask.promise;
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    const page = await pdf.getPage(i);
    // eslint-disable-next-line no-await-in-loop
    const content = await page.getTextContent();
    const txt = content.items
      .map((it) => ('str' in it ? String(it.str) : ''))
      .join(' ')
      .trim();
    if (txt) pages.push(txt);
  }
  return pages.join('\n');
}

async function extractWordText(file: File) {
  const ab = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer: ab });
  return String(result.value || '').trim();
}

async function getResumeTextFromInput() {
  if (resumeInputMode.value === 'text') {
    const txt = form.resumeText.trim();
    if (!txt) throw new Error('请填写简历内容');
    return txt;
  }

  const raw = fileList.value[0]?.raw as File | undefined;
  if (!raw) throw new Error('请先上传简历文件');
  const name = raw.name.toLowerCase();
  if (name.endsWith('.pdf')) {
    return extractPdfText(raw);
  }
  if (name.endsWith('.docx') || name.endsWith('.doc')) {
    return extractWordText(raw);
  }
  throw new Error('仅支持 PDF/Word 文件');
}

/** 拉取岗位后填充表单默认值 */
function fillFormFromJob(j: HotJobItem) {
  form.positionName = j.name || '';
  form.resumeText =
    `候选人，具有相关项目经验。目标岗位：${j.name || ''}。` +
    `${j.jobContent ? `过往经验摘要：${j.jobContent.slice(0, 140)}` : ''}`;
}

async function onStartInterview() {
  if (!job.value) return;
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  const idParam = String(route.params.id || 'new');

  starting.value = true;
  try {
    const resumeText = (await getResumeTextFromInput()).trim();
    if (!resumeText) {
      ElMessage.error('简历内容解析为空，请更换文件或改为手动输入');
      return;
    }
    const position = form.positionName.trim();
    const collection_name = inferCollectionNameByPosition(position);
    const pendingStartPayload = JSON.stringify({
      resume: resumeText,
      position,
      collection_name,
      user_id: userStore.userInfo?.id,
      interview_mode: interviewMode.value,
      avatar_id: avatarId.value,
    });
    sessionStorage.setItem('pendingInterviewStart', pendingStartPayload);

    router.push({
      name: 'InterviewSession',
      params: { id: idParam },
      query: {
        jobName: position,
        interviewMode: interviewMode.value,
        avatarId: avatarId.value,
      },
    });
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '创建面试会话失败');
  } finally {
    starting.value = false;
  }
}

watch(
  () => [String(route.name || ''), form.positionName.trim()] as const,
  ([n, pos]) => {
    if (n !== 'InterviewSettings') return;
    document.title = pos || '面试设置';
  },
  { immediate: true }
);

onMounted(async () => {
  const id = Number(route.params.id);
  if (!id) {
    form.positionName = form.positionName || '通用岗位';
    loading.value = false;
    return;
  }
  try {
    const res = await getJobDetailApi(id);
    job.value = res;
    fillFormFromJob(res);
  } catch {
    job.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.interview-settings-page { max-width: 1000px; margin: 0 auto; }
.settings-card { width: 100%; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.intro { font-size: 13px; color: #606266; margin: 0 0 16px; line-height: 1.5; }
.settings-form { max-width: 100%; }
.upload-block { width: 100%; max-width: 520px; }
.upload-icon { font-size: 32px; color: #409eff; margin-bottom: 8px; }
.actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
.mode-tip { margin-top: 6px; color: #909399; font-size: 12px; line-height: 1.4; }
.avatar-select { width: 320px; }
</style>
