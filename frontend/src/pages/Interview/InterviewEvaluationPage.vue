<template>
  <div class="evaluation-page theme-page-shell">
    <div class="eval-toolbar fade-in-up">
      <div class="eval-toolbar-start">
        <el-button class="theme-back-btn" @click="goBack">← 返回</el-button>
        <el-button class="theme-back-btn" @click="goHome">返回首页</el-button>
      </div>
      <el-button
        type="primary"
        class="theme-primary-btn"
        :disabled="!sessionId"
        @click="goInterviewSession"
      >
        查看面试会话
      </el-button>
    </div>

    <div class="theme-section-header fade-in-up delay-1">
      <h2 class="theme-section-title">
        面试评估报告
        <span>Evaluation</span>
      </h2>
      <div class="theme-section-decoration" />
      <div v-if="jobName || summaryPills.length" class="eval-meta-row">
        <span v-if="jobName" class="eval-meta-pill eval-meta-pill--job">岗位 · {{ jobName }}</span>
        <span v-for="(pill, idx) in summaryPills" :key="idx" class="eval-meta-pill">{{ pill }}</span>
      </div>
    </div>

    <el-skeleton v-if="loading" class="eval-skeleton theme-card" :rows="12" animated />
    <el-alert v-else-if="errorText" :title="errorText" type="error" show-icon class="eval-alert theme-card" />
    <div v-else-if="data" class="eval-body">
      <!-- 顶部：得分、结论、维度条 -->
      <section class="eval-hero theme-card fade-in-up delay-1">
        <div class="eval-hero-top">
          <div class="eval-hero-score">
            <span class="eval-hero-score-label">综合得分</span>
            <div class="eval-hero-score-row">
              <span class="eval-hero-score-num">{{ formatScore(data.overall_score) }}</span>
              <span class="eval-hero-score-max">/ 10</span>
            </div>
          </div>
          <div class="eval-hero-side">
            <div v-if="showRecommendationTag || String(data.confidence_level || '').trim()" class="eval-hero-chips">
              <el-tag
                v-if="showRecommendationTag"
                :type="recommendationTagType(data.recommendation)"
                effect="dark"
                size="large"
                class="eval-chip-rec"
              >
                {{ data.recommendation }}
              </el-tag>
              <el-tag
                v-if="String(data.confidence_level || '').trim()"
                type="info"
                effect="plain"
                size="large"
                class="eval-chip-conf"
              >
                置信度 · {{ data.confidence_level }}
              </el-tag>
            </div>
            <p v-if="primaryTechnologyLine" class="eval-hero-lead">{{ primaryTechnologyLine }}</p>
            <div v-if="technicalSummaryChips.length" class="eval-hero-stats">
              <span v-for="(c, i) in technicalSummaryChips" :key="i" class="eval-stat-pill">{{ c }}</span>
            </div>
          </div>
        </div>
        <div v-if="dimensionScores.length" class="eval-dim-block">
          <div class="eval-dim-title">维度得分</div>
          <div class="eval-dim-bars">
            <div v-for="m in dimensionScores" :key="m.key" class="eval-dim-row">
              <div class="eval-dim-head">
                <span class="eval-dim-name">{{ m.label }}</span>
                <span class="eval-dim-val">{{ formatScore(m.value) }}</span>
              </div>
              <div class="eval-dim-track" aria-hidden="true">
                <div class="eval-dim-fill" :style="{ width: dimBarPercent(m.value) }" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 考察话题 -->
      <el-card
        v-if="data.topic_coverage?.length"
        class="eval-panel theme-card fade-in-up delay-1"
        shadow="hover"
      >
        <template #header>
          <div class="eval-panel-head">
            <span class="eval-panel-title">考察话题</span>
            <span class="eval-panel-hint">本次对话涉及的主要方向</span>
          </div>
        </template>
        <div class="eval-chip-flow">
          <span v-for="(t, i) in data.topic_coverage" :key="i" class="eval-topic-chip">{{ t }}</span>
        </div>
      </el-card>

      <div class="eval-split">
        <el-card class="eval-panel theme-card fade-in-up delay-1" shadow="hover">
          <template #header>
            <div class="eval-panel-head eval-panel-head--ok">
              <span class="eval-panel-title">表现较好</span>
            </div>
          </template>
          <ul v-if="data.strong_topics?.length" class="eval-list eval-list--ok">
            <li v-for="(s, i) in data.strong_topics" :key="i">{{ s }}</li>
          </ul>
          <el-empty v-else description="暂无" :image-size="48" />
        </el-card>
        <el-card class="eval-panel theme-card fade-in-up delay-2" shadow="hover">
          <template #header>
            <div class="eval-panel-head eval-panel-head--warn">
              <span class="eval-panel-title">薄弱话题</span>
            </div>
          </template>
          <ul v-if="data.weak_topics?.length" class="eval-list eval-list--warn">
            <li v-for="(w, i) in data.weak_topics" :key="i">{{ w }}</li>
          </ul>
          <el-empty v-else description="暂无" :image-size="48" />
        </el-card>
      </div>

      <!-- 综合评述 -->
      <el-card v-if="data.overall_comment" class="eval-narrative theme-card fade-in-up delay-1" shadow="hover">
        <template #header>
          <div class="eval-panel-head">
            <span class="eval-panel-title">综合评述</span>
          </div>
        </template>
        <p class="eval-prose">{{ data.overall_comment }}</p>
      </el-card>

      <!-- 技术缺点（内含技术点解析） -->
      <el-card v-if="sortedTechnicalCards.length" class="eval-panel eval-tech eval-tech-root theme-card fade-in-up delay-2" shadow="hover">
        <template #header>
          <div class="eval-tech-section-head">
            <div class="eval-tech-section-titles">
              <h3 class="eval-tech-section-title">技术缺点</h3>
              <span class="eval-tech-section-sub">Technical gaps</span>
            </div>
            <p class="eval-tech-section-lead">按短板维度展开，内为对应技术点解析</p>
            <div class="eval-tech-section-deco" aria-hidden="true" />
          </div>
        </template>
        <el-collapse v-model="techCollapseActive" accordion class="eval-tech-collapse">
          <el-collapse-item
            v-for="(card, idx) in sortedTechnicalCards"
            :key="card.id ?? idx"
            :name="String(card.id ?? idx)"
          >
            <template #title>
              <div class="eval-tech-item-title">
                <span class="eval-tech-item-name">{{ card.title || '未命名短板' }}</span>
                <span class="eval-tech-item-badges">
                  <el-tag :type="technicalCardTagType(card.type)" size="small" effect="plain" class="eval-tech-type-tag">
                    {{ technicalCardTypeLabel(card.type) }}
                  </el-tag>
                  <el-tag v-if="card.category" type="info" size="small" effect="plain">{{ card.category }}</el-tag>
                  <span v-if="formatRelevancePercent(card.relevance_score) != null" class="eval-tech-rel">
                    相关度 {{ formatRelevancePercent(card.relevance_score) }}%
                  </span>
                </span>
              </div>
            </template>
            <div class="eval-tp-deck">
              <article
                v-for="(blk, pi) in resolveTechnicalPointBlocks(card)"
                :key="pi"
                class="eval-tp-card"
              >
                <header class="eval-tp-card-head">{{ blk.title }}</header>
                <p v-if="blk.brief" class="eval-tp-brief">{{ blk.brief }}</p>
                <p v-if="blk.detail" class="eval-tp-detail">{{ blk.detail }}</p>
              </article>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-card>

      <div class="eval-split">
        <el-card class="eval-panel theme-card fade-in-up delay-1" shadow="hover">
          <template #header>
            <div class="eval-panel-head eval-panel-head--ok">
              <span class="eval-panel-title">优势</span>
            </div>
          </template>
          <ul v-if="data.strengths?.length" class="eval-list eval-list--ok">
            <li v-for="(s, i) in data.strengths" :key="i">{{ s }}</li>
          </ul>
          <el-empty v-else description="暂无" :image-size="48" />
        </el-card>
        <el-card class="eval-panel theme-card fade-in-up delay-2" shadow="hover">
          <template #header>
            <div class="eval-panel-head eval-panel-head--warn">
              <span class="eval-panel-title">待提升</span>
            </div>
          </template>
          <ul v-if="data.weaknesses?.length" class="eval-list eval-list--warn">
            <li v-for="(w, i) in data.weaknesses" :key="i">{{ w }}</li>
          </ul>
          <el-empty v-else description="暂无" :image-size="48" />
        </el-card>
      </div>

      <el-card v-if="data.suggestions?.length" class="eval-panel theme-card fade-in-up delay-1" shadow="hover">
        <template #header>
          <div class="eval-panel-head">
            <span class="eval-panel-title">改进建议</span>
          </div>
        </template>
        <ol class="eval-ordered">
          <li v-for="(s, i) in data.suggestions" :key="i">{{ s }}</li>
        </ol>
      </el-card>

      <!-- 逐轮评价：时间线 -->
      <el-card v-if="sortedRoundEvaluations.length" class="eval-panel theme-card fade-in-up delay-2" shadow="hover">
        <template #header>
          <div class="eval-panel-head">
            <span class="eval-panel-title">逐轮评价</span>
          </div>
        </template>
        <div class="eval-timeline">
          <article v-for="item in sortedRoundEvaluations" :key="item.round" class="eval-timeline-item">
            <div class="eval-timeline-axis">
              <span class="eval-timeline-dot" />
              <span class="eval-timeline-line" aria-hidden="true" />
            </div>
            <div class="eval-timeline-card">
              <div class="eval-timeline-head">
                <span class="eval-timeline-badge">第 {{ item.round }} 轮</span>
                <span v-if="item.topic" class="eval-timeline-topic">{{ item.topic }}</span>
              </div>
              <p class="eval-timeline-body">{{ item.comment }}</p>
            </div>
          </article>
        </div>
      </el-card>

      <div class="eval-split eval-split--prose">
        <el-card v-if="data.technical_evaluation" class="eval-panel eval-prose-card theme-card fade-in-up delay-1" shadow="hover">
          <template #header>
            <div class="eval-panel-head">
              <span class="eval-panel-title">技术能力评价</span>
            </div>
          </template>
          <p class="eval-prose">{{ data.technical_evaluation }}</p>
        </el-card>
        <el-card
          v-if="data.communication_evaluation"
          class="eval-panel eval-prose-card theme-card fade-in-up delay-2"
          shadow="hover"
        >
          <template #header>
            <div class="eval-panel-head">
              <span class="eval-panel-title">沟通表达评价</span>
            </div>
          </template>
          <p class="eval-prose">{{ data.communication_evaluation }}</p>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getInterviewEvaluationApi, type InterviewEvaluationData, type InterviewTechnicalCard } from '@/api/interviewAi';

const route = useRoute();
const router = useRouter();

const sessionId = computed(() => String(route.params.sessionId || '').trim());
const jobName = computed(() => String(route.query.jobName || '').trim());

const loading = ref(true);
const errorText = ref('');
const data = ref<InterviewEvaluationData | null>(null);
const techCollapseActive = ref<string | number>('');

const showRecommendationTag = computed(() => {
  const r = String(data.value?.recommendation || '').trim();
  if (!r) return false;
  if (r === '待定') return false;
  return true;
});

const summaryPills = computed(() => {
  const d = data.value;
  if (!d) return [];
  const pills: string[] = [];
  if (typeof d.total_rounds === 'number' && Number.isFinite(d.total_rounds)) {
    pills.push(`共 ${d.total_rounds} 轮`);
  }
  if (typeof d.duration_minutes === 'number' && Number.isFinite(d.duration_minutes)) {
    const mins = Math.round(d.duration_minutes * 10) / 10;
    pills.push(`约 ${mins} 分钟`);
  }
  return pills;
});

const primaryTechnologyLine = computed(() => {
  const s = data.value?.technical_summary;
  const line = String(s?.primary_technology || '').trim();
  return line ? `主技术栈 · ${line}` : '';
});

const technicalSummaryChips = computed(() => {
  const s = data.value?.technical_summary;
  if (!s) return [];
  const chips: string[] = [];
  if (typeof s.total_cards === 'number' && Number.isFinite(s.total_cards)) {
    chips.push(`技术缺点 ${s.total_cards} 项`);
  }
  if (typeof s.mastered_count === 'number' && Number.isFinite(s.mastered_count)) {
    chips.push(`已掌握 ${s.mastered_count}`);
  }
  if (typeof s.needs_improvement_count === 'number' && Number.isFinite(s.needs_improvement_count)) {
    chips.push(`待加强 ${s.needs_improvement_count}`);
  }
  return chips;
});

const dimensionScores = computed(() => {
  const d = data.value;
  if (!d) return [];
  const items: { key: string; label: string; value: number | undefined }[] = [
    { key: 'tc', label: '技术能力', value: d.technical_competency },
    { key: 'cs', label: '沟通表达', value: d.communication_skill },
    { key: 'ps', label: '问题解决', value: d.problem_solving },
    { key: 'dk', label: '知识深度', value: d.depth_of_knowledge },
  ];
  return items.filter((x) => typeof x.value === 'number' && !Number.isNaN(x.value as number));
});

const sortedRoundEvaluations = computed(() => {
  const list = data.value?.round_evaluations;
  if (!Array.isArray(list) || !list.length) return [];
  return [...list]
    .filter((x) => x && typeof x.round === 'number')
    .sort((a, b) => a.round - b.round)
    .map((x) => ({
      round: x.round,
      topic: String(x.topic || '').trim(),
      comment: String(x.comment || '').trim(),
    }));
});

function technicalCardWeaknessRank(type: string | undefined) {
  const t = String(type || '').toLowerCase();
  if (t === 'needs_improvement') return 0;
  if (t === 'mastered') return 1;
  return 2;
}

const sortedTechnicalCards = computed((): InterviewTechnicalCard[] => {
  const list = data.value?.technical_cards;
  if (!Array.isArray(list) || !list.length) return [];
  return [...list].sort((a, b) => {
    const w = technicalCardWeaknessRank(a.type) - technicalCardWeaknessRank(b.type);
    if (w !== 0) return w;
    const ra = Number(a.relevance_score);
    const rb = Number(b.relevance_score);
    const na = Number.isFinite(ra) ? ra : -1;
    const nb = Number.isFinite(rb) ? rb : -1;
    return nb - na;
  });
});

/** 技术缺点条目内的技术点解析块：优先嵌套数组，否则用父级 brief/detailed 合成一条 */
function resolveTechnicalPointBlocks(card: InterviewTechnicalCard) {
  const raw =
    (Array.isArray(card.technical_point_cards) && card.technical_point_cards.length
      ? card.technical_point_cards
      : null) ??
    (Array.isArray(card.topic_analysis_cards) && card.topic_analysis_cards.length ? card.topic_analysis_cards : null);
  if (raw?.length) {
    return raw.map((p, i) => {
      const title = String(p.title || `技术点解析 ${i + 1}`).trim() || `技术点解析 ${i + 1}`;
      const brief = String(p.brief_description || p.summary || '').trim();
      const detail = String(p.detailed_explanation || p.detail || '').trim();
      return { title, brief, detail };
    });
  }
  const brief = String(card.brief_description || '').trim();
  const detail = String(card.detailed_explanation || '').trim();
  if (!brief && !detail) return [];
  return [{ title: '技术点解析', brief, detail }];
}

function recommendationTagType(r: string | undefined): 'success' | 'warning' | 'info' | 'danger' {
  const t = String(r || '').trim();
  if (/不推荐|不建议录用|不通过|淘汰/.test(t)) return 'danger';
  if (/推荐|建议录用|通过|录用/.test(t)) return 'success';
  return 'warning';
}

function technicalCardTypeLabel(type: string | undefined) {
  const t = String(type || '').toLowerCase();
  if (t === 'needs_improvement') return '待加强';
  if (t === 'mastered') return '已掌握';
  return String(type || '—').trim() || '—';
}

function technicalCardTagType(type: string | undefined): 'success' | 'warning' | 'info' {
  const t = String(type || '').toLowerCase();
  if (t === 'needs_improvement') return 'warning';
  if (t === 'mastered') return 'success';
  return 'info';
}

function formatRelevancePercent(n: number | undefined): number | null {
  if (n == null || Number.isNaN(Number(n))) return null;
  return Math.round(Number(n) * 100);
}

function formatScore(n: number | undefined) {
  if (n == null || Number.isNaN(Number(n))) return '--';
  const num = Number(n);
  if (!Number.isFinite(num)) return '--';
  if (Number.isInteger(num)) return String(num);
  return num.toFixed(1);
}

function dimBarPercent(v: number | undefined) {
  if (v == null || Number.isNaN(Number(v))) return '0%';
  const pct = Math.min(100, Math.max(0, (Number(v) / 10) * 100));
  return `${pct}%`;
}

function goBack() {
  router.back();
}

function goHome() {
  router.push({ name: 'Home' });
}

function goInterviewSession() {
  const sid = String(data.value?.session_id || sessionId.value).trim();
  if (!sid) return;
  const interviewMode = String(route.query.interviewMode || '').trim().toLowerCase();
  router.push({
    name: interviewMode === 'avatar' ? 'InterviewSessionAvatar' : 'InterviewSessionText',
    params: { id: sid },
    query: {
      sessionId: sid,
      jobName: jobName.value || undefined,
      interviewMode: interviewMode || undefined,
      avatarId: route.query.avatarId || undefined,
      avatarVcn: route.query.avatarVcn || undefined,
    },
  });
}

async function load() {
  const sid = sessionId.value;
  if (!sid) {
    errorText.value = '缺少会话 ID';
    loading.value = false;
    return;
  }
  loading.value = true;
  errorText.value = '';
  try {
    data.value = await getInterviewEvaluationApi(sid);
  } catch (e: unknown) {
    const msg = (e as Error).message || '加载报告失败';
    errorText.value = msg;
    ElMessage.error(msg);
    data.value = null;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [String(route.name || ''), String(route.query.jobName || '').trim()] as const,
  ([n, job]) => {
    if (n !== 'InterviewEvaluation') return;
    document.title = job || '面试评估报告';
  },
  { immediate: true }
);

onMounted(load);
</script>

<style scoped>
.evaluation-page {
  max-width: 1040px;
  margin: 0 auto;
  padding-bottom: 32px;
  color: #1f2937;
}

.eval-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.eval-toolbar-start {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.theme-section-header {
  margin-bottom: 20px;
}

.eval-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.eval-meta-pill {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  max-width: 100%;
}

.eval-meta-pill--job {
  border-color: #c4b5fd;
  background: linear-gradient(90deg, #f5f3ff 0%, #eef2ff 100%);
  color: #4338ca;
}

.eval-skeleton {
  padding: 20px;
  border-radius: 16px !important;
}

.eval-alert {
  padding: 12px 16px;
  border-radius: 16px !important;
}

.eval-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* —— 顶部英雄区 —— */
.eval-hero {
  position: relative;
  overflow: hidden;
  border-radius: 16px !important;
  border: 1px solid #e5e7eb !important;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 48%, #f5f3ff 100%) !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 1) !important;
  padding: 22px 22px 20px;
}

.eval-hero::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
  background: linear-gradient(180deg, #a855f7, #3b82f6);
}

.eval-hero-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px 24px;
  padding-left: 8px;
}

.eval-hero-score-label {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.eval-hero-score-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 6px;
}

.eval-hero-score-num {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 42%, #3b82f6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.eval-hero-score-max {
  font-size: 1rem;
  font-weight: 700;
  color: #94a3b8;
}

.eval-hero-side {
  flex: 1;
  min-width: min(100%, 280px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.eval-hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eval-chip-rec {
  font-weight: 700;
  border-radius: 10px !important;
}

.eval-chip-conf {
  font-weight: 600;
  border-radius: 10px !important;
}

.eval-hero-lead {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #475569;
  font-weight: 600;
}

.eval-hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eval-stat-pill {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #4338ca;
}

.eval-dim-block {
  margin-top: 20px;
  padding: 16px 8px 4px;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
}

.eval-dim-title {
  font-size: 12px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.eval-dim-bars {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 20px;
}

.eval-dim-row {
  min-width: 0;
}

.eval-dim-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.eval-dim-name {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.eval-dim-val {
  font-size: 13px;
  font-weight: 800;
  color: #4338ca;
  font-variant-numeric: tabular-nums;
}

.eval-dim-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.eval-dim-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6366f1, #8b5cf6 55%, #3b82f6);
  transition: width 0.35s ease;
}

/* —— 通用面板 —— */
.eval-panel {
  border-radius: 16px !important;
}

.eval-panel :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #fafafa 0%, #fff 100%);
}

.eval-panel :deep(.el-card__body) {
  padding: 16px 18px 18px;
}

.eval-panel-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.eval-panel-head--ok {
  border-left: 3px solid #10b981;
  padding-left: 10px;
  margin: -2px 0;
}

.eval-panel-head--warn {
  border-left: 3px solid #f59e0b;
  padding-left: 10px;
  margin: -2px 0;
}

.eval-panel-title {
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.02em;
}

.eval-panel-hint {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}

.eval-chip-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eval-topic-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #3730a3;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
  border: 1px solid rgba(99, 102, 241, 0.22);
  max-width: 100%;
  line-height: 1.4;
}

.eval-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.eval-split--prose {
  align-items: stretch;
}

.eval-list {
  margin: 0;
  padding-left: 1.15rem;
  line-height: 1.72;
  color: #334155;
  font-size: 14px;
}

.eval-list li + li {
  margin-top: 8px;
}

.eval-list--ok li::marker {
  color: #10b981;
}

.eval-list--warn li::marker {
  color: #f59e0b;
}

.eval-narrative {
  border-radius: 16px !important;
  border-left: 4px solid #6366f1 !important;
}

.eval-narrative :deep(.el-card__header) {
  background: linear-gradient(90deg, #f5f3ff 0%, #fff 100%);
}

.eval-narrative :deep(.el-card__body) {
  padding: 18px 20px 22px;
}

.eval-prose {
  margin: 0;
  line-height: 1.78;
  color: #334155;
  font-size: 14px;
  white-space: pre-wrap;
}

.eval-ordered {
  margin: 0;
  padding-left: 1.25rem;
  line-height: 1.75;
  color: #334155;
  font-size: 14px;
}

.eval-ordered li + li {
  margin-top: 10px;
}

.eval-ordered li::marker {
  font-weight: 800;
  color: #6366f1;
}

/* 技术缺点区块：与 theme-section / theme-card 一致的页内标题与折叠样式 */
.eval-tech-root :deep(.el-card__header) {
  padding: 16px 18px 14px;
  border-bottom: 1px solid #f1f5f9 !important;
  background: linear-gradient(180deg, #fafafa 0%, #ffffff 100%) !important;
}

.eval-tech-section-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.eval-tech-section-titles {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.eval-tech-section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.02em;
}

.eval-tech-section-sub {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}

.eval-tech-section-lead {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  font-weight: 500;
  color: #64748b;
}

.eval-tech-section-deco {
  width: 44px;
  height: 4px;
  margin-top: 4px;
  border-radius: 2px;
  background: linear-gradient(90deg, #a855f7, #3b82f6);
}

.eval-tech-root :deep(.el-card__body) {
  padding: 16px 18px 18px;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 40%);
}

.eval-tech :deep(.el-collapse) {
  border: none;
}

.eval-tech :deep(.el-collapse-item) {
  border: none;
  margin-bottom: 10px;
}

.eval-tech :deep(.el-collapse-item:last-child) {
  margin-bottom: 0;
}

.eval-tech :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 48px;
  line-height: 1.4;
  padding: 12px 14px !important;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  border-radius: 12px !important;
  border: 1px solid #e5e7eb !important;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%) !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 1);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.eval-tech :deep(.el-collapse-item__header:hover) {
  border-color: rgba(59, 130, 246, 0.28) !important;
  box-shadow: 0 4px 12px -4px rgba(59, 130, 246, 0.12), inset 0 1px 0 rgba(255, 255, 255, 1);
}

.eval-tech :deep(.el-collapse-item__wrap) {
  border: none !important;
  background: transparent;
}

.eval-tech :deep(.el-collapse-item__content) {
  padding: 12px 2px 4px 10px;
  color: #475569;
}

.eval-tech :deep(.el-collapse-item__arrow) {
  color: #7c3aed;
  font-weight: 700;
}

.eval-tech-item-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  width: 100%;
  padding-right: 8px;
}

.eval-tech-item-name {
  flex: 1;
  min-width: 0;
  font-weight: 800;
  color: #0f172a;
}

.eval-tech-item-badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.eval-tech-type-tag {
  font-weight: 700 !important;
}

.eval-tech-rel {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  margin-left: 4px;
}

.eval-tp-deck {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.eval-tp-card {
  position: relative;
  margin: 0;
  padding: 12px 14px 14px 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 1);
}

.eval-tp-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: linear-gradient(180deg, #a855f7, #3b82f6);
}

.eval-tp-card-head {
  font-size: 12px;
  font-weight: 800;
  color: #4338ca;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}

.eval-tp-brief {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.65;
  font-weight: 600;
  color: #475569;
}

.eval-tp-detail {
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  color: #334155;
}

/* 时间线 */
.eval-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-left: 4px;
}

.eval-timeline-item {
  display: flex;
  gap: 14px;
  position: relative;
}

.eval-timeline-axis {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
  padding-top: 6px;
}

.eval-timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.35);
  z-index: 1;
}

.eval-timeline-line {
  flex: 1;
  width: 2px;
  min-height: 12px;
  margin-top: 2px;
  background: linear-gradient(180deg, #c4b5fd, #e2e8f0);
  border-radius: 1px;
}

.eval-timeline-item:last-child .eval-timeline-line {
  display: none;
}

.eval-timeline-card {
  flex: 1;
  min-width: 0;
  padding-bottom: 18px;
}

.eval-timeline-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-bottom: 8px;
}

.eval-timeline-badge {
  font-size: 11px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  padding: 4px 10px;
  border-radius: 999px;
  letter-spacing: 0.04em;
}

.eval-timeline-topic {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.eval-timeline-body {
  margin: 0;
  font-size: 14px;
  line-height: 1.72;
  color: #475569;
  white-space: pre-wrap;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.eval-prose-card {
  height: 100%;
}

@media (max-width: 900px) {
  .eval-dim-bars {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .eval-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .eval-toolbar .theme-back-btn,
  .eval-toolbar .theme-primary-btn {
    width: 100%;
  }

  .eval-split,
  .eval-split--prose {
    grid-template-columns: 1fr;
  }

  .eval-hero-score-num {
    font-size: 2.5rem;
  }
}
</style>
