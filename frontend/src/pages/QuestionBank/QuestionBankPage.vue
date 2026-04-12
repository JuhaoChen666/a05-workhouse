<template>
  <div class="question-bank-page theme-page-shell">
    <el-card class="theme-card fade-in-up delay-1" shadow="hover">
      <p class="intro">
        选择目标岗位后，将弹出表单选择一份简历；确认后由 AI
        结合简历与岗位方向流式生成面试题，参考答案默认隐藏，可按需展开。
      </p>

      <el-form label-width="88px" class="qb-form">
        <el-form-item label="岗位">
          <el-select
            v-model="selectedJobId"
            filterable
            remote
            reserve-keyword
            clearable
            :remote-method="remoteJobSearch"
            :loading="jobLoading || jobLoadingMore"
            placeholder="输入关键字搜索并选择岗位"
            class="job-select"
            popper-class="job-select-popper-qb"
            @visible-change="onJobSelectVisibleChange"
            @change="onJobChange"
          >
            <el-option v-for="job in allJobs" :key="job.id" :label="job.name" :value="job.id" />
          </el-select>
          <div v-if="hasSearched" class="job-meta">
            <template v-if="jobLoading">正在搜索…</template>
            <template v-else>
              共 <strong>{{ jobTotal }}</strong> 条
              <span v-if="jobTotal > 0"> · 已加载 {{ allJobs.length }} 条</span>
              <span v-if="jobLoadingMore"> · 加载中…</span>
            </template>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog
      v-model="predictDialogVisible"
      title="生成押题"
      width="min(92vw, 440px)"
      destroy-on-close
      class="predict-dialog"
      @closed="onPredictDialogClosed"
    >
      <div v-if="selectedJobLabel" class="dialog-job">
        <span class="label">已选岗位</span>
        <span class="value">{{ selectedJobLabel }}</span>
      </div>
      <el-form label-width="88px" class="dialog-form">
        <el-form-item label="简历" required>
          <el-select
            v-model="dialogResumeId"
            placeholder="选择用于生题的简历"
            style="width: 100%"
            :loading="resumeLoading"
            popper-class="resume-select-popper-qb"
            @visible-change="onResumeSelectVisibleChange"
          >
            <el-option
              v-for="item in resumeOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="predictDialogVisible = false">取消</el-button>
        <el-button type="primary" class="theme-primary-btn" :disabled="!canConfirmPredict" @click="confirmPredict">
          确认生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getPositionDetailApi, getSimplePositionPageApi, type HotJobItem } from '@/api/jobs';
import { getResumeListApi } from '@/api/resume';
import { useUserStore } from '@/store/user';
import { resolvePositionSlug } from '@/utils/positionSlug';

const router = useRouter();
const userStore = useUserStore();

const selectedJobId = ref<number | undefined>(undefined);
const selectedJobLabel = ref('');
const positionSlug = ref('backend_engineer');
const allJobs = ref<HotJobItem[]>([]);
const jobLoading = ref(false);
const jobLoadingMore = ref(false);
const hasSearched = ref(false);
const jobKeyword = ref('');
const jobNextPage = ref(2);
const jobPageSize = 10;
const jobTotal = ref(0);
let jobSearchTimer: number | null = null;
let jobSelectScrollWrap: HTMLElement | null = null;

const predictDialogVisible = ref(false);
const dialogResumeId = ref<number | undefined>(undefined);

const resumeOptions = ref<Array<{ id: number; name: string }>>([]);
const resumePage = ref(1);
const resumePageSize = 8;
const resumeTotal = ref(0);
const resumeLoading = ref(false);
let resumeScrollWrap: HTMLElement | null = null;

const jobHasMore = computed(
  () => hasSearched.value && jobTotal.value > 0 && allJobs.value.length < jobTotal.value
);

const canConfirmPredict = computed(
  () => Boolean(dialogResumeId.value && positionSlug.value && selectedJobId.value)
);

function mapSimplePositionList(list: { id: unknown; name?: unknown }[]): HotJobItem[] {
  return list.map((it) => ({
    id: Number(it.id),
    name: String(it.name || '未命名岗位'),
    companyName: '岗位库',
    companyLogo: '',
    salaryMin: '--',
    salaryMax: '--',
    jobContent: '',
    type: '岗位',
  }));
}

async function loadJobPositionsPage(mode: 'replace' | 'append') {
  const keyword = String(jobKeyword.value || '').trim();
  if (mode === 'append') {
    if (!jobHasMore.value || jobLoadingMore.value || jobLoading.value) return;
    jobLoadingMore.value = true;
  } else {
    jobLoading.value = true;
  }

  const page = mode === 'replace' ? 1 : jobNextPage.value;
  hasSearched.value = true;

  try {
    const res = await getSimplePositionPageApi({
      page,
      pageSize: jobPageSize,
      name: keyword || undefined,
    });
    const list = Array.isArray(res?.list) ? res.list : [];
    const mapped = mapSimplePositionList(list);
    const totalNum = Number(res?.total);
    if (res?.total != null && res?.total !== '' && Number.isFinite(totalNum)) {
      jobTotal.value = Math.max(0, totalNum);
    } else if (mode === 'replace') {
      jobTotal.value = mapped.length;
    }

    if (mode === 'replace') {
      allJobs.value = mapped;
      jobNextPage.value = 2;
    } else {
      if (mapped.length === 0) {
        jobTotal.value = allJobs.value.length;
        return;
      }
      const seen = new Set(allJobs.value.map((j) => j.id));
      for (const j of mapped) {
        if (!seen.has(j.id)) {
          seen.add(j.id);
          allJobs.value.push(j);
        }
      }
      jobNextPage.value = page + 1;
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '岗位搜索失败');
  } finally {
    jobLoading.value = false;
    jobLoadingMore.value = false;
  }
}

function remoteJobSearch(query: string) {
  jobKeyword.value = query;
  if (jobSearchTimer != null) window.clearTimeout(jobSearchTimer);
  jobSearchTimer = window.setTimeout(() => {
    void loadJobPositionsPage('replace');
  }, 320);
}

function detachJobSelectScrollListener() {
  if (!jobSelectScrollWrap) return;
  jobSelectScrollWrap.removeEventListener('scroll', onJobDropdownScroll);
  jobSelectScrollWrap = null;
}

function onJobDropdownScroll(e: Event) {
  const target = e.target as HTMLElement;
  const reachBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 24;
  if (!reachBottom) return;
  void loadJobPositionsPage('append');
}

function onJobSelectVisibleChange(visible: boolean) {
  if (!visible) {
    detachJobSelectScrollListener();
    return;
  }
  void loadJobPositionsPage('replace');
  nextTick(() => {
    detachJobSelectScrollListener();
    const wrap = document.querySelector('.job-select-popper-qb .el-select-dropdown__wrap') as
      | HTMLElement
      | null;
    if (!wrap) return;
    jobSelectScrollWrap = wrap;
    jobSelectScrollWrap.addEventListener('scroll', onJobDropdownScroll, { passive: true });
  });
}

async function fetchPositionMeta(job: HotJobItem) {
  try {
    const raw = await getPositionDetailApi(job.id);
    const detail = raw as Record<string, unknown>;
    const name = String(detail.name ?? job.name ?? '');
    const type = String(detail.type ?? '');
    selectedJobLabel.value = name;
    positionSlug.value = resolvePositionSlug({ type, name: job.name, jobId: job.id });
  } catch {
    selectedJobLabel.value = job.name || '';
    positionSlug.value = resolvePositionSlug({ type: '', name: job.name, jobId: job.id });
  }
}

async function onJobChange(val: string | number | null | undefined) {
  const id = val === '' || val == null ? undefined : typeof val === 'number' ? val : Number(val);
  if (id == null || Number.isNaN(id)) {
    selectedJobLabel.value = '';
    return;
  }
  const job = allJobs.value.find((j) => j.id === id);
  if (!job) return;
  await fetchPositionMeta(job);
  predictDialogVisible.value = true;
  dialogResumeId.value = resumeOptions.value[0]?.id;
}

function onPredictDialogClosed() {
  dialogResumeId.value = undefined;
}

async function fetchResumeOptions(reset = false) {
  const userId = userStore.userInfo?.id;
  if (!userId || resumeLoading.value) return;
  if (reset) {
    resumePage.value = 1;
    resumeOptions.value = [];
    resumeTotal.value = 0;
  }
  if (!reset && resumeOptions.value.length >= resumeTotal.value && resumeTotal.value > 0) return;
  resumeLoading.value = true;
  try {
    const res = await getResumeListApi(userId, resumePage.value, resumePageSize);
    const list = Array.isArray(res?.items) ? res.items : [];
    resumeTotal.value = Number(res?.total || 0);
    const mapped = list.map((it) => ({
      id: Number(it.id),
      name: String(it.filename || '未命名简历'),
    }));
    resumeOptions.value = reset ? mapped : [...resumeOptions.value, ...mapped];
    if (list.length > 0) resumePage.value += 1;
  } finally {
    resumeLoading.value = false;
  }
}

function detachResumeScrollListener() {
  if (!resumeScrollWrap) return;
  resumeScrollWrap.removeEventListener('scroll', onResumeDropdownScroll);
  resumeScrollWrap = null;
}

function onResumeDropdownScroll(e: Event) {
  const target = e.target as HTMLElement;
  const reachBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 20;
  if (!reachBottom) return;
  void fetchResumeOptions(false);
}

function onResumeSelectVisibleChange(visible: boolean) {
  if (!visible) {
    detachResumeScrollListener();
    return;
  }
  nextTick(() => {
    detachResumeScrollListener();
    const wrap = document.querySelector('.resume-select-popper-qb .el-select-dropdown__wrap') as
      | HTMLElement
      | null;
    if (!wrap) return;
    resumeScrollWrap = wrap;
    resumeScrollWrap.addEventListener('scroll', onResumeDropdownScroll, { passive: true });
    if (resumeOptions.value.length === 0) void fetchResumeOptions(true);
  });
}

function confirmPredict() {
  const rid = dialogResumeId.value;
  if (!rid || !selectedJobId.value) {
    ElMessage.warning('请选择简历');
    return;
  }
  predictDialogVisible.value = false;
  router.push({
    name: 'HomePredictQuestions',
    query: {
      resumeId: String(rid),
      position: positionSlug.value,
      jobName: selectedJobLabel.value || '岗位',
    },
  });
}

onMounted(async () => {
  try {
    await fetchResumeOptions(true);
  } catch {
    ElMessage.warning('获取简历列表失败，弹窗内仍可下拉加载');
  }
});

onBeforeUnmount(() => {
  detachJobSelectScrollListener();
  detachResumeScrollListener();
  if (jobSearchTimer != null) {
    window.clearTimeout(jobSearchTimer);
    jobSearchTimer = null;
  }
});
</script>

<style scoped>
.question-bank-page {
  max-width: 1000px;
}

.intro {
  margin-top: 0;
  color: #4b5563;
  line-height: 1.65;
  margin-bottom: 20px;
}

.qb-form {
  max-width: 560px;
}

.job-select {
  width: 100%;
}

.job-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
}

.dialog-job {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
}

.dialog-job .label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.dialog-job .value {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.dialog-form {
  margin-top: 4px;
}
</style>
