<template>
  <div class="question-bank-page theme-page-shell">
    <el-card class="theme-card flow-steps-card fade-in-up delay-1" shadow="hover">
      <el-steps :active="activeStep" finish-status="success" simple class="flow-steps">
        <el-step title="选择岗位" />
        <el-step title="选择简历" />
        <el-step title="生成题目" />
      </el-steps>
    </el-card>

    <div class="qb-main-body fade-in-up delay-1">
      <div v-if="currentStep === 0" class="step-layout">
        <el-card class="theme-card step-left-card" shadow="hover">
          <div class="step-left-stack">
            <el-form label-width="88px" class="qb-form">
              <el-form-item>
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
              </el-form-item>
            </el-form>

            <div class="job-card-wrap">
              <div class="job-card-body">
                <el-progress
                  v-if="jobLoading"
                  class="job-card-progress"
                  indeterminate
                  :show-text="false"
                  :stroke-width="2"
                />
                <div class="job-card-scroll">
                  <el-empty
                    v-if="hasSearched && allJobs.length === 0 && !jobLoading"
                    description="未找到匹配岗位，请更换关键字"
                    :image-size="72"
                  />
                  <div v-else class="job-card-list">
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
                      <div class="job-card-head">
                        <div class="job-card-name">{{ job.name }}</div>
                      </div>
                      <div class="job-card-responsibility">
                        {{ job.responsibility || '暂无' }}
                      </div>
                    </article>
                  </div>
                </div>
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
          </div>
        </el-card>

        <el-card class="theme-card step-right-card" shadow="hover">
          <div class="step-right-stack">
            <InterviewPositionJobDetailBlock
              :job="selectedJob"
              :loading="detailLoading"
              :error="detailError"
              :detail="selectedJobDetail"
            />
          </div>
        </el-card>
      </div>

      <el-card v-else-if="currentStep === 1" class="theme-card step-resume-card" shadow="hover">
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
      </el-card>

      <div v-else class="step-generate-layout">
        <el-card class="theme-card gen-left-card" shadow="hover">
          <div class="gen-left-stack">
            <div class="gen-left-head">
              <h3 class="gen-left-title">{{ selectedJobLabel || '岗位押题' }}</h3>
              <el-tag v-if="predictStreaming" size="small" type="warning" effect="plain" class="gen-status-tag">
                <el-icon class="is-loading gen-status-icon"><Loading /></el-icon>
                <span>生成中</span>
              </el-tag>
              <el-tag v-else-if="predictStreamDone && predictItems.length > 0" size="small" type="success" effect="plain">
                已生成 {{ predictItems.length }} 题
              </el-tag>
              <el-button
                v-if="predictStreamDone && predictItems.length > 0"
                size="small"
                class="gen-export-btn"
                :loading="exportingPdf"
                @click="exportPredictPdf"
              >
                导出 PDF
              </el-button>
            </div>

            <div v-if="predictStreamError" class="gen-banner gen-banner--error">
              {{ predictStreamError }}
            </div>

            <div
              v-if="predictStreaming && predictItems.length === 0"
              class="gen-streaming-hint"
              aria-live="polite"
            >
              <el-icon class="is-loading gen-spin"><Loading /></el-icon>
              <span>正在生成题目，请稍候…</span>
            </div>

            <div v-else-if="currentPredictItem" class="gen-question-scroll">
              <article class="pq-card">
                <div class="pq-card-head">
                  <span class="pq-index">第 {{ currentPredictItem.displayIndex }} 题</span>
                  <el-tag
                    v-if="currentPredictItem.difficulty && currentPredictItem.difficulty !== '—'"
                    size="small"
                    effect="plain"
                    class="pq-diff-tag"
                  >
                    {{ currentPredictItem.difficulty }}
                  </el-tag>
                </div>
                <div class="pq-question">{{ currentPredictItem.question }}</div>
                <div class="pq-answer-block">
                  <div v-if="!currentPredictItem.reveal" class="pq-answer-placeholder">
                    参考答案与要点已生成
                  </div>
                  <div v-else class="pq-reveal-body">
                    <div v-if="currentPredictItem.keyPoints" class="pq-key-points">
                      <span class="sub-label">关键要点</span>
                      <p class="pq-key-points-text">{{ currentPredictItem.keyPoints }}</p>
                    </div>
                    <div class="pq-answer-text">{{ currentPredictItem.answer }}</div>
                  </div>
                  <el-button
                    type="primary"
                    link
                    class="pq-reveal-btn"
                    @click="toggleCurrentReveal"
                  >
                    {{ currentPredictItem.reveal ? '隐藏答案' : '查看答案' }}
                  </el-button>
                </div>
              </article>
              <div v-if="predictStreaming && !predictStreamDone" class="gen-next-dialog" aria-live="polite">
                <el-icon class="is-loading gen-next-dialog-icon"><Loading /></el-icon>
                <span>正在生成第 {{ nextGeneratingIndex }} 题</span>
              </div>
            </div>

            <el-empty
              v-else-if="!predictStreaming"
              description="未收到题目，请返回上一步后重试"
              :image-size="72"
            />
          </div>
        </el-card>

        <el-card class="theme-card gen-right-card" shadow="hover">
          <div class="gen-toc-head">题目目录</div>
          <div ref="genTocScrollRef" class="gen-toc-scroll">
            <button
              v-for="(it, idx) in predictItems"
              :key="it.id"
              type="button"
              class="gen-toc-item"
              :class="{ active: idx === activePredictIndex }"
              :data-toc-index="idx"
              @click="activePredictIndex = idx"
            >
              {{ it.displayIndex }}
            </button>
            <button
              v-if="predictStreaming && !predictStreamDone"
              type="button"
              class="gen-toc-item generating"
              :data-toc-index="'generating'"
              disabled
            >
              <el-icon class="is-loading gen-toc-loading-icon"><Loading /></el-icon>
            </button>
            <p v-if="predictItems.length === 0 && !predictStreaming" class="gen-toc-empty">暂无题目</p>
          </div>
        </el-card>
      </div>
    </div>

    <div class="actions">
      <template v-if="currentStep === 1">
        <el-button @click="goPrevStep">上一步</el-button>
        <el-button
          type="primary"
          class="theme-primary-btn"
          :disabled="!canConfirmPredict"
          @click="confirmPredict"
        >
          开始生成押题
        </el-button>
      </template>
      <template v-else-if="currentStep === 2">
        <el-button type="primary" class="theme-primary-btn" @click="finishPredictFlow">完成</el-button>
      </template>
      <el-button
        v-else
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import {
  getPositionDetailApi,
  getSimplePositionPageApi,
  type HotJobItem,
  type SimplePositionItem,
} from '@/api/jobs';
import { streamPredictQuestions, type PredictQuestionStreamEvent } from '@/api/interviewAi';
import { getResumeListApi } from '@/api/resume';
import { useUserStore } from '@/store/user';
import { resolvePositionSlug } from '@/utils/positionSlug';
import InterviewPositionJobDetailBlock from '@/pages/Interview/InterviewPositionJobDetailBlock.vue';

const router = useRouter();
const userStore = useUserStore();

const selectedJobId = ref<number | undefined>(undefined);
const selectedJobLabel = ref('');
const positionSlug = ref('backend_engineer');
const currentStep = ref<0 | 1 | 2>(0);
type QuestionBankJobRow = HotJobItem & { responsibility: string };
const allJobs = ref<QuestionBankJobRow[]>([]);
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

type PredCard = {
  id: string;
  displayIndex: number;
  question: string;
  keyPoints: string;
  answer: string;
  difficulty: string;
  reveal: boolean;
};

const predictItems = ref<PredCard[]>([]);
const predictStreaming = ref(false);
const predictStreamDone = ref(false);
const predictStreamError = ref('');
const activePredictIndex = ref(0);
const genTocScrollRef = ref<HTMLElement | null>(null);
const exportingPdf = ref(false);
let predictStreamSession = 0;
let predictSeq = 0;

const currentPredictItem = computed(() => predictItems.value[activePredictIndex.value] ?? null);
const nextGeneratingIndex = computed(() => Math.max(1, predictItems.value.length + 1));

function parsePredictionPayload(data: Record<string, unknown>): Omit<PredCard, 'id' | 'reveal'> | null {
  const q = String(data.question ?? data.q ?? '').trim();
  if (!q) return null;
  const rawId = data.id;
  const numId = typeof rawId === 'number' ? rawId : Number(rawId);
  const displayIndex = Number.isFinite(numId) && numId > 0 ? numId : 0;

  const keyPoints = String(data.key_points ?? data.keyPoints ?? '').trim();
  const answer = String(
    data.answer ?? data.reference_answer ?? data.suggested_answer ?? data.reference ?? ''
  ).trim();
  const difficulty = String(data.difficulty ?? '').trim() || '—';

  return {
    displayIndex,
    question: q,
    keyPoints,
    answer: answer || '（暂无参考答案，请结合简历自行整理要点）',
    difficulty,
  };
}

function toggleCurrentReveal() {
  const it = predictItems.value[activePredictIndex.value];
  if (it) it.reveal = !it.reveal;
}

function sanitizeFileName(raw: string) {
  const name = String(raw || '').trim() || '押题题单';
  return name.replace(/[\\/:*?"<>|]/g, '_');
}

function createPredictExportWrapper(title: string, list: PredCard[]) {
  const wrapper = document.createElement('div');
  wrapper.className = 'qb-export-wrapper';
  wrapper.style.cssText = [
    'position:fixed',
    'left:-12000px',
    'top:0',
    'width:794px',
    'box-sizing:border-box',
    'padding:44px 54px',
    'background:#ffffff',
    'color:#111827',
    'font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif',
  ].join(';');

  const style = document.createElement('style');
  style.textContent = `
    .qb-export-header { margin-bottom: 16px; page-break-inside: avoid; break-inside: avoid; }
    .qb-export-title { margin: 0 0 8px; font-size: 24px; line-height: 1.3; font-weight: 700; color: #111827; }
    .qb-export-sub { margin: 0; font-size: 13px; color: #6b7280; }
    .qb-export-card { border: 1px solid #e5e7eb; border-radius: 12px; background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%); padding: 14px 16px; margin-bottom: 12px; page-break-inside: avoid; break-inside: avoid; }
    .qb-export-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 9px; }
    .qb-export-index { font-size: 12px; font-weight: 700; color: #6366f1; background: rgba(99, 102, 241, 0.1); padding: 3px 10px; border-radius: 999px; }
    .qb-export-diff { font-size: 11px; color: #6b7280; border: 1px solid #d1d5db; border-radius: 999px; padding: 2px 8px; }
    .qb-export-question { margin: 0 0 10px; font-size: 15px; line-height: 1.65; color: #1f2937; font-weight: 600; white-space: pre-wrap; word-break: break-word; }
    .qb-export-block { border-top: 1px dashed #e5e7eb; padding-top: 10px; }
    .qb-export-label { display: block; margin: 0 0 6px; font-size: 12px; letter-spacing: 0.04em; color: #6b7280; font-weight: 700; }
    .qb-export-key { margin: 0 0 10px; font-size: 13px; line-height: 1.55; color: #78350f; background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 40%, #fff 100%); border: 1px solid #fde68a; border-radius: 10px; padding: 10px 12px; white-space: pre-wrap; word-break: break-word; }
    .qb-export-answer { margin: 0; font-size: 13px; line-height: 1.65; color: #374151; background: #f9fafb; border: 1px solid #f3f4f6; border-radius: 10px; padding: 10px 12px; white-space: pre-wrap; word-break: break-word; }
  `;
  wrapper.appendChild(style);

  const header = document.createElement('section');
  header.className = 'qb-export-header';
  const titleEl = document.createElement('h1');
  titleEl.className = 'qb-export-title';
  titleEl.textContent = title;
  header.appendChild(titleEl);

  const subEl = document.createElement('p');
  subEl.className = 'qb-export-sub';
  subEl.textContent = `导出时间：${new Date().toLocaleString()}`;
  header.appendChild(subEl);
  wrapper.appendChild(header);

  for (const it of list) {
    const card = document.createElement('section');
    card.className = 'qb-export-card';

    const head = document.createElement('div');
    head.className = 'qb-export-head';
    const idx = document.createElement('span');
    idx.className = 'qb-export-index';
    idx.textContent = `第 ${it.displayIndex} 题`;
    head.appendChild(idx);
    if (it.difficulty && it.difficulty !== '—') {
      const diff = document.createElement('span');
      diff.className = 'qb-export-diff';
      diff.textContent = it.difficulty;
      head.appendChild(diff);
    }
    card.appendChild(head);

    const q = document.createElement('p');
    q.className = 'qb-export-question';
    q.textContent = it.question;
    card.appendChild(q);

    const block = document.createElement('div');
    block.className = 'qb-export-block';
    if (it.keyPoints) {
      const kl = document.createElement('span');
      kl.className = 'qb-export-label';
      kl.textContent = '关键要点';
      block.appendChild(kl);
      const kp = document.createElement('p');
      kp.className = 'qb-export-key';
      kp.textContent = it.keyPoints;
      block.appendChild(kp);
    }
    const al = document.createElement('span');
    al.className = 'qb-export-label';
    al.textContent = '参考答案';
    block.appendChild(al);
    const ans = document.createElement('p');
    ans.className = 'qb-export-answer';
    ans.textContent = it.answer || '（暂无参考答案）';
    block.appendChild(ans);
    card.appendChild(block);
    wrapper.appendChild(card);
  }
  return wrapper;
}

async function renderElementToCanvas(el: HTMLElement) {
  return html2canvas(el, {
    scale: 2,
    useCORS: true,
    logging: false,
    backgroundColor: '#ffffff',
  });
}

async function exportPredictPdf() {
  if (predictItems.value.length === 0) {
    ElMessage.warning('暂无可导出的题目');
    return;
  }
  if (exportingPdf.value) return;
  exportingPdf.value = true;
  const title = selectedJobLabel.value || '岗位押题题单';
  const wrapper = createPredictExportWrapper(title, predictItems.value);
  document.body.appendChild(wrapper);
  try {
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const pageMargin = 10;
    const contentWidth = pdfWidth - pageMargin * 2;
    const pageContentHeight = pdfHeight - pageMargin * 2;
    const sections = Array.from(
      wrapper.querySelectorAll<HTMLElement>('.qb-export-header, .qb-export-card')
    );
    let isFirstOnPage = true;
    let usedHeight = 0; // 当前页内容区已使用高度（不含页边距）

    for (const section of sections) {
      const canvas = await renderElementToCanvas(section);
      const imgData = canvas.toDataURL('image/png', 1);
      const drawHeight = (canvas.height * contentWidth) / canvas.width;
      const fitsCurrentPage = usedHeight + drawHeight <= pageContentHeight;

      if (!fitsCurrentPage && !isFirstOnPage) {
        pdf.addPage();
        usedHeight = 0;
        isFirstOnPage = true;
      }

      if (drawHeight <= pageContentHeight) {
        pdf.addImage(imgData, 'PNG', pageMargin, pageMargin + usedHeight, contentWidth, drawHeight);
        usedHeight += drawHeight;
        isFirstOnPage = false;
        continue;
      }

      // 极端长题：仅在必要时按页切，但这会影响单题完整性，通常不会触发
      let remaining = drawHeight;
      let y = 0;
      while (remaining > 0) {
        const space = pageContentHeight - usedHeight;
        const slice = Math.min(space, remaining);
        pdf.addImage(
          imgData,
          'PNG',
          pageMargin,
          pageMargin + usedHeight - y,
          contentWidth,
          drawHeight
        );
        remaining -= slice;
        y += slice;
        usedHeight = pageContentHeight;
        if (remaining > 0) {
          pdf.addPage();
          usedHeight = 0;
          isFirstOnPage = true;
        }
      }
      isFirstOnPage = false;
    }
    pdf.save(`${sanitizeFileName(title)}-押题题单.pdf`);
    ElMessage.success('题单已导出');
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '导出失败');
  } finally {
    document.body.removeChild(wrapper);
    exportingPdf.value = false;
  }
}

async function runPredictStream() {
  const rid = dialogResumeId.value;
  const pos = positionSlug.value;
  if (!rid || !pos || !Number.isFinite(rid) || rid <= 0) {
    ElMessage.warning('参数不完整');
    return;
  }

  const session = ++predictStreamSession;
  predictStreaming.value = true;
  predictStreamDone.value = false;
  predictStreamError.value = '';
  predictItems.value = [];
  predictSeq = 0;
  activePredictIndex.value = 0;

  try {
    await streamPredictQuestions({ resume_id: rid, position: pos }, (evt: PredictQuestionStreamEvent) => {
      if (session !== predictStreamSession) return;
      if (
        evt.type === 'prediction_item' ||
        evt.type === 'predict_question' ||
        evt.type === 'question'
      ) {
        const parsed = parsePredictionPayload(evt.data || {});
        if (!parsed) return;
        predictSeq += 1;
        const displayIndex = parsed.displayIndex > 0 ? parsed.displayIndex : predictSeq;
        predictItems.value.push({
          id: `pq-${displayIndex > 0 ? displayIndex : 'x'}-${Date.now()}-${predictSeq}`,
          displayIndex,
          question: parsed.question,
          keyPoints: parsed.keyPoints,
          answer: parsed.answer,
          difficulty: parsed.difficulty,
          reveal: false,
        });
        activePredictIndex.value = predictItems.value.length - 1;
      } else if (evt.type === 'error') {
        const msg = String((evt.data as { message?: string })?.message || '生成失败');
        predictStreamError.value = msg;
        ElMessage.error(msg);
      } else if (evt.type === 'predict_complete' || evt.type === 'prediction_complete') {
        predictStreamDone.value = true;
      }
    });
  } catch (e: unknown) {
    const msg = (e as Error).message || '请求失败';
    predictStreamError.value = msg;
    ElMessage.error(msg);
  } finally {
    if (session !== predictStreamSession) return;
    predictStreaming.value = false;
    if (predictItems.value.length > 0 && !predictStreamError.value && !predictStreamDone.value) {
      predictStreamDone.value = true;
    }
  }
}

watch(activePredictIndex, async () => {
  await nextTick();
  const wrap = genTocScrollRef.value;
  if (!wrap) return;
  const el = wrap.querySelector('.gen-toc-item.active') as HTMLElement | null;
  el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
});

function mapSimplePositionList(list: SimplePositionItem[]): QuestionBankJobRow[] {
  return list.map((it) => {
    const responsibility = String(it.responsibility ?? '').trim();
    return {
      id: Number(it.id),
      name: String(it.name || '未命名岗位'),
      companyName: '岗位库',
      companyLogo: '',
      salaryMin: '--',
      salaryMax: '--',
      jobContent: '',
      type: '岗位',
      responsibility,
    };
  });
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
    if (Number.isFinite(totalNum)) {
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
  if (currentStep.value === 2) {
    predictStreamSession += 1;
    predictStreaming.value = false;
    currentStep.value = 1;
    return;
  }
  if (currentStep.value === 1) {
    currentStep.value = 0;
  }
}

async function fetchPositionMeta(job: HotJobItem) {
  detailLoading.value = true;
  detailError.value = '';
  selectedJobDetail.value = null;
  try {
    const raw = await getPositionDetailApi(job.id);
    const detail = raw as unknown as Record<string, unknown>;
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

async function onPickJob(job: QuestionBankJobRow) {
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
  currentStep.value = 2;
  void runPredictStream();
}

function finishPredictFlow() {
  predictStreamSession += 1;
  predictStreaming.value = false;
  router.push({ name: 'Home' });
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
  predictStreamSession += 1;
});
</script>

<style scoped>
.question-bank-page {
  max-width: 1000px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-sizing: border-box;
  min-height: calc(100dvh - 132px);
  max-height: calc(100dvh - 132px);
  padding-top: 4px;
  padding-bottom: 10px;
}

.question-bank-page > .flow-steps-card {
  flex-shrink: 0;
}

.qb-main-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.flow-steps-card :deep(.el-card__body) {
  padding: 8px 14px 10px;
}

.step-layout,
.step-generate-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  gap: 10px;
  align-items: stretch;
}

.step-layout {
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
}

.step-generate-layout {
  grid-template-columns: minmax(0, 1fr) minmax(132px, 200px);
}

.gen-left-card,
.gen-right-card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.gen-left-card :deep(.el-card__body),
.gen-right-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
}

.gen-left-stack {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.gen-left-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.gen-left-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #374151;
  flex: 1;
  min-width: 0;
  line-height: 1.35;
  word-break: break-word;
}

.gen-export-btn {
  margin-left: auto;
}

.gen-status-tag {
  vertical-align: middle;
}

.gen-status-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  line-height: 1;
}

.gen-status-icon {
  font-size: 12px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
}

.gen-banner {
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1.5;
}

.gen-banner--error {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.gen-streaming-hint {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f5f3ff 0%, #eff6ff 100%);
  border: 1px solid #e9d5ff;
  color: #5b21b6;
  font-size: 14px;
}

.gen-spin {
  font-size: 20px;
}

.gen-question-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.gen-next-dialog {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px dashed #c7d2fe;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 12px;
}

.gen-next-dialog-icon {
  font-size: 14px;
}

.gen-toc-head {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.gen-toc-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, 34px);
  gap: 8px;
  align-content: start;
  justify-content: start;
  padding-right: 2px;
}

.gen-toc-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  text-align: center;
  padding: 0;
  border-radius: 8px;
  border: 1px solid #60a5fa;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}

.gen-toc-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.gen-toc-item.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: #ffffff;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.25);
}

.gen-toc-item.generating {
  border-style: dashed;
  background: #f8fbff;
  color: #3b82f6;
  box-shadow: none;
  gap: 3px;
  cursor: default;
}

.gen-toc-loading-icon {
  font-size: 11px;
}

.gen-toc-empty {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
  padding: 8px 4px;
  text-align: center;
  line-height: 1.5;
}

.pq-card {
  border-radius: 16px;
  border: none;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  box-shadow: none;
  padding: 16px 18px;
}

.pq-card-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.pq-diff-tag {
  border-color: #e5e7eb !important;
  color: #6b7280 !important;
  font-weight: 600;
}

.pq-index {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
  padding: 4px 10px;
  border-radius: 999px;
}

.pq-question {
  font-size: 15px;
  line-height: 1.65;
  color: #1f2937;
  font-weight: 600;
  margin-bottom: 14px;
  word-break: break-word;
}

.pq-answer-block {
  border-top: 1px dashed #e5e7eb;
  padding-top: 12px;
}

.pq-answer-placeholder {
  font-size: 13px;
  color: #9ca3af;
  line-height: 1.5;
  margin-bottom: 8px;
}

.pq-reveal-body {
  margin-bottom: 8px;
}

.pq-key-points {
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 35%, #fff 100%);
  border: 1px solid #fde68a;
}

.pq-key-points .sub-label {
  display: block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #b45309;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.pq-key-points-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #78350f;
  white-space: pre-wrap;
  word-break: break-word;
}

.pq-answer-text {
  font-size: 14px;
  line-height: 1.65;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 8px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid #f3f4f6;
}

.pq-reveal-btn {
  font-weight: 600;
}

.step-left-card,
.step-right-card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.step-left-card :deep(.el-card__body),
.step-right-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
}

.step-left-stack {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.step-right-stack {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.step-right-stack :deep(.job-detail-block) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.step-right-stack :deep(.selected-job-card),
.step-right-stack :deep(.detail-loading),
.step-right-stack :deep(.detail-error) {
  flex: 1;
  min-height: 0;
  max-height: none !important;
  overflow-y: auto;
}

.step-right-stack :deep(.el-empty) {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.step-resume-card {
  flex: 0 1 auto;
  max-height: 100%;
  overflow: auto;
  width: 100%;
}

.step-resume-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.flow-steps {
  margin: 0;
}

.flow-steps :deep(.el-step__title) {
  font-size: 13px;
  line-height: 1.3;
}

.intro {
  margin-top: 0;
  color: #4b5563;
  line-height: 1.65;
  margin-bottom: 20px;
}

.qb-form {
  max-width: 760px;
  flex-shrink: 0;
}

.qb-form :deep(.el-form-item) {
  margin-bottom: 10px;
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
  margin-top: 4px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
}

.job-card-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.job-card-progress {
  flex-shrink: 0;
}

.job-card-progress :deep(.el-progress-bar__outer) {
  border-radius: 0;
}

.job-card-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 8px 8px 6px;
  background: #fff;
}

.job-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.job-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: hidden;
}

.job-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
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
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  word-break: break-word;
}

.job-card-meta {
  font-size: 12px;
  color: #9ca3af;
  flex-shrink: 0;
  white-space: nowrap;
}

.job-card-responsibility {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.55;
  min-height: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  word-break: break-word;
}

.pager-wrap {
  flex-shrink: 0;
  margin-top: 8px;
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

.actions {
  flex-shrink: 0;
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

@media (max-width: 768px) {
  .question-bank-page {
    min-height: 0;
    max-height: none;
  }

  .qb-main-body {
    flex: none;
    min-height: 0;
  }

  .actions {
    margin-top: 10px;
  }

  .step-layout,
  .step-generate-layout {
    grid-template-columns: 1fr;
  }

  .step-left-card,
  .step-right-card,
  .gen-left-card,
  .gen-right-card {
    height: auto;
    min-height: 280px;
  }

  .gen-right-card :deep(.el-card__body) {
    max-height: 240px;
  }

  .gen-toc-scroll {
    grid-template-columns: repeat(auto-fill, 30px);
    gap: 6px;
  }

  .gen-toc-item {
    width: 30px;
    height: 30px;
    font-size: 11px;
  }
}
</style>
