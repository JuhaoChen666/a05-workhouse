<template>
  <div class="question-bank-page theme-page-shell">
    <el-card class="theme-card fade-in-up delay-1" shadow="hover">
      <el-steps :active="activeStep" finish-status="success" align-center class="flow-steps">
        <el-step title="选择岗位" />
        <el-step title="选择简历" />
      </el-steps>
    </el-card>

    <div v-if="currentStep === 0" class="step-layout fade-in-up delay-1">
      <el-card class="theme-card step-left-card" shadow="hover">
        <el-form label-width="88px" class="qb-form">
          <el-form-item label="岗位">
            <div class="job-search-row">
              <el-input
                v-model.trim="jobKeyword"
                clearable
                placeholder="输入岗位关键字，如：后端、Java、产品经理"
                class="job-search-input"
                @keyup.enter="onSearchJobs"
              />
              <el-button type="primary" :loading="jobLoading" @click="onSearchJobs">搜索</el-button>
            </div>
            <div v-if="hasSearched" class="job-meta">
              共 <strong>{{ jobTotal }}</strong> 条
            </div>
          </el-form-item>
        </el-form>

        <div v-loading="jobLoading" class="job-card-wrap">
          <el-empty
            v-if="hasSearched && allJobs.length === 0"
            description="未找到匹配岗位，请更换关键字"
            :image-size="72"
          />
          <div v-else class="job-card-grid">
            <article
              v-for="job in allJobs"
              :key="job.id"
              class="job-card"
              :class="{ active: selectedJobId === job.id }"
              role="button"
              tabindex="0"
              @click="onPickJob(job)"
              @keydown.enter.prevent="onPickJob(job)"
            >
              <div class="job-card-name">{{ job.name }}</div>
              <div class="job-card-meta">ID: {{ job.id }}</div>
            </article>
          </div>
        </div>

        <div v-if="hasSearched && jobTotal > 0" class="pager-wrap">
          <el-pagination
            v-model:current-page="jobPage"
            v-model:page-size="jobPageSize"
            :total="jobTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @current-change="fetchJobPositions"
            @size-change="onJobPageSizeChange"
          />
        </div>
      </el-card>

      <el-card class="theme-card step-right-card" shadow="hover">
        <InterviewPositionJobDetailBlock
          :job="selectedJob"
          :loading="detailLoading"
          :error="detailError"
          :detail="selectedJobDetail"
        />
      </el-card>
    </div>

    <el-card v-else class="theme-card fade-in-up delay-1" shadow="hover">
      <div class="dialog-job">
        <span class="label">已选岗位</span>
        <span class="value">{{ selectedJobLabel || '请先在上方选择岗位' }}</span>
      </div>
      <el-form label-width="88px" class="dialog-form">
        <el-form-item label="简历" required>
          <el-select
            v-model="dialogResumeId"
            :disabled="!selectedJobId"
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
      <div class="confirm-row">
        <el-button type="primary" class="theme-primary-btn" :disabled="!canConfirmPredict" @click="confirmPredict">
          开始生成押题
        </el-button>
      </div>
    </el-card>

    <div class="actions">
      <el-button v-if="currentStep === 1" @click="goPrevStep">上一步</el-button>
      <el-button
        v-if="currentStep === 0"
        type="primary"
        class="theme-primary-btn"
        :disabled="!selectedJobId"
        @click="goNextStep"
      >
        下一步
      </el-button>
    </div>
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
import InterviewPositionJobDetailBlock from '@/pages/Interview/InterviewPositionJobDetailBlock.vue';

const router = useRouter();
const userStore = useUserStore();

const selectedJobId = ref<number | undefined>(undefined);
const selectedJobLabel = ref('');
const positionSlug = ref('backend_engineer');
const currentStep = ref<0 | 1>(0);
const allJobs = ref<HotJobItem[]>([]);
const jobLoading = ref(false);
const hasSearched = ref(false);
const jobKeyword = ref('');
const jobPage = ref(1);
const jobPageSize = ref(10);
const jobTotal = ref(0);
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

const dialogResumeId = ref<number | undefined>(undefined);

const resumeOptions = ref<Array<{ id: number; name: string }>>([]);
const resumePage = ref(1);
const resumePageSize = 8;
const resumeTotal = ref(0);
const resumeLoading = ref(false);
let resumeScrollWrap: HTMLElement | null = null;

const canConfirmPredict = computed(
  () => Boolean(dialogResumeId.value && positionSlug.value && selectedJobId.value)
);
const activeStep = computed(() => currentStep.value);

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

async function fetchJobPositions() {
  const keyword = String(jobKeyword.value || '').trim();
  jobLoading.value = true;
  hasSearched.value = true;

  try {
    const res = await getSimplePositionPageApi({
      page: jobPage.value,
      pageSize: jobPageSize.value,
    });
    const list = Array.isArray(res?.list) ? res.list : [];
    const mapped = mapSimplePositionList(list).filter((it) =>
      keyword ? it.name.toLowerCase().includes(keyword.toLowerCase()) : true
    );
    const totalNum = Number(res?.total);
    if (res?.total != null && res?.total !== '' && Number.isFinite(totalNum)) {
      jobTotal.value = Math.max(0, totalNum);
    } else {
      jobTotal.value = mapped.length;
    }
    allJobs.value = mapped;
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '岗位搜索失败');
  } finally {
    jobLoading.value = false;
  }
}

function onSearchJobs() {
  jobPage.value = 1;
  void fetchJobPositions();
}

function onJobPageSizeChange(size: number) {
  jobPageSize.value = size;
  jobPage.value = 1;
  void fetchJobPositions();
}

function goNextStep() {
  if (!selectedJobId.value) {
    ElMessage.warning('请先选择岗位');
    return;
  }
  currentStep.value = 1;
}

function goPrevStep() {
  currentStep.value = 0;
}

async function fetchPositionMeta(job: HotJobItem) {
  detailLoading.value = true;
  detailError.value = '';
  selectedJobDetail.value = null;
  try {
    const raw = await getPositionDetailApi(job.id);
    const detail = raw as Record<string, unknown>;
    const name = String(detail.name ?? job.name ?? '');
    const type = String(detail.type ?? '');
    selectedJobLabel.value = name;
    positionSlug.value = resolvePositionSlug({ type, name: job.name, jobId: job.id });
    selectedJobDetail.value = {
      name,
      type,
      jobContent: String(detail.jobContent ?? detail.content ?? detail.description ?? '').trim(),
      companyName: String(detail.companyName ?? '').trim(),
      responsibility: String(detail.responsibility ?? '').trim(),
      skillRequirements: String(detail.skill_requirements ?? detail.skillRequirements ?? '').trim(),
      salaryJunior: String(detail.salary_junior ?? '').trim(),
      salaryMid: String(detail.salary_mid ?? '').trim(),
      salarySenior: String(detail.salary_senior ?? '').trim(),
      salaryExpert: String(detail.salary_expert ?? '').trim(),
      updateTime: String(detail.updated_at ?? detail.updatedAt ?? '').trim(),
    };
  } catch {
    selectedJobLabel.value = job.name || '';
    positionSlug.value = resolvePositionSlug({ type: '', name: job.name, jobId: job.id });
    detailError.value = '获取岗位详情失败';
  } finally {
    detailLoading.value = false;
  }
}

async function onPickJob(job: HotJobItem) {
  selectedJobId.value = job.id;
  await fetchPositionMeta(job);
  if (!dialogResumeId.value) {
    dialogResumeId.value = resumeOptions.value[0]?.id;
  }
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
  void fetchJobPositions();
});

onBeforeUnmount(() => {
  detachResumeScrollListener();
});
</script>

<style scoped>
.question-bank-page {
  max-width: 1000px;
  display: grid;
  gap: 14px;
}

.step-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
  gap: 14px;
}

.flow-steps {
  margin-top: 4px;
}

.intro {
  margin-top: 0;
  color: #4b5563;
  line-height: 1.65;
  margin-bottom: 20px;
}

.qb-form {
  max-width: 760px;
}

.job-search-row {
  width: 100%;
  display: flex;
  gap: 10px;
}

.job-search-input {
  width: min(100%, 560px);
}

.job-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
}

.job-card-wrap {
  margin-top: 8px;
}

.job-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.job-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.job-card:hover {
  border-color: #c4b5fd;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.1);
  transform: translateY(-1px);
}

.job-card.active {
  border-color: #8b5cf6;
  background: linear-gradient(145deg, #faf5ff 0%, #ffffff 100%);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.15);
}

.job-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  line-height: 1.45;
  word-break: break-word;
}

.job-card-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #9ca3af;
}

.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
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

.confirm-row {
  display: flex;
  justify-content: flex-end;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1024px) {
  .job-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .step-layout {
    grid-template-columns: 1fr;
  }
  .job-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
