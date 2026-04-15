<template>
  <div class="interview-session-root">
    <InterviewFlowDock
      ref="flowDockRef"
      :visible="showFlowDock"
      :open="flowPanelOpen"
      :duration-display="interviewDurationDisplay"
      :focus-status="flowDockFocusStatus"
      :focus-topic="flowDockFocusTopicDisplay"
      :nodes="flowNodes"
      :tooltip-lines="flowNodeTooltipLines"
      @update:open="flowPanelOpen = $event"
      @activate-node="onFlowStepActivate"
    />
    <InterviewMaterialsDock
      :visible="showMaterialsDock"
      :open="materialsPanelOpen"
      :has-session-resume="hasSessionResume"
      :session-resume-loading="sessionResumeLoading"
      :session-resume-error="sessionResumeError"
      :session-resume-pdf-src="sessionResumePdfSrc"
      :session-resume-plain-text="sessionResumePlainText"
      :session-resume-title="sessionResumeTitle"
      :resume-thumb-zoom-percent="resumeThumbZoomPercent"
      :resume-thumb-dragging="resumeThumbDragging"
      :resume-thumb-pan-x="resumeThumbPanX"
      :resume-thumb-pan-y="resumeThumbPanY"
      :resume-thumb-scale="resumeThumbScale"
      @update:open="materialsPanelOpen = $event"
      @zoom-in="resumeThumbZoomIn"
      @zoom-out="resumeThumbZoomOut"
      @zoom-reset="resumeThumbPanZoomReset"
      @thumb-wheel="onResumeThumbWheel"
      @thumb-pointer-down="onResumeThumbPointerDown"
      @thumb-pointer-move="onResumeThumbPointerMove"
      @thumb-pointer-up="onResumeThumbPointerUp"
    />

    <div
      class="interview-session-main-wrap"
      :class="mainWrapDockClass"
    >
    <div class="interview-session-page interview-session--gpt theme-page-shell">
    <el-card class="session-card session-card--gpt" shadow="never">
      <template #header>
        <div class="gpt-topbar">
          <div class="gpt-topbar-side gpt-topbar-side--left">
            <div class="window-traffic-lights" role="toolbar" aria-label="窗口操作">
              <button
                type="button"
                class="window-traffic-slot window-traffic-btn window-traffic-btn--close"
                title="结束面试"
                aria-label="结束面试"
                @click="onLeavePage"
              >
                <span class="window-traffic-dot window-traffic-dot--close" aria-hidden="true" />
              </button>
              <span class="window-traffic-slot window-traffic-slot--decorative" aria-hidden="true">
                <span class="window-traffic-dot window-traffic-dot--min" />
              </span>
              <span class="window-traffic-slot window-traffic-slot--decorative" aria-hidden="true">
                <span class="window-traffic-dot window-traffic-dot--zoom" />
              </span>
            </div>
          </div>
          <div class="gpt-topbar-center">
            <span class="gpt-title-text">{{ pageInterviewTopic }}</span>
          </div>
          <div class="gpt-topbar-side gpt-topbar-side--right" aria-hidden="true" />
        </div>
      </template>

      <el-alert
        v-if="showMissingSessionAlert"
        title="请先完成面试设置"
        type="warning"
        description="请从岗位详情进入「面试设置」页并开始面试。"
        show-icon
        class="mb-16"
      />

      <template v-else-if="canRenderInterview">
        <div class="session-workspace">
          <div class="conference-right">
            <div class="chat-panel-wrap">
              <div class="chat-panel" ref="chatPanelRef" @scroll.passive="onChatPanelScroll">
              <div
                v-for="(m, idx) in messages"
                :key="idx"
                class="msg"
                :class="m.role === 'user' ? 'msg-user' : 'msg-ai'"
                :data-chat-index="idx"
              >
                <div class="msg-row">
                  <el-avatar class="msg-avatar" :size="30" :src="m.role === 'user' ? userAvatar : aiAvatarSrc">
                    {{ m.role === 'user' ? '我' : 'AI' }}
                  </el-avatar>
                  <div>
                    <div class="msg-label">{{ m.role === 'user' ? '我' : m.tone === 'error' ? '提示' : '面试官' }}</div>
                    <div
                      class="msg-bubble"
                      :class="{
                        'msg-bubble-error': m.role === 'assistant' && m.tone === 'error',
                        'msg-bubble-voice': m.role === 'user' && m.kind === 'voice',
                      }"
                    >
                      <template v-if="m.kind === 'voice'">
                        <div class="voice-topline">
                          <span class="voice-icon">🔊</span>
                          <span class="voice-duration">{{ formatVoiceDuration(m.voiceDurationSec) }}</span>
                        </div>
                        <div v-if="m.transcript" class="msg-transcript">{{ m.transcript }}</div>
                      </template>
                      <template v-else>
                        {{ m.content }}
                      </template>
                    </div>
                  </div>
                </div>
              </div>
              <div
                v-if="showReportInvite && effectiveSessionId"
                class="report-share-card"
                role="button"
                tabindex="0"
                @click="goEvaluationReport"
                @keydown.enter.prevent="goEvaluationReport"
              >
                <div class="report-share-thumb" aria-hidden="true">
                  <span class="report-share-icon">📋</span>
                </div>
                <div class="report-share-body">
                  <div class="report-share-title">面试评估报告</div>
                  <div class="report-share-desc">点击查看 AI 综合评分与录用建议</div>
                </div>
                <el-icon class="report-share-arrow"><ArrowRight /></el-icon>
              </div>
              <div v-if="streaming" class="msg msg-ai">
                <div class="msg-row">
                  <el-avatar class="msg-avatar" :size="30" :src="aiAvatarSrc">AI</el-avatar>
                  <div>
                    <div class="msg-label">面试官</div>
                    <div class="msg-bubble streaming">
                      <span v-if="showThinkingHint" class="thinking-hint">面试官思考中...</span>
                      <br v-if="showThinkingHint" />
                      {{ streamingText }}<span class="cursor">▍</span>
                    </div>
                  </div>
                </div>
              </div>
              </div>
              <transition name="chat-scroll-fab">
                <button
                  v-show="showChatScrollToBottomFab"
                  type="button"
                  class="chat-scroll-to-bottom-fab"
                  aria-label="回到底部"
                  title="回到底部"
                  @click="onClickScrollChatToBottom"
                >
                  <el-icon><ArrowDown /></el-icon>
                </button>
              </transition>
            </div>

            <div class="composer composer-integrated">
              <div class="composer-shell" :class="{ 'composer-shell--recording': isRecording }">
                <div v-show="isRecording" class="composer-wave" aria-hidden="true">
                  <div
                    v-for="(level, i) in waveformBars"
                    :key="i"
                    class="composer-wave-bar"
                    :style="{ transform: `scaleY(${0.12 + level * 0.88})` }"
                  />
                </div>
                <p v-if="isRecording" class="composer-rec-hint">正在聆听，再次点击麦克风结束并发送</p>
                <el-input
                  v-model="userInput"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 6 }"
                  :maxlength="INTERVIEW_ANSWER_MAX_LEN"
                  show-word-limit
                  :placeholder="
                    isRecording ? '录音中…' : '输入回答，Enter 发送 · Shift+Enter 换行'
                  "
                  :disabled="streaming || isRecording || interviewEnded"
                  class="composer-field"
                  @keydown.enter.exact.prevent="sendMessage"
                />
                <div class="composer-toolbar">
                  <el-button
                    circle
                    type="danger"
                    class="composer-tool-btn composer-hangup-btn"
                    title="结束面试"
                    aria-label="结束面试"
                    @click="onLeavePage"
                  >
                    <el-icon class="composer-hangup-icon"><PhoneFilled /></el-icon>
                  </el-button>
                  <el-button
                    circle
                    :type="isRecording ? 'danger' : 'default'"
                    :disabled="streaming || interviewEnded"
                    class="composer-tool-btn"
                    :title="isRecording ? '停止并发送' : '语音回答'"
                    @click="toggleVoiceRecord"
                  >
                    <el-icon><Microphone /></el-icon>
                  </el-button>
                  <el-button
                    circle
                    type="primary"
                    :disabled="streaming || isRecording || interviewEnded || !userInput.trim()"
                    class="composer-tool-btn composer-send-btn"
                    title="发送"
                    @click="sendMessage"
                  >
                    <el-icon><Right /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-card>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, watchEffect, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useViewport } from '@/composables/useViewport';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Microphone,
  Right,
  ArrowDown,
  ArrowRight,
  PhoneFilled,
} from '@element-plus/icons-vue';
import {
  startInterviewApi,
  streamInterviewAnswer,
  streamInterviewVoiceAnswer,
  getInterviewSessionApi,
  endInterviewSessionApi,
  type StartInterviewBody,
  type InterviewAnswerStreamEvent,
  type InterviewSessionInfo,
} from '@/api/interviewAi';
import { useUserStore } from '@/store/user';
import { apiOrigin } from '@/api/request';
import { getResumeItemApi } from '@/api/resume';
import { RESUME_FILE_PUBLIC_BASE_URL } from '@/config/resumeAssets';
import InterviewFlowDock from '@/pages/Home/components/InterviewFlowDock.vue';
import InterviewMaterialsDock from '@/pages/Home/components/InterviewMaterialsDock.vue';

/** 文字作答最大字数（与输入框 maxlength 一致） */
const INTERVIEW_ANSWER_MAX_LEN = 400;

const SESSION_RESUME_STORAGE_PREFIX = 'interviewSessionResumeMeta:';

type PendingInterviewStart = Partial<StartInterviewBody> & {
  resume?: string;
  interview_mode?: string;
};

type SessionResumeCache = {
  resumeId?: number;
  resumeText?: string;
  displayName?: string;
};

function sessionResumeStorageKey(sessionId: string) {
  return `${SESSION_RESUME_STORAGE_PREFIX}${sessionId}`;
}

function readSessionResumeCache(sessionId: string): SessionResumeCache | null {
  if (!sessionId.trim()) return null;
  try {
    const raw = sessionStorage.getItem(sessionResumeStorageKey(sessionId));
    if (!raw) return null;
    return JSON.parse(raw) as SessionResumeCache;
  } catch {
    return null;
  }
}

function writeSessionResumeCache(sessionId: string, data: SessionResumeCache) {
  sessionStorage.setItem(sessionResumeStorageKey(sessionId), JSON.stringify(data));
}

function buildCacheFromPending(p: PendingInterviewStart): SessionResumeCache {
  const rid = p.resume_id;
  const resumeId = typeof rid === 'number' && Number.isFinite(rid) ? rid : undefined;
  const resumeText =
    typeof p.resume === 'string' && p.resume.trim() ? p.resume.trim() : undefined;
  const displayName = String(p.position || '').trim() || '本场简历';
  return { resumeId, resumeText, displayName };
}

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const { isMobile } = useViewport();

const jobName = computed(() => (route.query.jobName as string) || '');
const pageInterviewTopic = computed(() => `${jobName.value || '未设置岗位'}`);
/** 会话 ID：路由 query 与「pending 创建后立即回填」合并，避免仅有 pending 时 query 仍为空导致发语音/文字静默 return、网络里看不到请求 */
const effectiveSessionId = ref(String(route.query.sessionId || ''));
watch(
  () => route.query.sessionId,
  (q) => {
    if (q != null && String(q).trim()) effectiveSessionId.value = String(q).trim();
  }
);

watch(
  () => [String(route.name || ''), String(route.query.jobName || '').trim()] as const,
  ([n, job]) => {
    if (n !== 'InterviewSession' && n !== 'InterviewSessionText') return;
    document.title = job || '面试';
  },
  { immediate: true }
);
const userAvatar = computed(() => {
  const raw = String(userStore.userInfo?.avatarUrl || '').trim();
  if (!raw) return '';
  if (raw.startsWith('http') || raw.startsWith('/img/')) return raw;
  return `${apiOrigin}${raw}`;
});
const aiAvatarSrc = computed(() => '/img/mentor-a.png');
const hasPendingStart = ref(false);

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  tone?: 'error';
  kind?: 'text' | 'voice';
  transcript?: string;
  voiceDurationSec?: number;
};

const messages = ref<ChatMessage[]>([]);
const userInput = ref('');
const streaming = ref(false);
const streamingText = ref('');
/** 开场 NDJSON 是否已下发 question_chunk（避免最终 question 再整段口播/逐字动画重复） */
const hadQuestionStreamChunks = ref(false);
const chatPanelRef = ref<HTMLElement | null>(null);
const showChatScrollToBottomFab = ref(false);
/** 距底部小于该像素视为「在底部」，隐藏回到底部按钮 */
const CHAT_SCROLL_BOTTOM_EPS_PX = 80;

function isChatPanelNearBottom(el: HTMLElement): boolean {
  return el.scrollTop + el.clientHeight >= el.scrollHeight - CHAT_SCROLL_BOTTOM_EPS_PX;
}

function onChatPanelScroll() {
  const el = chatPanelRef.value;
  if (!el) {
    showChatScrollToBottomFab.value = false;
    return;
  }
  if (el.scrollHeight <= el.clientHeight + 2) {
    showChatScrollToBottomFab.value = false;
    return;
  }
  showChatScrollToBottomFab.value = !isChatPanelNearBottom(el);
}

function onClickScrollChatToBottom() {
  const el = chatPanelRef.value;
  if (!el) return;
  el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
}

watchEffect((onCleanup) => {
  const el = chatPanelRef.value;
  if (!el) return;
  const ro = new ResizeObserver(() => onChatPanelScroll());
  ro.observe(el);
  onChatPanelScroll();
  onCleanup(() => ro.disconnect());
});

const showThinkingHint = computed(() => streaming.value && !streamingText.value);

/** 文本面试左侧流程（虚拟人模式不展示） */
type InterviewFlowNode = {
  id: string;
  side: 'ai' | 'user';
  title: string;
  status: 'thinking' | 'done';
  messageIndex: number | null;
  /** 悬浮气泡用元信息（不含完整题干） */
  flowRound?: number;
  flowTopic?: string;
  flowAt?: string;
  flowDepthScore?: number;
};

type FlowMetaInput = {
  flowRound?: number | null;
  flowTopic?: string;
  flowAt?: string;
  flowDepthScore?: number | null;
};

const flowNodes = ref<InterviewFlowNode[]>([]);
const flowActiveThinkingId = ref<string | null>(null);
/** 最近一次题目轮次，用于用户作答节点关联 */
const lastStreamQuestionRound = ref<number | null>(null);
let flowIdSeq = 0;

function flowEnabled() {
  return true;
}

function truncateFlowTitle(s: string, n = 22): string {
  const t = String(s || '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!t) return '…';
  return t.length <= n ? t : `${t.slice(0, n - 1)}…`;
}

function metaFields(meta?: FlowMetaInput): Partial<InterviewFlowNode> {
  if (!meta) return {};
  const o: Partial<InterviewFlowNode> = {};
  if (meta.flowRound != null && meta.flowRound > 0) o.flowRound = meta.flowRound;
  const tp = meta.flowTopic?.replace(/\n/g, ' ').trim();
  if (tp) o.flowTopic = tp.length > 100 ? `${tp.slice(0, 99)}…` : tp;
  if (meta.flowAt?.trim()) o.flowAt = meta.flowAt.trim();
  if (meta.flowDepthScore != null && Number.isFinite(Number(meta.flowDepthScore))) {
    o.flowDepthScore = Number(meta.flowDepthScore);
  }
  return o;
}

function patchFlowMeta(node: InterviewFlowNode, meta?: FlowMetaInput) {
  Object.assign(node, metaFields(meta));
}

/** 从历史消息摘一行的短主题（非全文） */
function shortTopicFromQuestionContent(content: string): string | undefined {
  const oneLine = String(content || '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(/[。\n]/)[0]
    ?.trim();
  if (!oneLine) return undefined;
  return oneLine.length > 72 ? `${oneLine.slice(0, 71)}…` : oneLine;
}

function formatFlowTooltipTime(iso?: string): string | undefined {
  if (!iso?.trim()) return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toLocaleString('zh-CN', { hour12: false });
}

function flowNodeTooltipLines(node: InterviewFlowNode): string[] {
  const lines: string[] = [];
  if (node.flowRound != null && node.flowRound > 0) {
    lines.push(`轮次：第 ${node.flowRound} 轮`);
  }
  const topic = node.flowTopic?.trim();
  if (topic) {
    lines.push(`主题：${topic}`);
  }
  const timeStr = formatFlowTooltipTime(node.flowAt);
  if (timeStr) lines.push(`时间：${timeStr}`);
  if (node.flowDepthScore != null && Number.isFinite(node.flowDepthScore)) {
    lines.push(`深度得分：${node.flowDepthScore}`);
  }
  if (!lines.length && node.status === 'thinking') {
    lines.push('面试官处理中…');
  } else if (!lines.length && node.messageIndex != null) {
    lines.push('点击可定位到聊天记录');
  }
  return lines;
}

function flowStartAiThinking(label: string, meta?: FlowMetaInput) {
  if (!flowEnabled()) return;
  if (interviewEnded.value) return;
  const text = truncateFlowTitle(label, 24);
  const id = flowActiveThinkingId.value;
  if (id) {
    const node = flowNodes.value.find((x) => x.id === id);
    if (node) {
      node.title = text;
      patchFlowMeta(node, meta);
      return;
    }
  }
  const newId = `f-${flowIdSeq++}`;
  flowActiveThinkingId.value = newId;
  flowNodes.value.push({
    id: newId,
    side: 'ai',
    title: text,
    status: 'thinking',
    messageIndex: null,
    ...metaFields(meta),
  });
}

function flowFinishThinkingOnly() {
  const id = flowActiveThinkingId.value;
  if (!id) return;
  const node = flowNodes.value.find((x) => x.id === id);
  if (node) node.status = 'done';
  flowActiveThinkingId.value = null;
}

/** 将当前「思考中」节点标为完成并绑定标题与消息锚点；若无思考节点则追加一条 */
function flowSettleAiThinking(title: string, messageIndex: number | null, meta?: FlowMetaInput) {
  if (!flowEnabled()) return;
  const short = truncateFlowTitle(title, 22);
  const id = flowActiveThinkingId.value;
  if (id) {
    const node = flowNodes.value.find((x) => x.id === id);
    if (node) {
      node.title = short;
      node.status = 'done';
      node.messageIndex = messageIndex;
      patchFlowMeta(node, meta);
      flowActiveThinkingId.value = null;
      return;
    }
    flowActiveThinkingId.value = null;
  }
  flowNodes.value.push({
    id: `f-${flowIdSeq++}`,
    side: 'ai',
    title: short,
    status: 'done',
    messageIndex,
    ...metaFields(meta),
  });
}

function flowPushAiDone(title: string, messageIndex: number | null, meta?: FlowMetaInput) {
  if (!flowEnabled()) return;
  flowFinishThinkingOnly();
  flowNodes.value.push({
    id: `f-${flowIdSeq++}`,
    side: 'ai',
    title: truncateFlowTitle(title, 22),
    status: 'done',
    messageIndex,
    ...metaFields(meta),
  });
}

function flowPushUserNode(title: string, messageIndex: number) {
  if (!flowEnabled()) return;
  const r = lastStreamQuestionRound.value;
  flowNodes.value.push({
    id: `f-${flowIdSeq++}`,
    side: 'user',
    title: truncateFlowTitle(title, 16),
    status: 'done',
    messageIndex,
    ...metaFields({
      flowRound: r != null && r > 0 ? r : null,
      flowAt: new Date().toISOString(),
    }),
  });
}

function rebuildFlowFromMessages() {
  if (!flowEnabled()) return;
  flowNodes.value = [];
  flowActiveThinkingId.value = null;
  flowIdSeq = 0;
  let round = 0;
  let lastQRound: number | null = null;
  const list = messages.value;
  list.forEach((m, idx) => {
    if (m.role === 'user') {
      flowNodes.value.push({
        id: `hf-${flowIdSeq++}`,
        side: 'user',
        title: m.kind === 'voice' ? '语音作答' : '我的回答',
        status: 'done',
        messageIndex: idx,
        ...metaFields({
          flowRound: lastQRound != null && lastQRound > 0 ? lastQRound : null,
        }),
      });
      return;
    }
    if (m.role === 'assistant') {
      if (m.tone === 'error') {
        flowNodes.value.push({
          id: `hf-${flowIdSeq++}`,
          side: 'ai',
          title: '系统提示',
          status: 'done',
          messageIndex: idx,
        });
        return;
      }
      round += 1;
      lastQRound = round;
      const trailing = idx === list.length - 1;
      const topicHint = shortTopicFromQuestionContent(m.content);
      flowNodes.value.push({
        id: `hf-${flowIdSeq++}`,
        side: 'ai',
        title: trailing ? '当前提问' : `第 ${round} 轮提问`,
        status: 'done',
        messageIndex: idx,
        flowRound: round,
        ...(topicHint ? { flowTopic: topicHint } : {}),
      });
    }
  });
  lastStreamQuestionRound.value = round > 0 ? round : null;
  scheduleScrollFlowCurrent();
}

function scrollToMessageIndex(idx: number | null) {
  if (idx == null || idx < 0) return;
  nextTick(() => {
    const panel = chatPanelRef.value;
    if (!panel) return;
    const el = panel.querySelector(`[data-chat-index="${idx}"]`);
    (el as HTMLElement | null)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
}

function onFlowStepActivate(node: InterviewFlowNode) {
  if (node.messageIndex != null) {
    scrollToMessageIndex(node.messageIndex);
  }
}
/** 面试已结束：展示报告分享卡片并禁用作答 */
const interviewEnded = ref(false);
const showReportInvite = ref(false);

/** 侧栏「当前焦点」：考察主题（与后端 topic / current_topic 同步） */
const sessionFocusTopic = ref('');

function mergeSessionFocusTopic(raw: unknown) {
  const s = String(raw ?? '')
    .replace(/\n/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (s) sessionFocusTopic.value = s;
}

const flowDockFocusTopicDisplay = computed(() => {
  const t = sessionFocusTopic.value.trim();
  if (!t) return '';
  return t.length > 80 ? `${t.slice(0, 79)}…` : t;
});

const flowDockFocusStatus = computed(() => {
  if (interviewEnded.value) return '面试已结束';
  if (streaming.value) {
    if (showThinkingHint.value) return '面试官思考中…';
    const st = streamingText.value.trim();
    if (st) return st.length > 40 ? `${st.slice(0, 39)}…` : st;
    return '处理中…';
  }
  const list = messages.value;
  const last = list[list.length - 1];
  if (!last) return '准备作答';
  if (last.role === 'assistant' && last.tone !== 'error') return '请作答';
  if (last.role === 'user') return '等待面试官响应…';
  return '进行中';
});

/** 流程侧栏：面试时长（起算优先服务端 created_at / 历史最早时间戳） */
const interviewEpochMs = ref<number | null>(null);
const interviewFrozenElapsedMs = ref<number | null>(null);
const interviewDurationDisplay = ref('00:00');
let interviewDurationTimer: ReturnType<typeof setInterval> | null = null;

function pickInterviewStartMs(info: InterviewSessionInfo): number | null {
  for (const key of ['started_at', 'created_at'] as const) {
    const s = info[key];
    if (typeof s === 'string' && s.trim()) {
      const t = Date.parse(s);
      if (!Number.isNaN(t)) return t;
    }
  }
  for (const h of info.history || []) {
    if (h.timestamp?.trim()) {
      const t = Date.parse(h.timestamp);
      if (!Number.isNaN(t)) return t;
    }
  }
  return null;
}

function pickLatestHistoryTimestampMs(info: InterviewSessionInfo): number | null {
  let last: number | null = null;
  for (const h of info.history || []) {
    if (!h.timestamp?.trim()) continue;
    const t = Date.parse(h.timestamp);
    if (!Number.isNaN(t)) last = t;
  }
  return last;
}

function formatInterviewDuration(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function tickInterviewDuration() {
  const start = interviewEpochMs.value;
  if (start == null) {
    interviewDurationDisplay.value = '—';
    return;
  }
  const frozen = interviewFrozenElapsedMs.value;
  const ms = frozen != null ? frozen : Date.now() - start;
  interviewDurationDisplay.value = formatInterviewDuration(ms);
}

function stopInterviewDurationTimer() {
  if (interviewDurationTimer != null) {
    clearInterval(interviewDurationTimer);
    interviewDurationTimer = null;
  }
}

function startInterviewDurationTimer() {
  stopInterviewDurationTimer();
  tickInterviewDuration();
  interviewDurationTimer = window.setInterval(tickInterviewDuration, 1000);
}

function resumeInterviewDurationFromSession(info: InterviewSessionInfo) {
  stopInterviewDurationTimer();
  interviewFrozenElapsedMs.value = null;
  const startMs = pickInterviewStartMs(info) ?? Date.now();
  interviewEpochMs.value = startMs;

  if (info.status === 'ended') {
    const endMs = pickLatestHistoryTimestampMs(info);
    if (endMs != null && endMs >= startMs) {
      interviewFrozenElapsedMs.value = endMs - startMs;
    } else {
      interviewFrozenElapsedMs.value = Date.now() - startMs;
    }
    tickInterviewDuration();
    return;
  }

  if (interviewEnded.value) {
    interviewFrozenElapsedMs.value = Date.now() - startMs;
    tickInterviewDuration();
    return;
  }

  startInterviewDurationTimer();
}

watch(interviewEnded, (ended) => {
  if (!ended || interviewEpochMs.value == null) return;
  if (interviewFrozenElapsedMs.value != null) return;
  interviewFrozenElapsedMs.value = Date.now() - interviewEpochMs.value;
  stopInterviewDurationTimer();
  tickInterviewDuration();
});
const canRenderInterview = computed(
  () => Boolean(effectiveSessionId.value || hasPendingStart.value)
);
const showMissingSessionAlert = computed(() => !canRenderInterview.value);

/** 文本面试：页面左侧可折叠流程浮层（不在聊天卡片内）；移动端默认收起 */
const flowPanelOpen = ref(!isMobile.value);
const showFlowDock = computed(() => canRenderInterview.value);
const flowDockRef = ref<{ flowDockBodyRef: HTMLElement | null } | null>(null);

/** 文本面试：右侧「资料 · 助手」浮层（与流程侧栏形态一致）；移动端默认收起 */
const materialsPanelOpen = ref(!isMobile.value);
const showMaterialsDock = computed(() => canRenderInterview.value);

/** 桌面端：始终为左右 dock 预留宽度，避免折叠/展开导致会话区位移 */
const mainWrapDockClass = computed(() => ({
  'interview-main-wrap--reserve-left': !isMobile.value && showFlowDock.value,
  'interview-main-wrap--reserve-right': !isMobile.value && showMaterialsDock.value,
}));

const sessionResumePdfSrc = ref('');
const sessionResumePlainText = ref('');
const sessionResumeTitle = ref('');
const sessionResumeLoading = ref(false);
const sessionResumeError = ref('');
const hasSessionResume = computed(
  () => Boolean(sessionResumePdfSrc.value) || Boolean(sessionResumePlainText.value)
);

/** 侧栏 PDF 小窗：平移 + 缩放（与 session 无关，换简历或离开时重置） */
const RESUME_THUMB_SCALE_MIN = 0.45;
const RESUME_THUMB_SCALE_MAX = 2.75;
const RESUME_THUMB_ZOOM_STEP = 0.12;
const RESUME_THUMB_WHEEL_FACTOR = 0.09;

const resumeThumbScale = ref(1);
const resumeThumbPanX = ref(0);
const resumeThumbPanY = ref(0);
const resumeThumbDragging = ref(false);
let resumeThumbPointerId = -1;
let resumeThumbDragLastX = 0;
let resumeThumbDragLastY = 0;

const resumeThumbZoomPercent = computed(() => Math.round(resumeThumbScale.value * 100));

function resumeThumbPanZoomReset() {
  resumeThumbScale.value = 1;
  resumeThumbPanX.value = 0;
  resumeThumbPanY.value = 0;
}

function resumeThumbZoomIn() {
  resumeThumbScale.value = Math.min(
    RESUME_THUMB_SCALE_MAX,
    Math.round((resumeThumbScale.value + RESUME_THUMB_ZOOM_STEP) * 100) / 100
  );
}

function resumeThumbZoomOut() {
  resumeThumbScale.value = Math.max(
    RESUME_THUMB_SCALE_MIN,
    Math.round((resumeThumbScale.value - RESUME_THUMB_ZOOM_STEP) * 100) / 100
  );
}

function onResumeThumbWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? -RESUME_THUMB_WHEEL_FACTOR : RESUME_THUMB_WHEEL_FACTOR;
  const next = Math.min(
    RESUME_THUMB_SCALE_MAX,
    Math.max(RESUME_THUMB_SCALE_MIN, resumeThumbScale.value + delta)
  );
  resumeThumbScale.value = Math.round(next * 100) / 100;
}

function onResumeThumbPointerDown(e: PointerEvent) {
  if (e.button !== 0) return;
  const el = e.currentTarget as HTMLElement;
  resumeThumbDragging.value = true;
  resumeThumbPointerId = e.pointerId;
  resumeThumbDragLastX = e.clientX;
  resumeThumbDragLastY = e.clientY;
  try {
    el.setPointerCapture(e.pointerId);
  } catch {
    /* ignore */
  }
}

function onResumeThumbPointerMove(e: PointerEvent) {
  if (!resumeThumbDragging.value || e.pointerId !== resumeThumbPointerId) return;
  const dx = e.clientX - resumeThumbDragLastX;
  const dy = e.clientY - resumeThumbDragLastY;
  resumeThumbPanX.value += dx;
  resumeThumbPanY.value += dy;
  resumeThumbDragLastX = e.clientX;
  resumeThumbDragLastY = e.clientY;
}

function onResumeThumbPointerUp(e: PointerEvent) {
  if (e.pointerId !== resumeThumbPointerId) return;
  resumeThumbDragging.value = false;
  resumeThumbPointerId = -1;
  const el = e.currentTarget as HTMLElement;
  try {
    el.releasePointerCapture(e.pointerId);
  } catch {
    /* ignore */
  }
}

watch(sessionResumePdfSrc, () => {
  resumeThumbPanZoomReset();
});

/** 本场 PDF 简历内存缓存（object URL），离开面试页时释放 */
let sessionResumePdfObjectUrl: string | null = null;

function revokeSessionResumePdfBlob() {
  if (sessionResumePdfObjectUrl) {
    URL.revokeObjectURL(sessionResumePdfObjectUrl);
    sessionResumePdfObjectUrl = null;
  }
}

/**
 * 拉取 PDF 一次并缓存在本地 Blob URL，侧栏与放大弹窗共用，避免重复请求。
 * 若 fetch 失败（如跨域无 CORS），回退为直链由浏览器自行缓存。
 */
async function loadSessionPdfIntoLocalCache(remoteUrl: string): Promise<void> {
  sessionResumeError.value = '';
  try {
    const res = await fetch(remoteUrl, { credentials: 'omit', mode: 'cors' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    revokeSessionResumePdfBlob();
    sessionResumePdfObjectUrl = URL.createObjectURL(blob);
    sessionResumePdfSrc.value = sessionResumePdfObjectUrl;
  } catch {
    sessionResumePdfSrc.value = remoteUrl;
  }
}

/** 与 sessionStorage 条目无关，仅标识「同一份简历内容」，用于跳过重复拉取 */
const resumeLoadFingerprint = ref('');

function resumeCacheFingerprint(c: SessionResumeCache): string {
  const t = c.resumeText;
  if (typeof t === 'string' && t.trim()) {
    return `text:${t.length}:${t.slice(0, 240)}`;
  }
  if (c.resumeId != null && Number.isFinite(c.resumeId)) {
    return `id:${c.resumeId}`;
  }
  return '';
}

/** 释放 PDF Blob URL 与内存中的简历展示状态（离开面试页或切换会话时调用） */
function disposeInterviewResumeLocalCache() {
  resumeLoadFingerprint.value = '';
  revokeSessionResumePdfBlob();
  sessionResumePdfSrc.value = '';
  sessionResumePlainText.value = '';
  resumeThumbPanZoomReset();
}

/**
 * 根据缓存元数据加载简历（PDF / 纯文本）。简历 id 与正文均来自面试启动前的 pending 载荷，不依赖会话接口或首题。
 */
async function loadResumeFromSessionCacheEntry(cached: SessionResumeCache) {
  const fp = resumeCacheFingerprint(cached);
  if (
    fp &&
    resumeLoadFingerprint.value === fp &&
    (sessionResumePdfSrc.value || sessionResumePlainText.value)
  ) {
    return;
  }

  revokeSessionResumePdfBlob();
  sessionResumePdfSrc.value = '';
  sessionResumePlainText.value = '';
  sessionResumeTitle.value = cached.displayName || '本场简历';
  sessionResumeError.value = '';
  resumeLoadFingerprint.value = '';

  if (typeof cached.resumeText === 'string' && cached.resumeText.trim()) {
    sessionResumePlainText.value = cached.resumeText;
    resumeLoadFingerprint.value = fp;
    return;
  }

  if (cached.resumeId == null) return;

  const uid = userStore.userInfo?.id;
  if (uid == null || uid === '') {
    sessionResumeError.value = '请登录后查看已选简历文件';
    return;
  }

  sessionResumeLoading.value = true;
  try {
    const item = await getResumeItemApi(cached.resumeId);
    const fileKey = String(item?.unique_filename || item?.filename || '').trim();
    if (!fileKey) {
      sessionResumeError.value = '未获取到简历文件名，无法预览';
      return;
    }
    const remoteUrl = `${RESUME_FILE_PUBLIC_BASE_URL}${encodeURIComponent(fileKey)}`;
    await loadSessionPdfIntoLocalCache(remoteUrl);
    if (item?.filename) sessionResumeTitle.value = String(item.filename);
    resumeLoadFingerprint.value = fp;
  } catch (e: unknown) {
    sessionResumeError.value = (e as Error).message || '加载简历失败';
  } finally {
    sessionResumeLoading.value = false;
  }
}

async function hydrateSessionResume(sessionId: string) {
  const sid = String(sessionId || '').trim();
  // 无 sessionId 时不清空界面：新建会话流程中可能已通过 pending 预加载简历
  if (!sid) return;

  const cached = readSessionResumeCache(sid);
  if (!cached) return;

  await loadResumeFromSessionCacheEntry(cached);
}

watch(
  effectiveSessionId,
  (id) => {
    void hydrateSessionResume(String(id || '').trim());
  },
  { immediate: true }
);

function scrollFlowCurrentIntoView(behavior: ScrollBehavior = 'smooth') {
  const root = flowDockRef.value?.flowDockBodyRef ?? null;
  if (!root || !showFlowDock.value || !flowPanelOpen.value) return;
  const targetId = flowActiveThinkingId.value ?? flowNodes.value[flowNodes.value.length - 1]?.id;
  if (!targetId) return;
  const el = root.querySelector(`[data-flow-node-id="${targetId}"]`) as HTMLElement | null;
  el?.scrollIntoView({ block: 'center', inline: 'nearest', behavior });
}

function scheduleScrollFlowCurrent() {
  if (!showFlowDock.value || !flowPanelOpen.value) return;
  nextTick(() => {
    requestAnimationFrame(() => scrollFlowCurrentIntoView());
  });
}

watch(
  () => [
    flowNodes.value.length,
    flowNodes.value[flowNodes.value.length - 1]?.id ?? '',
    flowActiveThinkingId.value ?? '',
    streaming.value,
    messages.value.length,
  ],
  () => scheduleScrollFlowCurrent()
);

watch(isMobile, (mobile) => {
  if (mobile) {
    flowPanelOpen.value = false;
    materialsPanelOpen.value = false;
  } else {
    flowPanelOpen.value = true;
    materialsPanelOpen.value = true;
  }
});

watch(flowPanelOpen, (open) => {
  if (open && isMobile.value && showMaterialsDock.value) {
    materialsPanelOpen.value = false;
  }
  if (open) scheduleScrollFlowCurrent();
});

watch(materialsPanelOpen, (open) => {
  if (open && isMobile.value && showFlowDock.value) {
    flowPanelOpen.value = false;
  }
});

const isRecording = ref(false);
const waveformBars = ref<number[]>(Array.from({ length: 24 }, () => 0));
let recordStream: MediaStream | null = null;
let recordStartedAt = 0;
let audioContext: AudioContext | null = null;
let audioAnalyser: AnalyserNode | null = null;
let audioSourceNode: MediaStreamAudioSourceNode | null = null;
let meterRafId: number | null = null;
let pcmRecordContext: AudioContext | null = null;
let pcmRecordSource: MediaStreamAudioSourceNode | null = null;
let pcmRecordProcessor: ScriptProcessorNode | null = null;
let pcmSampleRate = 16000;
let pcmChunks: Float32Array[] = [];

function stopPcmRecorder() {
  try {
    pcmRecordSource?.disconnect();
  } catch {
    /* ignore */
  }
  try {
    pcmRecordProcessor?.disconnect();
  } catch {
    /* ignore */
  }
  pcmRecordSource = null;
  pcmRecordProcessor = null;
  if (pcmRecordContext && pcmRecordContext.state !== 'closed') {
    void pcmRecordContext.close().catch(() => {});
  }
  pcmRecordContext = null;
}

async function startPcmRecorder(stream: MediaStream) {
  stopPcmRecorder();
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  pcmRecordContext = new AC();
  await pcmRecordContext.resume();
  pcmSampleRate = pcmRecordContext.sampleRate || 48000;
  pcmChunks = [];
  pcmRecordSource = pcmRecordContext.createMediaStreamSource(stream);
  pcmRecordProcessor = pcmRecordContext.createScriptProcessor(4096, 1, 1);
  pcmRecordProcessor.onaudioprocess = (evt: AudioProcessingEvent) => {
    if (!isRecording.value) return;
    const input = evt.inputBuffer.getChannelData(0);
    pcmChunks.push(new Float32Array(input));
  };
  pcmRecordSource.connect(pcmRecordProcessor);
  pcmRecordProcessor.connect(pcmRecordContext.destination);
}

function downsampleTo16k(input: Float32Array, sourceRate: number): Int16Array {
  if (!input.length) return new Int16Array(0);
  if (sourceRate <= 16000) {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i] ?? 0));
      out[i] = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
    }
    return out;
  }
  const ratio = sourceRate / 16000;
  const outLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Int16Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    const srcIdx = Math.min(input.length - 1, Math.floor(i * ratio));
    const s = Math.max(-1, Math.min(1, input[srcIdx] ?? 0));
    out[i] = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
  }
  return out;
}

function encodeWavFromPcm16(pcm16: Int16Array, sampleRate: number): Blob {
  const bytesPerSample = 2;
  const dataSize = pcm16.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i += 1) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true); // PCM fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true); // byteRate
  view.setUint16(32, bytesPerSample, true); // blockAlign
  view.setUint16(34, 16, true); // bitDepth
  writeStr(36, 'data');
  view.setUint32(40, dataSize, true);
  let offset = 44;
  for (let i = 0; i < pcm16.length; i += 1) {
    view.setInt16(offset, pcm16[i] ?? 0, true);
    offset += 2;
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

function stopAudioMeter() {
  if (meterRafId != null) {
    cancelAnimationFrame(meterRafId);
    meterRafId = null;
  }
  try {
    audioSourceNode?.disconnect();
  } catch {
    /* ignore */
  }
  audioSourceNode = null;
  try {
    audioAnalyser?.disconnect();
  } catch {
    /* ignore */
  }
  audioAnalyser = null;
  if (audioContext && audioContext.state !== 'closed') {
    void audioContext.close();
  }
  audioContext = null;
  waveformBars.value = Array.from({ length: 24 }, () => 0);
}

function startAudioMeter(stream: MediaStream) {
  stopAudioMeter();
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  audioContext = new AC();
  void audioContext.resume();
  audioAnalyser = audioContext.createAnalyser();
  audioAnalyser.fftSize = 256;
  audioAnalyser.smoothingTimeConstant = 0.72;
  audioAnalyser.minDecibels = -85;
  audioAnalyser.maxDecibels = -10;
  audioSourceNode = audioContext.createMediaStreamSource(stream);
  audioSourceNode.connect(audioAnalyser);

  const bufferLength = audioAnalyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  const tick = () => {
    if (!audioAnalyser) return;
    audioAnalyser.getByteFrequencyData(dataArray);
    const bars = waveformBars.value.length;
    const step = Math.max(1, Math.floor(bufferLength / bars));
    const next: number[] = [];
    for (let b = 0; b < bars; b++) {
      let sum = 0;
      const start = b * step;
      const end = Math.min(start + step, bufferLength);
      for (let i = start; i < end; i++) sum += dataArray[i] ?? 0;
      next.push(sum / (end - start) / 255);
    }
    waveformBars.value = next;
    meterRafId = requestAnimationFrame(tick);
  };
  meterRafId = requestAnimationFrame(tick);
}

onBeforeUnmount(() => {
  stopPcmRecorder();
  pcmChunks = [];
  isRecording.value = false;
  stopMicTracks();
  stopInterviewDurationTimer();
});

function stopMicTracks() {
  stopPcmRecorder();
  stopAudioMeter();
  recordStream?.getTracks().forEach((t) => t.stop());
  recordStream = null;
}

async function renderStreamingText(text: string) {
  const full = String(text || '');
  streamingText.value = '';
  if (!full) return;
  for (let i = 0; i < full.length; i += 1) {
    if (interviewEnded.value) break;
    streamingText.value += full.slice(i, i + 1);
    // 稍慢一点的逐字显示，提升阅读感知
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 15));
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatPanelRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

watch(
  () => messages.value.length,
  () => scrollToBottom()
);

function backToSettings() {
  disposeInterviewResumeLocalCache();
  router.push({ name: 'Home' });
}

function goEvaluationReport() {
  const sid = effectiveSessionId.value;
  if (!sid) return;
  router.push({
    name: 'InterviewEvaluation',
    params: { sessionId: sid },
    query: { jobName: jobName.value || undefined },
  });
}

async function refreshSessionEndedState() {
  const sid = effectiveSessionId.value;
  if (!sid) return;
  try {
    const info = await getInterviewSessionApi(sid);
    if (info.status === 'ended') {
      interviewEnded.value = true;
      showReportInvite.value = true;
    }
  } catch {
    /* 会话已删或网络错误时忽略 */
  }
}
async function createInterviewSessionFromPending(payload: PendingInterviewStart): Promise<string | null> {
  try {
    const startBody: StartInterviewBody = {
      resume: typeof payload.resume === 'string' ? payload.resume : undefined,
      resume_id: typeof payload.resume_id === 'number' ? payload.resume_id : undefined,
      position: String(payload.position || ''),
      collection_name: String(payload.collection_name || ''),
      user_id: payload.user_id,
      difficulty: payload.difficulty,
      interview_mode: payload.interview_mode || 'text',
    };
    const started = await startInterviewApi(startBody);
    const sid = String(started.session_id || '').trim();
    if (!sid) return null;
    writeSessionResumeCache(sid, buildCacheFromPending(payload));
    effectiveSessionId.value = sid;
    sessionStorage.removeItem('pendingInterviewStart');
    hasPendingStart.value = false;
    await router.replace({
      query: {
        ...route.query,
        sessionId: sid,
        jobName: payload.position,
        interviewMode: payload.interview_mode || route.query.interviewMode || 'text',
      },
    });
    return sid;
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '创建面试会话失败');
    return null;
  }
}

function formatVoiceDuration(sec?: number): string {
  const s = Math.max(1, Number.isFinite(sec as number) ? Math.round(sec as number) : 1);
  return `${s}"`;
}

function createVoicePlaceholderMessage(voiceDurationSec?: number): ChatMessage {
  return { role: 'user', content: '语音消息', kind: 'voice', voiceDurationSec };
}

function pickTranscriptText(data: Record<string, unknown>): string {
  const candidates = [
    data.transcript,
    data.transcription,
    data.asr_text,
    data.asr,
    data.text,
    data.recognized_text,
    data.recognition,
    data.stt,
  ];
  for (const item of candidates) {
    if (typeof item === 'string' && item.trim()) return item.trim();
  }
  return '';
}

function updateVoiceTranscriptAt(index: number | null, transcript: string) {
  if (index == null || !transcript) return;
  const msg = messages.value[index];
  if (!msg || msg.role !== 'user' || msg.kind !== 'voice') return;
  msg.transcript = transcript;
}


onMounted(async () => {
  hasPendingStart.value = !!sessionStorage.getItem('pendingInterviewStart');
  let sid = effectiveSessionId.value;
  if (!sid) {
    const pending = sessionStorage.getItem('pendingInterviewStart');
    if (!pending) return;
    let payload: PendingInterviewStart;
    try {
      payload = JSON.parse(pending) as PendingInterviewStart;
    } catch {
      return;
    }
    // 简历 id/正文均在 pending 里，与 startInterview / 首题无关，提前加载侧栏预览
    void loadResumeFromSessionCacheEntry(buildCacheFromPending(payload));
    const createdSid = await createInterviewSessionFromPending(payload);
    if (!createdSid) {
      disposeInterviewResumeLocalCache();
      return;
    }
    sid = createdSid;
  }

  let loadedSessionInfo: InterviewSessionInfo | null = null;

  try {
    const loadSession = async (): Promise<InterviewSessionInfo> => {
      const info = await getInterviewSessionApi(sid);
      loadedSessionInfo = info;
      mergeSessionFocusTopic(info.current_topic);
      const hist = info.history || [];
      if (!sessionFocusTopic.value.trim() && hist.length) {
        mergeSessionFocusTopic(hist[hist.length - 1]?.topic);
      }
      if (hist.length > 0) {
        hist.forEach((h) => {
          messages.value.push({ role: 'assistant', content: h.question, kind: 'text' });
          messages.value.push({ role: 'user', content: h.answer, kind: 'text' });
        });
        if (info.current_question) {
          messages.value.push({ role: 'assistant', content: info.current_question, kind: 'text' });
        }
      } else if (info.current_question) {
        messages.value.push({ role: 'assistant', content: info.current_question, kind: 'text' });
      }
      rebuildFlowFromMessages();
      return info;
    };

    await loadSession();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '恢复会话失败');
  }

  await refreshSessionEndedState();
  resumeInterviewDurationFromSession(
    loadedSessionInfo ?? {
      session_id: sid,
      status: interviewEnded.value ? 'ended' : 'questioning',
      total_rounds: 0,
      current_topic: '',
      current_question: '',
      history: [],
    }
  );
});

onBeforeUnmount(() => {
  disposeInterviewResumeLocalCache();
});

function attachAnswerStreamHandler(voiceMessageIndex: number | null = null) {
  let uiChain: Promise<void> = Promise.resolve();
  const onEvent = (evt: InterviewAnswerStreamEvent) => {
    updateVoiceTranscriptAt(voiceMessageIndex, pickTranscriptText(evt.data));

    if (evt.type === 'interview_complete') {
      if (!interviewEnded.value) {
        interviewEnded.value = true;
        showReportInvite.value = true;
        streaming.value = false;
        streamingText.value = '';
        const hint = String(evt.data.message || '').trim() || '面试已结束，可查看评估报告。';
        messages.value.push({ role: 'assistant', content: hint, kind: 'text' });
        flowSettleAiThinking('面试结束', messages.value.length - 1, {
          flowAt: evt.timestamp,
          flowRound: lastStreamQuestionRound.value ?? null,
        });
        scrollToBottom();
      }
      return;
    }

    if (interviewEnded.value) {
      return;
    }

    if (evt.type === 'voice_processing' || evt.type === 'analyzing') {
      const hint = String(evt.data.message || '').trim();
      if (hint) streamingText.value = hint;
      flowStartAiThinking(hint || (evt.type === 'voice_processing' ? '语音处理中…' : '分析中…'), {
        flowAt: evt.timestamp,
      });
    } else if (evt.type === 'checking_completeness') {
      const hint = String(evt.data.message || '').trim();
      if (hint) streamingText.value = hint;
      flowStartAiThinking(hint || '检查完整性…', { flowAt: evt.timestamp });
    } else if (evt.type === 'analysis_result') {
      const feedback = String(evt.data.feedback || '').trim();
      const depthRaw = Number(evt.data.depth_score);
      const analysisDepth = Number.isFinite(depthRaw) ? depthRaw : null;
      const analysisTs = evt.timestamp;
      if (feedback) {
        uiChain = uiChain.then(async () => {
          if (interviewEnded.value) return;
          await renderStreamingText(feedback);
          if (interviewEnded.value) return;
          messages.value.push({ role: 'assistant', content: feedback });
          const idx = messages.value.length - 1;
          flowSettleAiThinking('评价反馈', idx, {
            flowAt: analysisTs,
            flowDepthScore: analysisDepth,
            flowRound: lastStreamQuestionRound.value ?? null,
          });
          streamingText.value = '';
          scrollToBottom();
        });
      } else {
        flowSettleAiThinking('评价反馈', null, {
          flowAt: analysisTs,
          flowDepthScore: analysisDepth,
          flowRound: lastStreamQuestionRound.value ?? null,
        });
      }
    } else if (evt.type === 'completeness_result') {
      const ok = Boolean(evt.data.is_sufficient);
      flowSettleAiThinking(ok ? '完整性通过' : '待补充要点', null, {
        flowAt: evt.timestamp,
        flowRound: lastStreamQuestionRound.value ?? null,
      });
    } else if (evt.type === 'topic_completed') {
      const topic = String(evt.data.topic || '')
        .replace(/\n/g, ' ')
        .trim();
      mergeSessionFocusTopic(topic);
      const reason = String(evt.data.reason || '').trim();
      const tail = topic ? ` · ${truncateFlowTitle(topic, 14)}` : '';
      const reasonPart = reason ? ` · ${truncateFlowTitle(reason, 12)}` : '';
      const topicLine = [topic, reason].filter(Boolean).join(' · ');
      flowPushAiDone(`话题完成${tail}${reasonPart}`, null, {
        flowAt: evt.timestamp,
        flowTopic: topicLine || undefined,
        flowRound: lastStreamQuestionRound.value ?? null,
      });
    } else if (evt.type === 'question_chunk') {
      const ch = String(evt.data.chunk ?? '');
      if (!ch || interviewEnded.value) return;
      hadQuestionStreamChunks.value = true;
      streamingText.value += ch;
      scrollToBottom();
    } else if (evt.type === 'followup') {
      const topicLine = String(evt.data.topic || '')
        .replace(/\s+/g, ' ')
        .trim();
      mergeSessionFocusTopic(topicLine);
      const msg = String(evt.data.message || '').trim();
      if (msg) {
        uiChain = uiChain.then(async () => {
          if (interviewEnded.value) return;
          await renderStreamingText(msg);
          if (interviewEnded.value) return;
          messages.value.push({ role: 'assistant', content: msg });
          const idx = messages.value.length - 1;
          const r = Number(evt.data.round);
          const rl = Number.isFinite(r) && r > 0 ? r : lastStreamQuestionRound.value;
          if (rl != null && rl > 0) lastStreamQuestionRound.value = rl;
          flowSettleAiThinking('追问', idx, {
            flowAt: evt.timestamp,
            flowRound: rl ?? null,
            flowTopic: topicLine || shortTopicFromQuestionContent(msg) || undefined,
          });
          streamingText.value = '';
          scrollToBottom();
        });
      }
    } else if (evt.type === 'question') {
      const topicLine = String(evt.data.topic || '')
        .replace(/\s+/g, ' ')
        .trim();
      mergeSessionFocusTopic(topicLine);
      const msg = String(evt.data.answer || evt.data.question || '').trim();
      const round = Number(evt.data.round);
      const roundLabel = Number.isFinite(round) && round > 0 ? round : null;
      const isFollowup = Boolean(evt.data.is_followup);
      const qTitle = isFollowup ? '追问' : roundLabel != null ? `第 ${roundLabel} 轮提问` : '提问';
      if (roundLabel != null) lastStreamQuestionRound.value = roundLabel;
      if (msg) {
        const chunkMode = hadQuestionStreamChunks.value;
        hadQuestionStreamChunks.value = false;
        uiChain = uiChain.then(async () => {
          if (interviewEnded.value) return;
          if (!chunkMode) {
            await renderStreamingText(msg);
          }
          if (interviewEnded.value) return;
          messages.value.push({ role: 'assistant', content: msg });
          const idx = messages.value.length - 1;
          flowSettleAiThinking(qTitle, idx, {
            flowAt: evt.timestamp,
            flowRound: roundLabel ?? lastStreamQuestionRound.value ?? null,
            flowTopic: topicLine || shortTopicFromQuestionContent(msg) || undefined,
          });
          streamingText.value = '';
          scrollToBottom();
        });
      }
    } else if (evt.type === 'error') {
      const msg = String(evt.data.message || '').trim() || '处理失败';
      streamingText.value = '';
      messages.value.push({ role: 'assistant', content: msg, tone: 'error' });
      flowSettleAiThinking('处理失败', messages.value.length - 1, { flowAt: evt.timestamp });
      ElMessage.error(msg);
      scrollToBottom();
    }
    scrollToBottom();
  };
  return { onEvent, drain: () => uiChain };
}

async function sendMessage() {
  const sid = effectiveSessionId.value;
  if (!sid) {
    ElMessage.warning('会话尚未就绪，请稍候再试');
    return;
  }
  if (interviewEnded.value) return;
  const text = userInput.value.trim();
  if (!text || streaming.value) return;
  if (text.length > INTERVIEW_ANSWER_MAX_LEN) {
    ElMessage.warning(`回答请勿超过 ${INTERVIEW_ANSWER_MAX_LEN} 字`);
    return;
  }

  messages.value.push({ role: 'user', content: text, kind: 'text' });
  flowPushUserNode('文字作答', messages.value.length - 1);
  userInput.value = '';
  streaming.value = true;
  streamingText.value = '';

  try {
    const { onEvent, drain } = attachAnswerStreamHandler();
    await streamInterviewAnswer(sid, text, onEvent);
    await drain();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '发送失败');
  } finally {
    streaming.value = false;
    streamingText.value = '';
    await refreshSessionEndedState();
    scrollToBottom();
  }
}

async function sendVoiceFile(file: File, voiceDurationSec?: number) {
  const sid = effectiveSessionId.value;
  if (!sid) {
    ElMessage.warning('会话尚未就绪，无法发送语音');
    return;
  }
  if (interviewEnded.value) return;
  if (streaming.value) return;

  messages.value.push(createVoicePlaceholderMessage(voiceDurationSec));
  const voiceMsgIndex = messages.value.length - 1;
  flowPushUserNode('语音作答', voiceMsgIndex);
  streaming.value = true;
  streamingText.value = '';

  try {
    const { onEvent, drain } = attachAnswerStreamHandler(voiceMsgIndex);
    await streamInterviewVoiceAnswer(sid, file, onEvent);
    await drain();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '语音上传失败');
  } finally {
    streaming.value = false;
    streamingText.value = '';
    await refreshSessionEndedState();
    scrollToBottom();
  }
}

async function startVoiceRecord() {
  if (!effectiveSessionId.value) {
    ElMessage.warning('会话尚未就绪，无法开始录音');
    return;
  }
  if (interviewEnded.value) return;
  if (streaming.value) return;
  try {
    recordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    await startPcmRecorder(recordStream);
    recordStartedAt = Date.now();
    startAudioMeter(recordStream);
    isRecording.value = true;
  } catch (e: unknown) {
    stopMicTracks();
    ElMessage.error('无法使用麦克风：' + ((e as Error).message || '请检查权限'));
  }
}

function stopVoiceRecorderOnly() {
  if (!isRecording.value) return;
  isRecording.value = false;
  void finalizeRecordingAndSendVoice();
}

async function finalizeRecordingAndSendVoice() {
  const chunks = pcmChunks;
  const sourceRate = pcmSampleRate;
  pcmChunks = [];
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const merged = new Float32Array(total);
  let cursor = 0;
  for (const c of chunks) {
    merged.set(c, cursor);
    cursor += c.length;
  }
  const pcm16 = downsampleTo16k(merged, sourceRate);
  const blob = encodeWavFromPcm16(pcm16, 16000);
  stopMicTracks();
  isRecording.value = false;
  const durationSec = Math.max(1, Math.round((Date.now() - recordStartedAt) / 1000));
  recordStartedAt = 0;

  if (!blob.size) {
    ElMessage.warning('录音过短或未采集到音频');
    return;
  }
  const file = new File([blob], 'frontend-record.wav', { type: 'audio/wav' });
  await sendVoiceFile(file, durationSec);
}

function toggleVoiceRecord() {
  if (isRecording.value) {
    stopVoiceRecorderOnly();
  } else {
    void startVoiceRecord();
  }
}

async function onLeavePage() {
  const sid = effectiveSessionId.value;
  try {
    await ElMessageBox.confirm('是否保存当前面试进度后离开？', '离开面试', {
      confirmButtonText: '保存并离开',
      cancelButtonText: '不保存并离开',
      distinguishCancelAndClose: true,
      type: 'warning',
      closeOnClickModal: false,
    });
    backToSettings();
  } catch (e) {
    // 点击“取消”分支按“不保存并离开”处理；关闭弹窗则不做操作
    if (e !== 'cancel') return;
    if (sid) {
      try {
        await endInterviewSessionApi(sid);
      } catch (_err) {
        // 删除失败不阻断离开
      }
    }
    backToSettings();
  }
}
</script>

<style scoped>
/* 根容器（流程面板为 fixed 浮层，不挤压聊天卡片） */
.interview-session-root {
  width: 100%;
  min-height: 100%;
  position: relative;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
}

/* 桌面端：与 .flow-dock-panel / .material-dock-panel 宽度 280px 对齐，会话区向内收缩 */
.interview-session-main-wrap {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  transition:
    padding-left 0.28s cubic-bezier(0.32, 0.72, 0, 1),
    padding-right 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}
@media (min-width: 769px) {
  .interview-session-main-wrap.interview-main-wrap--reserve-left {
    padding-left: 280px;
  }
  .interview-session-main-wrap.interview-main-wrap--reserve-right {
    padding-right: 280px;
  }
}

/* —— 左侧流程浮层（独立于聊天卡片） —— */
.flow-dock-backdrop {
  display: none;
}
.flow-dock-backdrop-enter-active,
.flow-dock-backdrop-leave-active {
  transition: opacity 0.26s ease;
}
.flow-dock-backdrop-enter-from,
.flow-dock-backdrop-leave-to {
  opacity: 0;
}
.flow-dock-slide-enter-active.flow-dock-panel,
.flow-dock-slide-leave-active.flow-dock-panel {
  transition:
    transform 0.28s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.22s ease;
}
.flow-dock-slide-enter-from.flow-dock-panel,
.flow-dock-slide-leave-to.flow-dock-panel {
  transform: translate(-100%, -50%);
  opacity: 0;
  pointer-events: none;
}
.flow-dock-panel {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 280px;
  height: min(86vh, calc(100vh - 24px));
  max-height: calc(100vh - 16px);
  bottom: auto;
  z-index: 2000;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  /* 与 .theme-card 一致的浅渐变 + 内高光 */
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  border: 1px solid #d1d5db;
  border-radius: 0 16px 16px 0;
  box-shadow:
    4px 0 24px rgba(0, 0, 0, 0.04),
    4px 0 32px -8px rgba(59, 130, 246, 0.1),
    4px 0 28px -12px rgba(168, 85, 247, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.flow-dock-duration-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(90deg, rgba(245, 243, 255, 0.85) 0%, rgba(239, 246, 255, 0.75) 100%);
}
.flow-dock-duration-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6b7280;
}
.flow-dock-duration-value {
  font-size: 15px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #111827;
  background: linear-gradient(90deg, #6d28d9, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.flow-dock-focus {
  flex-shrink: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.65);
}
.flow-dock-focus-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.flow-dock-focus-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9ca3af;
  flex-shrink: 0;
}
.flow-dock-focus-status {
  font-size: 11px;
  font-weight: 600;
  color: #6d28d9;
  text-align: right;
  line-height: 1.35;
  min-width: 0;
}
.flow-dock-focus-topic {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #374151;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.flow-dock-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 12px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}
.flow-dock-header-title {
  display: block;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #111827;
}
.flow-dock-header-title::after {
  content: '';
  display: block;
  width: 40px;
  height: 3px;
  margin-top: 8px;
  border-radius: 2px;
  background: linear-gradient(90deg, #a855f7, #3b82f6);
}
.flow-dock-collapse-btn {
  flex-shrink: 0;
  margin-top: -2px;
  color: #6b7280 !important;
}
.flow-dock-collapse-btn:hover {
  color: #7c3aed !important;
  background: #f5f3ff !important;
}
.flow-dock-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px 8px 14px;
  scrollbar-gutter: stable;
}
.flow-dock-tab {
  position: fixed;
  left: 0;
  top: 50%;
  z-index: 2001;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  min-height: 64px;
  padding: 6px 0;
  margin: 0;
  /* 对齐 .theme-back-btn */
  border: 1px solid #d8dbe3;
  border-left: none;
  border-radius: 0 10px 10px 0;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  color: #374151;
  line-height: 1;
  transition:
    left 0.22s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}
.flow-dock-tab:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  box-shadow: 0 6px 16px rgba(124, 58, 237, 0.12);
  transform: translateY(calc(-50% - 1px));
}
.flow-dock-tab--panel-open {
  left: 280px;
}
.flow-dock-tab-chevron {
  font-size: 16px;
  color: #7c3aed;
}
.flow-dock-tab:hover .flow-dock-tab-chevron {
  color: #6d28d9;
}

@media (max-width: 768px) {
  .flow-dock-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 1999;
    background: rgba(15, 23, 42, 0.35);
  }
  .flow-dock-panel {
    width: min(288px, 86vw);
    top: 0;
    bottom: 0;
    left: 0;
    height: auto;
    max-height: none;
    transform: none;
    border-radius: 0 12px 12px 0;
  }
  .flow-dock-tab--panel-open {
    left: min(288px, 86vw);
  }
  .flow-dock-slide-enter-from.flow-dock-panel,
  .flow-dock-slide-leave-to.flow-dock-panel {
    transform: translateX(-100%);
  }
}

/* —— 右侧资料 · 助手浮层 —— */
.material-dock-backdrop {
  display: none;
}
.material-dock-backdrop-enter-active,
.material-dock-backdrop-leave-active {
  transition: opacity 0.26s ease;
}
.material-dock-backdrop-enter-from,
.material-dock-backdrop-leave-to {
  opacity: 0;
}
.material-dock-slide-enter-active.material-dock-panel,
.material-dock-slide-leave-active.material-dock-panel {
  transition:
    transform 0.28s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.22s ease;
}
.material-dock-slide-enter-from.material-dock-panel,
.material-dock-slide-leave-to.material-dock-panel {
  transform: translate(100%, -50%);
  opacity: 0;
  pointer-events: none;
}
.material-dock-panel {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 280px;
  height: min(86vh, calc(100vh - 24px));
  max-height: calc(100vh - 16px);
  z-index: 2000;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  background: linear-gradient(215deg, #ffffff 0%, #f9fafb 100%);
  border-left: 1px solid #e5e7eb;
  border-radius: 16px 0 0 16px;
  box-shadow:
    -4px 0 24px rgba(0, 0, 0, 0.04),
    -4px 0 32px -8px rgba(59, 130, 246, 0.1),
    -4px 0 28px -12px rgba(168, 85, 247, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.material-dock-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 12px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}
.material-dock-header-title {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #111827;
}
.material-dock-header-title::after {
  content: '';
  display: block;
  width: 40px;
  height: 3px;
  margin-top: 8px;
  border-radius: 2px;
  background: linear-gradient(90deg, #3b82f6, #a855f7);
}
.material-dock-collapse-btn {
  flex-shrink: 0;
  margin-top: -2px;
  color: #6b7280 !important;
}
.material-dock-collapse-btn:hover {
  color: #2563eb !important;
  background: #eff6ff !important;
}
.material-dock-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scrollbar-gutter: stable;
}
.material-dock-section {
  flex-shrink: 0;
}
.material-dock-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.material-dock-section-title {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  color: #374151;
  letter-spacing: 0.04em;
}
.material-zoom-btn {
  flex-shrink: 0;
}
.material-dock-hint {
  font-size: 12px;
  color: #6b7280;
  padding: 8px 0;
}
.material-dock-error {
  font-size: 12px;
  color: #b91c1c;
  line-height: 1.45;
}
.material-resume-pdf-thumb {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 268px;
  max-height: 268px;
  width: 100%;
  box-sizing: border-box;
  padding: 6px 6px 8px;
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #f3f4f6;
}
.material-resume-pdf-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.material-resume-pdf-toolbar-zoom {
  display: flex;
  align-items: center;
  gap: 2px;
}
.material-resume-pdf-tool-btn {
  padding: 4px 8px !important;
  min-height: 28px !important;
}
.material-resume-pdf-zoom-label {
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #374151;
  min-width: 38px;
  text-align: center;
}
.material-resume-pdf-reset {
  font-size: 12px !important;
  padding: 4px 8px !important;
}
.material-resume-pdf-hint {
  margin: 0;
  font-size: 10px;
  color: #9ca3af;
  line-height: 1.3;
  flex-shrink: 0;
}
.material-resume-pdf-viewport {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
  background: #e5e7eb;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.material-resume-pdf-viewport.is-dragging {
  cursor: grabbing;
}
.material-resume-pdf-pan-layer {
  transform-origin: 0 0;
  will-change: transform;
  width: max-content;
  max-width: none;
}
.material-resume-pdf-pan-layer :deep(.resume-pdf-preview--sidebar) {
  min-height: 240px;
  width: 232px;
  overflow: visible;
}
.material-resume-text {
  max-height: 240px;
  overflow-x: auto;
  overflow-y: auto;
  scrollbar-gutter: stable;
  margin: 0;
  padding: 10px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  color: #1f2937;
  font-family: inherit;
}
.material-resume-empty {
  padding: 8px 0;
}
.material-dock-section--ai {
  padding-top: 4px;
  border-top: 1px dashed #e5e7eb;
}
.ai-assistant-desc {
  margin: 0 0 10px;
  font-size: 11px;
  line-height: 1.45;
  color: #6b7280;
}
.ai-assistant-card {
  padding: 10px;
  border-radius: 12px;
  background: linear-gradient(145deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
}
.ai-assistant-bubble {
  font-size: 12px;
  line-height: 1.45;
  padding: 8px 10px;
  border-radius: 10px;
  margin-bottom: 8px;
  max-width: 100%;
}
.ai-assistant-bubble--ai {
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #111827;
}
.ai-assistant-bubble--hint {
  background: rgba(59, 130, 246, 0.08);
  border: 1px dashed rgba(37, 99, 235, 0.25);
  color: #1d4ed8;
  font-size: 11px;
  margin-bottom: 10px;
}
.ai-assistant-input :deep(.el-textarea__inner) {
  font-size: 12px;
  resize: none;
}
.material-dock-tab {
  position: fixed;
  right: 0;
  top: 50%;
  z-index: 2001;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  min-height: 64px;
  padding: 6px 0;
  margin: 0;
  border: 1px solid #d8dbe3;
  border-right: none;
  border-radius: 10px 0 0 10px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  color: #374151;
  line-height: 1;
  transition:
    right 0.22s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}
.material-dock-tab:hover {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.12);
  transform: translateY(calc(-50% - 1px));
}
.material-dock-tab--panel-open {
  right: 280px;
}
.material-dock-tab-chevron {
  font-size: 16px;
  color: #2563eb;
}
.material-dock-tab:hover .material-dock-tab-chevron {
  color: #1d4ed8;
}

.resume-zoom-text {
  max-height: min(78vh, 720px);
  overflow: auto;
  margin: 0;
  padding: 8px;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

@media (max-width: 768px) {
  .material-dock-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 1999;
    background: rgba(15, 23, 42, 0.35);
  }
  .material-dock-panel {
    width: min(288px, 86vw);
    top: 0;
    bottom: 0;
    right: 0;
    height: auto;
    max-height: none;
    transform: none;
    border-radius: 12px 0 0 12px;
  }
  .material-dock-tab--panel-open {
    right: min(288px, 86vw);
  }
  .material-dock-slide-enter-from.material-dock-panel,
  .material-dock-slide-leave-to.material-dock-panel {
    transform: translateX(100%);
  }
}

/* —— GPT 风格：中性灰、扁平对话区、无「桌面」渐变 —— */
.interview-session--gpt {
  width: 100%;
  flex: 0 0 auto;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ececf1;
}
.interview-session--gpt.theme-page-shell {
  max-width: 100%;
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.session-card--gpt {
  width: 100%;
  height: 100vh;
  max-height: 100vh;
  align-self: center;
  display: flex !important;
  flex-direction: column;
  border: 1px solid #d9d9e0 !important;
  border-radius: 12px !important;
  background: #fff !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06) !important;
  overflow: hidden;
}
.session-card--gpt:hover {
  border-color: #d9d9e0 !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06) !important;
}
.session-card--gpt :deep(.el-card__header) {
  padding: 0 !important;
  border-bottom: 1px solid #ececec !important;
  background: #fff !important;
}
.session-card--gpt :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 !important;
  background: #f7f7f8;
  overflow: hidden;
}

.gpt-topbar {
  display: grid;
  grid-template-columns: minmax(72px, 1fr) minmax(0, 2.2fr) minmax(72px, 1fr);
  align-items: center;
  gap: 8px;
  padding: 10px 14px 10px 12px;
  min-height: 48px;
  box-sizing: border-box;
}
.gpt-topbar-side--left {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  min-width: 0;
}
.gpt-topbar-side--right {
  min-width: 0;
}
.gpt-topbar-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
  text-align: center;
}
.gpt-title-text {
  font-size: 15px;
  font-weight: 600;
  color: #202123;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
/* macOS 风格三色圆点：仅红色可点，结束面试 */
.window-traffic-lights {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
/* 小圆点紧凑排列，点击格略大于 11px 圆点即可 */
.window-traffic-slot {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.window-traffic-slot--decorative {
  pointer-events: none;
}
.window-traffic-dot {
  display: block;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow:
    inset 0 0 0 0.4px rgba(0, 0, 0, 0.18),
    0 0.5px 1px rgba(0, 0, 0, 0.08);
}
.window-traffic-dot--close {
  background: linear-gradient(180deg, #ff857c 0%, #ff5f57 100%);
}
.window-traffic-dot--min {
  background: linear-gradient(180deg, #ffd078 0%, #febc2e 100%);
}
.window-traffic-dot--zoom {
  background: linear-gradient(180deg, #63de6e 0%, #28c840 100%);
}
.window-traffic-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  line-height: 0;
  transition: background 0.15s ease;
}
.window-traffic-btn:focus-visible {
  outline: 2px solid rgba(32, 33, 35, 0.35);
  outline-offset: 1px;
}
.window-traffic-btn--close:hover {
  background: rgba(255, 95, 87, 0.14);
}
.window-traffic-btn--close:active {
  background: rgba(255, 95, 87, 0.22);
}

.mb-16 {
  margin: 12px 16px;
  flex-shrink: 0;
}

.session-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* 纯文本面试：仅右侧栏时占满高度 */
.session-workspace > .conference-right {
  flex: 1;
  min-height: 0;
}

.session-workspace {
  border-top: 1px solid #ececec;
}

.flow-rail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.flow-step {
  user-select: none;
  cursor: pointer;
  padding: 6px 4px;
  margin: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  transition: color 0.18s ease;
}
.flow-step:focus-visible {
  outline: 2px solid rgba(139, 92, 246, 0.5);
  outline-offset: 2px;
}
/* AI：主题紫系（.theme-section-decoration 左端） */
.flow-step:hover .flow-step-label--ai {
  color: #5b21b6;
  font-weight: 700;
}
/* 用户：主题蓝系（装饰条右端） */
.flow-step:hover .flow-step-label--user {
  color: #1d4ed8;
  font-weight: 700;
}
.flow-step:hover .flow-dot--ai {
  transform: scale(1.35);
  box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.32);
}
.flow-step:hover .flow-dot--user {
  transform: scale(1.35);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.32);
}
.flow-step:hover .flow-dot--thinking .flow-spin-icon {
  color: #9333ea;
}
.flow-step--has-anchor:hover .flow-step-label--ai,
.flow-step--has-anchor:hover .flow-step-label--user {
  text-decoration: underline;
  text-decoration-color: rgba(124, 58, 237, 0.45);
  text-underline-offset: 2px;
}
.flow-step-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 18px minmax(0, 1fr);
  align-items: start;
  gap: 4px 6px;
  min-height: 28px;
}
.flow-step-side {
  min-width: 0;
  font-size: 11px;
  line-height: 1.4;
  padding-top: 2px;
}
.flow-step-side--left {
  text-align: right;
}
.flow-step-side--right {
  text-align: left;
}
.flow-step-label {
  display: inline-block;
  max-width: 100%;
  word-break: break-word;
}
.flow-step-label--ai {
  color: #6d28d9;
  font-weight: 600;
}
.flow-step-label--user {
  color: #2563eb;
  font-weight: 600;
}
.flow-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 18px;
  flex-shrink: 0;
}
.flow-dot-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 18px;
}
.flow-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.flow-dot--ai {
  background: linear-gradient(145deg, #c084fc, #7c3aed);
}
.flow-dot--user {
  background: linear-gradient(145deg, #93c5fd, #2563eb);
}
.flow-dot--thinking {
  width: auto;
  height: auto;
  background: transparent;
  box-shadow: none;
}
.flow-spin-icon {
  font-size: 15px;
  color: #8b5cf6;
  transition: color 0.18s ease;
}
.flow-vert-line {
  width: 2px;
  flex: 1;
  min-height: 10px;
  margin: 4px 0 0;
  border-radius: 2px;
  background: linear-gradient(180deg, rgba(168, 85, 247, 0.55), rgba(59, 130, 246, 0.5));
}
.flow-step--thinking .flow-step-label--ai {
  color: #7c3aed;
}

.conference-right {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 0;
  min-height: 0;
  background: #f7f7f8;
}

.chat-panel-wrap {
  position: relative;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.chat-panel-wrap .chat-panel {
  flex: 1;
  min-height: 0;
}

.chat-scroll-to-bottom-fab {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 5;
  width: 40px;
  height: 40px;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 50%;
  background: linear-gradient(180deg, #ffffff 0%, #f4f4f6 100%);
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.04);
  color: #374151;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    color 0.15s ease,
    transform 0.15s ease;
}
.chat-scroll-to-bottom-fab:hover {
  border-color: #c5c5d2;
  background: #fff;
  color: #1d4ed8;
  box-shadow:
    0 4px 14px rgba(37, 99, 235, 0.12),
    0 2px 4px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}
.chat-scroll-to-bottom-fab:focus-visible {
  outline: 2px solid rgba(37, 99, 235, 0.45);
  outline-offset: 2px;
}
.chat-scroll-to-bottom-fab .el-icon {
  font-size: 18px;
}

.chat-scroll-fab-enter-active,
.chat-scroll-fab-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.chat-scroll-fab-enter-from,
.chat-scroll-fab-leave-to {
  opacity: 0;
  transform: translateY(6px);
}


.chat-panel {
  flex: 1;
  min-height: 200px;
  max-height: none;
  overflow-y: auto;
  padding: 20px 16px 16px;
  background: linear-gradient(180deg, #efeff2 0%, #f4f4f6 48%, #f7f7f8 100%);
  scrollbar-gutter: stable;
}
.conference-right .chat-panel {
  margin-bottom: 0;
}

.report-share-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 8px 0 12px;
  padding: 12px 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fafafb 100%);
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
  max-width: 100%;
}
.report-share-card:hover {
  border-color: #c5c5d2;
  background: #fafafa;
}
.report-share-card:focus {
  outline: 2px solid #202123;
  outline-offset: 1px;
}
.report-share-thumb {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #ececf1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.report-share-icon {
  font-size: 22px;
  line-height: 1;
}
.report-share-body {
  flex: 1;
  min-width: 0;
}
.report-share-title {
  font-size: 14px;
  font-weight: 600;
  color: #202123;
  margin-bottom: 4px;
}
.report-share-desc {
  font-size: 12px;
  color: #8e8ea0;
  line-height: 1.4;
}
.report-share-arrow {
  flex-shrink: 0;
  font-size: 16px;
  color: #8e8ea0;
}


.msg {
  margin-bottom: 16px;
}
.msg-row {
  display: inline-flex;
  align-items: flex-start;
  gap: 10px;
}
.msg-user {
  text-align: right;
}
.msg-user .msg-row {
  flex-direction: row-reverse;
}
/* 用户消息：纯色灰气泡 */
.msg-user .msg-bubble {
  background: #ececf1;
  color: #1a1a1e;
  margin-left: auto;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  border-radius: 18px 18px 5px 18px;
}
.msg-user .msg-bubble.msg-bubble-voice {
  display: inline-block;
  min-width: 220px;
  max-width: 360px;
}
.voice-topline {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  font-weight: 500;
  color: #202123;
}
.voice-icon {
  font-size: 14px;
  line-height: 1;
}
.voice-duration {
  font-size: 13px;
}
.msg-transcript {
  margin-top: 8px;
  font-size: 13px;
  color: #353740;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 8px;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-ai .msg-bubble {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.07);
  color: #2d2d33;
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.05),
    0 2px 8px rgba(0, 0, 0, 0.03);
  border-radius: 18px 18px 18px 5px;
}
.msg-ai .msg-bubble.msg-bubble-error {
  background: #fff5f5;
  border-color: rgba(220, 38, 38, 0.22);
  color: #b42318;
  box-shadow: 0 1px 3px rgba(180, 35, 24, 0.08);
  border-radius: 18px 18px 18px 5px;
}
.msg-label {
  font-size: 11px;
  font-weight: 500;
  color: #8e8ea0;
  margin-bottom: 4px;
  letter-spacing: 0.02em;
}
.msg-user .msg-label {
  text-align: right;
}
.msg-avatar {
  margin-top: 2px;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  overflow: hidden;
}
.msg-avatar :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.msg-bubble {
  display: inline-block;
  max-width: min(85%, 720px);
  padding: 12px 16px;
  border-radius: 18px;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.55;
  font-size: 14px;
}
.thinking-hint {
  color: #8e8ea0;
  font-size: 12px;
}
.streaming .cursor {
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

.composer-integrated {
  padding: 12px 16px 16px;
  background: #f7f7f8;
  border-top: 1px solid #ececec;
}
.composer-shell {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  padding: 10px 12px 8px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfcfd 100%);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.composer-shell:focus-within {
  border-color: #202123;
  box-shadow: 0 0 0 1px rgba(32, 33, 35, 0.12);
}
.composer-shell--recording {
  border-color: #dc2626;
  box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.2);
}
.composer-wave {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 3px;
  height: 36px;
  margin-bottom: 8px;
  padding: 0 4px;
}
.composer-wave-bar {
  width: 4px;
  min-height: 4px;
  border-radius: 2px;
  background: linear-gradient(180deg, #9ca3af, #4b5563);
  transform-origin: center bottom;
  transition: transform 0.06s ease-out;
}
.composer-shell--recording .composer-wave-bar {
  background: linear-gradient(180deg, #f87171, #dc2626);
}
.composer-rec-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #8e8ea0;
  text-align: center;
}
.composer-field :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  padding: 4px 2px 8px;
  resize: none;
  background: transparent;
  border-radius: 8px;
  line-height: 1.55;
  color: #202123;
  font-size: 14px;
}
.composer-field :deep(.el-textarea__inner):focus {
  box-shadow: none;
}
.composer-field :deep(.el-input__wrapper) {
  box-shadow: none;
  padding: 0;
  background: transparent;
}
.composer-field :deep(.el-input__count) {
  font-size: 12px;
  color: #8e8ea0;
  background: transparent;
}
.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 6px;
  border-top: 1px solid #ececf1;
  margin-top: 4px;
}
.composer-tool-btn {
  width: 38px;
  height: 38px;
  padding: 0;
}
.composer-send-btn.el-button--primary {
  background: #202123 !important;
  border-color: #202123 !important;
  color: #fff !important;
  --el-button-hover-bg-color: #ffffff !important;
  --el-button-hover-border-color: #202123 !important;
  --el-button-hover-text-color: #202123 !important;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease;
}
.composer-send-btn.el-button--primary:hover:not(.is-disabled) {
  background: #ffffff !important;
  border-color: #202123 !important;
  color: #202123 !important;
}
/* 挂断：与左上角红色圆点同色渐变 */
.composer-hangup-btn.el-button--danger {
  background: linear-gradient(180deg, #ff857c 0%, #ff5f57 100%) !important;
  border-color: rgba(0, 0, 0, 0.12) !important;
  color: #fff !important;
  --el-button-hover-bg-color: #e04b44 !important;
  --el-button-hover-border-color: rgba(0, 0, 0, 0.18) !important;
}
.composer-hangup-icon {
  transform: rotate(135deg);
  font-size: 18px;
}

/* 与 constants/breakpoints.ts MOBILE_MAX_WIDTH_PX 保持一致 */
@media (max-width: 768px) {
  .interview-session--gpt.theme-page-shell {
    max-width: 100%;
    padding: 0;
  }
}
</style>

<style>
/* 流程节点气泡挂载在 body 上，需全局样式 */
.flow-node-tooltip-popper.el-popper {
  max-width: 280px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e5e7eb !important;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%) !important;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.04),
    0 12px 28px -8px rgba(59, 130, 246, 0.12),
    0 8px 20px -10px rgba(168, 85, 247, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 1) !important;
}
.flow-node-tooltip-popper .flow-node-tooltip-content {
  max-width: 256px;
}
.flow-node-tooltip-popper .flow-node-tooltip-line {
  font-size: 12px;
  line-height: 1.55;
  color: #374151;
}
.flow-node-tooltip-popper .flow-node-tooltip-line:first-child {
  color: #111827;
  font-weight: 600;
}
.flow-node-tooltip-popper .flow-node-tooltip-line + .flow-node-tooltip-line {
  margin-top: 4px;
}
</style>
