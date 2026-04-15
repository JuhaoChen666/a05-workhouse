<template>
  <div class="predict-page theme-page-shell">
    <div class="predict-header">
      <el-button text class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="header-text">
        <h1 class="title">{{ jobTitleDisplay }}</h1>
      </div>
    </div>

    <div class="predict-body">
      <div v-if="streamError" class="banner banner--error">
        {{ streamError }}
      </div>

      <div v-if="streaming && items.length === 0" class="streaming-hint" aria-live="polite">
        <el-icon class="is-loading spin"><Loading /></el-icon>
        <span>AI 正在结合简历与岗位生成题目，请稍候…</span>
      </div>

      <div ref="listWrapRef" class="list-wrap">
        <TransitionGroup name="pq-rise" tag="div" class="pq-list">
          <article
            v-for="it in items"
            :key="it.id"
            class="pq-card"
          >
            <div class="pq-card-head">
              <span class="pq-index">第 {{ it.displayIndex }} 题</span>
              <el-tag v-if="it.difficulty && it.difficulty !== '—'" size="small" effect="plain" class="pq-diff-tag">
                {{ it.difficulty }}
              </el-tag>
            </div>
            <div class="pq-question">{{ it.question }}</div>
            <div class="pq-answer-block">
              <div v-if="!it.reveal" class="pq-answer-placeholder">
                参考答案与要点已生成，默认隐藏；可先独立思考后再展开对照
              </div>
              <div v-else class="pq-reveal-body">
                <div v-if="it.keyPoints" class="pq-key-points">
                  <span class="sub-label">关键要点</span>
                  <p class="pq-key-points-text">{{ it.keyPoints }}</p>
                </div>
                <div class="pq-answer-text">{{ it.answer }}</div>
              </div>
              <el-button
                type="primary"
                link
                class="pq-reveal-btn"
                @click="it.reveal = !it.reveal"
              >
                {{ it.reveal ? '隐藏答案' : '查看答案' }}
              </el-button>
            </div>
          </article>
        </TransitionGroup>
      </div>

      <div v-if="!streaming && items.length === 0 && !streamError" class="empty-hint">
        未收到题目，请返回重试。
      </div>

      <div v-if="streamDone && items.length > 0" class="done-bar" aria-live="polite">
        已生成 {{ items.length }} 题
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft, Loading } from '@element-plus/icons-vue';
import { streamPredictQuestions } from '@/api/interviewAi';

const route = useRoute();
const router = useRouter();

const resumeId = computed(() => Number(route.query.resumeId));
const position = computed(() => String(route.query.position || '').trim());
const jobTitleDisplay = computed(() => {
  const raw = route.query.jobName;
  const s = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw[0] : '';
  if (!s) return '岗位押题';
  if (!/%[0-9A-Fa-f]{2}/.test(s)) return s;
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
});

type PredCard = {
  id: string;
  displayIndex: number;
  question: string;
  keyPoints: string;
  answer: string;
  difficulty: string;
  reveal: boolean;
};

const items = ref<PredCard[]>([]);
const streaming = ref(true);
const streamDone = ref(false);
const streamError = ref('');
const listWrapRef = ref<HTMLElement | null>(null);
let seq = 0;

function goBack() {
  router.push({ name: 'HomeQuestion' });
}

/** 解析 prediction_item 或旧版 predict_question / question */
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

async function runStream() {
  const rid = resumeId.value;
  const pos = position.value;
  if (!Number.isFinite(rid) || rid <= 0 || !pos) {
    ElMessage.warning('参数不完整，请从题库页重新进入');
    goBack();
    return;
  }

  streaming.value = true;
  streamDone.value = false;
  streamError.value = '';
  items.value = [];
  seq = 0;

  try {
    await streamPredictQuestions({ resume_id: rid, position: pos }, (evt) => {
      if (
        evt.type === 'prediction_item' ||
        evt.type === 'predict_question' ||
        evt.type === 'question'
      ) {
        const parsed = parsePredictionPayload(evt.data || {});
        if (!parsed) return;
        seq += 1;
        const displayIndex = parsed.displayIndex > 0 ? parsed.displayIndex : seq;
        items.value.push({
          id: `pq-${parsed.displayIndex > 0 ? parsed.displayIndex : 'x'}-${Date.now()}-${seq}`,
          displayIndex,
          question: parsed.question,
          keyPoints: parsed.keyPoints,
          answer: parsed.answer,
          difficulty: parsed.difficulty,
          reveal: false,
        });
        void nextTick(() => {
          listWrapRef.value?.scrollTo({
            top: listWrapRef.value.scrollHeight,
            behavior: 'smooth',
          });
        });
      } else if (evt.type === 'error') {
        const msg = String((evt.data as { message?: string })?.message || '生成失败');
        streamError.value = msg;
        ElMessage.error(msg);
      } else if (evt.type === 'predict_complete' || evt.type === 'prediction_complete') {
        streamDone.value = true;
      }
    });
  } catch (e: unknown) {
    const msg = (e as Error).message || '请求失败';
    streamError.value = msg;
    ElMessage.error(msg);
  } finally {
    streaming.value = false;
    if (items.value.length > 0 && !streamError.value && !streamDone.value) {
      streamDone.value = true;
    }
  }
}

onMounted(() => {
  void runStream();
});
</script>

<style scoped>
.predict-page {
  max-width: 880px;
  margin: 0 auto;
  padding-bottom: 32px;
}

.predict-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.back-btn {
  flex-shrink: 0;
  padding: 8px 10px;
  color: #4b5563;
}

.header-text {
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #374151;
  letter-spacing: 0.02em;
  line-height: 1.35;
  word-break: break-word;
}

.predict-body {
  position: relative;
}

.banner {
  padding: 12px 14px;
  border-radius: 10px;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.banner--error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.streaming-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f5f3ff 0%, #eff6ff 100%);
  border: 1px solid #e9d5ff;
  color: #5b21b6;
  font-size: 14px;
}

.streaming-hint .spin {
  font-size: 20px;
}

.list-wrap {
  max-height: min(70vh, 640px);
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.pq-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pq-card {
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
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

.empty-hint {
  text-align: center;
  color: #9ca3af;
  padding: 24px;
  font-size: 14px;
}

.done-bar {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

/* 自下而上浮现 */
.pq-rise-enter-active {
  transition:
    opacity 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.pq-rise-enter-from {
  opacity: 0;
  transform: translateY(28px);
}

.pq-rise-move {
  transition: transform 0.35s ease;
}
</style>
