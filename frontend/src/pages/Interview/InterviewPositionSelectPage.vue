<template>
  <div class="setup-page">
    <InterviewSetupProgress :active="1" />
    <div class="layout">
      <el-card class="theme-card left-card" shadow="hover">
        <el-form label-width="120px">
          <el-form-item label="是否使用简历">
            <el-switch v-model="useResume" />
          </el-form-item>

          <el-form-item v-if="useResume" label="个人简历：">
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
                placeholder="搜索工作岗位"
                clearable
                @keyup.enter="onSearch"
              />
              <el-button type="primary" :loading="jobLoading" @click="onSearch">搜索</el-button>
            </div>
          </el-form-item>

          <div class="job-result-wrap">
            <div class="job-cards">
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
            <el-empty
              v-if="filteredJobs.length === 0"
              description="暂无匹配工作"
              :image-size="54"
            />
          </div>
        </el-form>
      </el-card>

      <el-card class="theme-card right-card" shadow="hover">
        <h3 class="detail-title">岗位详情</h3>
        <el-empty
          v-if="!selectedJob"
          description="请先在左侧选择工作岗位"
          :image-size="72"
        />
        <div v-else-if="detailLoading" class="selected-job-card detail-loading">岗位详情加载中...</div>
        <div v-else-if="detailError" class="selected-job-card detail-error">{{ detailError }}</div>
        <div v-else class="selected-job-card">
          <div class="header-row">
            <h4>{{ selectedJobDetail?.name || selectedJob.name }}</h4>
            <el-tag size="small" type="info">{{
              selectedJobDetail?.companyName || selectedJob.companyName
            }}</el-tag>
          </div>
          <p class="job-time" v-if="selectedJobDetail?.updateTime">更新时间：{{ selectedJobDetail?.updateTime }}</p>

          <div class="salary-block" v-if="hasSalary(selectedJobDetail)">
            <h5>薪资范围</h5>
            <ul>
              <li v-if="selectedJobDetail?.salaryJunior"><span>初级</span><b>{{ selectedJobDetail?.salaryJunior }}</b></li>
              <li v-if="selectedJobDetail?.salaryMid"><span>中级</span><b>{{ selectedJobDetail?.salaryMid }}</b></li>
              <li v-if="selectedJobDetail?.salarySenior"><span>高级</span><b>{{ selectedJobDetail?.salarySenior }}</b></li>
              <li v-if="selectedJobDetail?.salaryExpert"><span>专家</span><b>{{ selectedJobDetail?.salaryExpert }}</b></li>
            </ul>
          </div>

          <div class="text-block">
            <h5>技能要求</h5>
            <p class="job-content">{{ selectedJobDetail?.skillRequirements || selectedJobDetail?.jobContent || '暂无技能要求' }}</p>
          </div>
        </div>
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

const router = useRouter();
const userStore = useUserStore();
const draft = loadInterviewSetupDraft();

const useResume = ref(Boolean(draft.useResume));
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

function onSearch() {
  void fetchSimplePositions();
}

async function fetchSimplePositions() {
  const keyword = String(jobKeyword.value || '').trim();
  jobLoading.value = true;
  try {
    const res = await getSimplePositionPageApi({
      page: 1,
      pageSize: 10,
      name: keyword || undefined,
    });
    const list = Array.isArray(res?.list) ? res.list : [];
    allJobs.value = list.map((it) => ({
      id: Number(it.id),
      name: String(it.name || '未命名岗位'),
      companyName: '岗位库',
      companyLogo: '',
      salaryMin: '--',
      salaryMax: '--',
      jobContent: '',
      type: '岗位',
    }));
    if (!allJobs.value.some((j) => j.id === selectedJobId.value)) {
      selectedJobId.value = undefined;
      positionName.value = '';
      positionDetail.value = '';
      selectedJobDetail.value = null;
      detailError.value = '';
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '岗位搜索失败');
  } finally {
    jobLoading.value = false;
  }
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

function hasSalary(detail: (typeof selectedJobDetail.value) | null) {
  if (!detail) return false;
  return Boolean(detail.salaryJunior || detail.salaryMid || detail.salarySenior || detail.salaryExpert);
}

function shorten(text: string) {
  const t = String(text || '');
  return t.length > 60 ? `${t.slice(0, 60)}...` : t;
}

onMounted(async () => {
  try {
    await fetchResumeOptions(true);
  } catch {
    ElMessage.warning('获取简历列表失败，请稍后重试');
  }
  try {
    await fetchSimplePositions();
  } catch {
    // ignore
  }
});

onBeforeUnmount(() => {
  detachResumeScrollListener();
});

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
.job-result-wrap {
  margin-top: 6px;
  flex: 0 0 auto;
  min-height: 0;
  overflow: hidden;
  max-height: 210px;
}
.search-row {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}
.job-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 210px;
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
.detail-title { margin: 0 0 8px; }
.selected-job-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  background: #fff;
  max-height: 340px;
  overflow-y: auto;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.header-row h4 {
  margin: 0;
  font-size: 16px;
}
.job-time {
  margin: 0 0 10px;
  color: #9ca3af;
  font-size: 12px;
}
.salary-block {
  margin-bottom: 12px;
  border: 1px solid #ede9fe;
  background: #faf5ff;
  border-radius: 10px;
  padding: 10px 12px;
}
.salary-block h5,
.text-block h5 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #374151;
}
.salary-block ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}
.salary-block li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #4b5563;
}
.salary-block li b {
  color: #111827;
  font-weight: 700;
}
.text-block {
  margin-bottom: 12px;
}
.job-content {
  margin: 0;
  color: #374151;
  line-height: 1.7;
  white-space: pre-wrap;
}
.detail-loading,
.detail-error {
  color: #6b7280;
  line-height: 1.7;
}
.detail-error {
  color: #b91c1c;
}
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 12px; }
@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .left-card,
  .right-card {
    max-height: none;
  }
}
</style>
