<template>
  <div class="setup-page">
    <InterviewSetupProgress :active="1" />

    <!-- 移动端：单列，岗位为远程下拉搜索，详情紧挨搜索区下方 -->
    <template v-if="isMobile">
      <el-card class="theme-card mobile-setup-card" shadow="hover">
        <el-form label-width="96px" class="mobile-setup-form">
          <el-form-item label="个人简历">
            <el-select
              v-model="selectedResumeId"
              placeholder="请选择个人简历"
              clearable
              style="width: 100%"
              :loading="resumeLoading"
              popper-class="resume-select-popper"
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

          <el-form-item label="岗位">
            <el-select
              v-model="selectedJobId"
              filterable
              remote
              reserve-keyword
              :remote-method="remoteJobSearch"
              :loading="jobLoading || jobLoadingMore"
              placeholder="输入关键字，在下拉列表中选择岗位"
              clearable
              class="mobile-job-select"
              popper-class="job-select-popper"
              @visible-change="onJobSelectVisibleChange"
              @change="onMobileJobSelectChange"
            >
              <el-option v-for="job in allJobs" :key="job.id" :label="job.name" :value="job.id" />
            </el-select>
            <div v-if="hasSearched" class="mobile-job-meta">
              <template v-if="jobLoading">正在搜索…</template>
              <template v-else>
                共 <strong>{{ jobTotal }}</strong> 条
                <span v-if="jobTotal > 0" class="meta-sub"> · 已加载 {{ allJobs.length }} 条</span>
                <span v-if="jobLoadingMore" class="meta-loading-inline"> · 加载中…</span>
              </template>
            </div>
          </el-form-item>
        </el-form>

        <div class="mobile-detail-wrap">
          <InterviewPositionJobDetailBlock
            :job="selectedJob"
            :loading="detailLoading"
            :error="detailError"
            :detail="selectedJobDetail"
          />
        </div>
      </el-card>
    </template>

    <!-- 桌面端：双栏 -->
    <div v-else class="layout">
      <el-card class="theme-card left-card" shadow="hover">
        <el-form label-width="120px">
          <el-form-item label="个人简历：">
            <el-select
              v-model="selectedResumeId"
              placeholder="请选择个人简历"
              clearable
              style="width: 100%"
              :loading="resumeLoading"
              popper-class="resume-select-popper"
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

          <el-form-item label="岗位：">
            <div class="search-row">
              <el-input
                v-model="jobKeyword"
                placeholder="请输入关键词"
                clearable
                @keyup.enter.prevent
              />
            </div>
          </el-form-item>

          <div v-if="hasSearched" class="job-search-meta">
            <template v-if="jobLoading">
              <span class="meta-loading">正在搜索…</span>
            </template>
            <template v-else>
              <span class="meta-count">共 <strong>{{ jobTotal }}</strong> 条岗位</span>
              <span v-if="jobTotal > 0" class="meta-sub"> · 已加载 {{ allJobs.length }} 条</span>
              <span v-if="jobLoadingMore" class="meta-loading-inline"> · 加载更多中…</span>
            </template>
          </div>

          <div class="job-result-wrap" v-loading="jobLoading" element-loading-text="岗位搜索中...">
            <div
              v-if="filteredJobs.length > 0"
              class="job-cards"
              @scroll.passive="onJobListScroll"
            >
              <article
                v-for="job in filteredJobs"
                :key="job.id"
                class="job-card"
                :class="{ active: selectedJobId === job.id }"
                @click="selectJob(job)"
              >
                <div class="job-card-header">
                  <h4>{{ job.name }}</h4>
                  <el-icon v-if="selectedJobId === job.id" class="selected-icon"><Select /></el-icon>
                </div>
                <p class="desc">{{ shorten(job.jobContent) }}</p>
              </article>
            </div>
            <div v-else-if="showNoJobResult" class="job-empty-wrap">
              <el-empty description="未搜索到匹配岗位" :image-size="54" />
            </div>
            <div v-else-if="showSearchHint" class="job-search-hint">请输入关键词</div>
          </div>
        </el-form>
      </el-card>

      <el-card class="theme-card right-card" shadow="hover">
        <InterviewPositionJobDetailBlock
          :job="selectedJob"
          :loading="detailLoading"
          :error="detailError"
          :detail="selectedJobDetail"
        />
      </el-card>
    </div>

    <div class="actions">
      <el-button @click="goPrev">上一步</el-button>
      <el-button type="primary" class="theme-primary-btn" @click="goNext">下一步</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { Select } from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';
import { getPositionDetailApi, getSimplePositionPageApi, type HotJobItem } from '@/api/jobs';
import { getResumeListApi } from '@/api/resume';
import { useUserStore } from '@/store/user';
import { loadInterviewSetupDraft, saveInterviewSetupDraft } from './setupState';
import InterviewSetupProgress from './InterviewSetupProgress.vue';
import InterviewPositionJobDetailBlock from './InterviewPositionJobDetailBlock.vue';
import { useViewport } from '@/composables/useViewport';
import { MOBILE_MAX_WIDTH_PX } from '@/constants/breakpoints';

const router = useRouter();
const userStore = useUserStore();
const { isMobile } = useViewport();
const draft = loadInterviewSetupDraft();

const useResume = ref(true);
const resumeName = ref(draft.resumeName || '');
const resumeType = ref(draft.resumeType || '');
const positionName = ref(draft.positionName || '');
const positionDetail = ref(draft.positionDetail || '');
const selectedResumeId = ref<number | undefined>(draft.resumeId);
const resumeOptions = ref<Array<{ id: number; name: string; content: string }>>([]);
const resumePage = ref(1);
const resumePageSize = 5;
const resumeTotal = ref(0);
const resumeLoading = ref(false);
const selectedJobId = ref<number | undefined>(undefined);
const jobKeyword = ref('');
const allJobs = ref<HotJobItem[]>([]);
const jobLoading = ref(false);
const jobLoadingMore = ref(false);
const hasSearched = ref(false);
const jobNextPage = ref(2);
const jobPageSize = 8;
const jobTotal = ref(0);
let jobSearchTimer: number | null = null;
let jobSelectScrollWrap: HTMLElement | null = null;
const selectedJob = computed(() => allJobs.value.find((j) => j.id === selectedJobId.value));
const selectedJobDetail = ref<{
  name: string;
  type: string;
  jobContent: string;
  companyName: string;
  responsibility: string;
  skillRequirements: string;
  salaryJunior: string;
  salaryMid: string;
  salarySenior: string;
  salaryExpert: string;
  updateTime: string;
} | null>(null);
const detailLoading = ref(false);
const detailError = ref('');
let resumeScrollWrap: HTMLElement | null = null;

watch(selectedResumeId, (id) => {
  const item = resumeOptions.value.find((r) => r.id === id);
  if (!item) return;
  resumeName.value = item.name;
  const text = `${String(item.content || '')} ${String(item.name || '')}`.toLowerCase();
  if (text.includes('android')) resumeType.value = 'Android';
  else if (text.includes('前端') || text.includes('frontend')) resumeType.value = '前端';
  else if (text.includes('后端') || text.includes('backend')) resumeType.value = '后端';
  else resumeType.value = '';
});

const filteredJobs = computed(() => allJobs.value);
const showNoJobResult = computed(() => hasSearched.value && !jobLoading.value && filteredJobs.value.length === 0);
const showSearchHint = computed(() => !hasSearched.value && !jobLoading.value);
const jobHasMore = computed(
  () => hasSearched.value && jobTotal.value > 0 && allJobs.value.length < jobTotal.value
);

function mapSimplePositionList(
  list: { id: unknown; name?: unknown; responsibility?: unknown; englishName?: unknown }[]
): HotJobItem[] {
  return list.map((it) => ({
    id: Number(it.id),
    name: String(it.name || '未命名岗位'),
    englishName: it.englishName == null ? null : String(it.englishName),
    companyName: '岗位库',
    companyLogo: '',
    salaryMin: '--',
    salaryMax: '--',
    // 搜索卡片展示：优先用 simple/page 返回的 responsibility
    jobContent: String(it.responsibility || '').trim(),
    type: String(it.englishName || '岗位'),
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
      if (!allJobs.value.some((j) => j.id === selectedJobId.value)) {
        selectedJobId.value = undefined;
        positionName.value = '';
        positionDetail.value = '';
        selectedJobDetail.value = null;
        detailError.value = '';
      }
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

function onJobListScroll(e: Event) {
  const el = e.target as HTMLElement;
  if (el.scrollTop + el.clientHeight < el.scrollHeight - 32) return;
  void loadJobPositionsPage('append');
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
  if (isMobile.value && !String(jobKeyword.value || '').trim()) {
    void loadJobPositionsPage('replace');
  }
  nextTick(() => {
    detachJobSelectScrollListener();
    const wrap = document.querySelector('.job-select-popper .el-select-dropdown__wrap') as
      | HTMLElement
      | null;
    if (!wrap) return;
    jobSelectScrollWrap = wrap;
    jobSelectScrollWrap.addEventListener('scroll', onJobDropdownScroll, { passive: true });
  });
}

function selectJob(job: HotJobItem) {
  selectedJobId.value = job.id;
  void fetchPositionDetail(job);
}

async function fetchPositionDetail(job: HotJobItem) {
  detailLoading.value = true;
  detailError.value = '';
  selectedJobDetail.value = null;
  try {
    const raw = await getPositionDetailApi(job.id);
    const detail = raw as Record<string, unknown>;
    const name = String(detail.name ?? job.name ?? '');
    const type = String(detail.type ?? '');
    const content = String(detail.jobContent ?? detail.content ?? detail.description ?? '');
    const companyName = String(detail.companyName ?? job.companyName ?? '岗位库');
    const responsibility = String(detail.responsibility ?? '');
    const skillRequirements = String(detail.skill_requirements ?? detail.skillRequirements ?? '');
    const salaryJunior = String(detail.salary_junior ?? detail.salaryJunior ?? '');
    const salaryMid = String(detail.salary_mid ?? detail.salaryMid ?? '');
    const salarySenior = String(detail.salary_senior ?? detail.salarySenior ?? '');
    const salaryExpert = String(detail.salary_expert ?? detail.salaryExpert ?? '');
    const updateTime = formatDateTime(String(detail.update_time ?? detail.updateTime ?? ''));
    selectedJobDetail.value = {
      name,
      type,
      jobContent: content,
      companyName,
      responsibility,
      skillRequirements,
      salaryJunior,
      salaryMid,
      salarySenior,
      salaryExpert,
      updateTime,
    };
    positionName.value = name;
    positionDetail.value = responsibility || skillRequirements || content;
  } catch (e: unknown) {
    detailError.value = (e as Error).message || '获取岗位详情失败';
    positionName.value = job.name || '';
    positionDetail.value = '';
  } finally {
    detailLoading.value = false;
  }
}

function formatDateTime(input: string) {
  if (!input) return '';
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return input;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function shorten(text: string) {
  const t = String(text || '');
  return t.length > 60 ? `${t.slice(0, 60)}...` : t;
}

function remoteJobSearch(query: string) {
  jobKeyword.value = query;
  if (jobSearchTimer != null) {
    window.clearTimeout(jobSearchTimer);
  }
  jobSearchTimer = window.setTimeout(() => {
    void loadJobPositionsPage('replace');
  }, 320);
}

function onMobileJobSelectChange(val: string | number | undefined | null) {
  const id =
    val === '' || val == null ? undefined : typeof val === 'number' ? val : Number(val);
  if (id == null || Number.isNaN(id)) {
    selectedJobDetail.value = null;
    detailError.value = '';
    positionName.value = '';
    positionDetail.value = '';
    return;
  }
  const job = allJobs.value.find((j) => j.id === id);
  if (job) void fetchPositionDetail(job);
}

onMounted(async () => {
  try {
    await fetchResumeOptions(true);
  } catch {
    ElMessage.warning('获取简历列表失败，请稍后重试');
  }
  const narrow =
    typeof window !== 'undefined' &&
    window.matchMedia(`(max-width: ${MOBILE_MAX_WIDTH_PX}px)`).matches;
  if (!narrow) {
    try {
      await loadJobPositionsPage('replace');
    } catch {
      // ignore
    }
  }
});

onBeforeUnmount(() => {
  detachResumeScrollListener();
  detachJobSelectScrollListener();
  if (jobSearchTimer != null) {
    window.clearTimeout(jobSearchTimer);
    jobSearchTimer = null;
  }
});

watch(
  () => jobKeyword.value,
  () => {
    if (isMobile.value) return;
    if (jobSearchTimer != null) {
      window.clearTimeout(jobSearchTimer);
    }
    jobSearchTimer = window.setTimeout(() => {
      void loadJobPositionsPage('replace');
    }, 350);
  }
);

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
      content: '',
    }));
    resumeOptions.value = reset ? mapped : [...resumeOptions.value, ...mapped];
    if (selectedResumeId.value && !resumeOptions.value.some((r) => r.id === selectedResumeId.value)) {
      selectedResumeId.value = undefined;
    }
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
    const wrap = document.querySelector('.resume-select-popper .el-select-dropdown__wrap') as
      | HTMLElement
      | null;
    if (!wrap) return;
    resumeScrollWrap = wrap;
    resumeScrollWrap.addEventListener('scroll', onResumeDropdownScroll, { passive: true });
    if (resumeOptions.value.length === 0) {
      void fetchResumeOptions(true);
    }
  });
}

function goPrev() {
  router.push({ name: 'HomeInterviewType' });
}

function goNext() {
  if (!selectedResumeId.value) {
    ElMessage.warning('请先选择个人简历');
    return;
  }
  if (!selectedJobId.value) {
    ElMessage.warning('请先选择工作岗位');
    return;
  }
  saveInterviewSetupDraft({
    useResume: useResume.value,
    resumeId: selectedResumeId.value,
    resumeName: resumeName.value,
    resumeType: resumeType.value,
    positionName: positionName.value.trim(),
    positionEnglishName: String(selectedJob.value?.englishName || '').trim(),
    positionDetail: positionDetail.value.trim(),
  });
  router.push({ name: 'HomeInterviewConfig' });
}
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.left-card,
.right-card {
  min-height: 420px;
  max-height: 460px;
}
.left-card :deep(.el-card__body) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.left-card :deep(.el-form) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.right-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.job-search-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
  margin: 4px 0 8px;
  font-size: 13px;
  color: #6b7280;
}
.job-search-meta strong {
  color: #111827;
  font-weight: 700;
}
.meta-sub {
  color: #9ca3af;
  font-size: 12px;
}
.meta-loading {
  color: #9ca3af;
}
.meta-loading-inline {
  color: #8b5cf6;
  font-size: 12px;
}
.mobile-job-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}
.mobile-job-meta strong {
  color: #111827;
  font-weight: 700;
}
.job-result-wrap {
  position: relative;
  margin-top: 6px;
  flex: 0 0 auto;
  min-height: 0;
  overflow: hidden;
  height: 75%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
  padding: 8px;
  display: flex;
  flex-direction: column;
}
.search-row {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}
.job-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
  align-items: stretch;
  justify-content: flex-start;
}
.job-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all .2s ease;
  background: #fff;
  flex: 0 0 auto;
}
.job-card:hover { border-color: #c4b5fd; background: #faf5ff; }
.job-card.active { border-color: #8b5cf6; background: #f5f3ff; }
.job-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.job-card h4 { margin: 0 0 4px; font-size: 14px; }
.selected-icon {
  color: #10b981;
  font-size: 16px;
  flex-shrink: 0;
}
.job-card .desc { margin: 0; color: #4b5563; font-size: 12px; line-height: 1.5; }
.job-empty-wrap,
.job-search-hint {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.job-search-hint {
  color: #9ca3af;
  font-size: 13px;
}
.mobile-setup-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mobile-setup-form {
  flex-shrink: 0;
}
.mobile-job-select {
  width: 100%;
}
.mobile-detail-wrap {
  margin-top: 8px;
  padding-top: 4px;
  border-top: 1px solid #f3f4f6;
}
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 12px; }
@media (max-width: 768px) {
  .actions {
    flex-wrap: wrap;
  }
}
</style>
