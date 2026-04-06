<template>
  <div class="interview-session-page">
    <el-card class="session-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-button link class="leave-btn" @click="onLeavePage">← 离开</el-button>
          <span class="card-title">模拟面试</span>
          <span class="header-placeholder"></span>
        </div>
      </template>

      <div v-if="jobName" class="job-info">当前面试岗位：<span class="job-name">{{ jobName }}</span></div>
      <div class="toolbar">
        <el-tag size="small" type="primary">新面试协议</el-tag>
        <el-tag v-if="isAvatarInterview" size="small" type="success">虚拟人面试</el-tag>
      </div>

      <el-alert
        v-if="showMissingSessionAlert"
        title="请先完成面试设置"
        type="warning"
        description="请从岗位详情进入「面试设置」页并开始面试。"
        show-icon
        class="mb-16"
      />

      <template v-else-if="canRenderInterview">
        <div class="session-workspace" :class="{ 'conference-layout': isAvatarInterview }">
          <div v-if="isAvatarInterview" class="conference-left">
            <div class="participant-card">
              <div class="participant-title">我</div>
              <div class="participant-stage">
                <el-avatar class="participant-avatar" :size="78" :src="userAvatar">我</el-avatar>
              </div>
            </div>

            <div class="avatar-panel">
              <div class="avatar-header">
                <span>虚拟人口播</span>
                <el-tag size="small" :type="avatarReady ? 'success' : 'warning'">
                  {{ avatarReady ? '已连接' : '连接中' }}
                </el-tag>
              </div>
              <div class="avatar-stage">
                <div ref="avatarStageRef" class="avatar-sdk-mount"></div>
                <div v-if="!avatarMountedBySdk" class="avatar-placeholder">
                  {{ avatarStatusText || '正在初始化虚拟人...' }}
                </div>
              </div>
              <div class="avatar-tip">{{ avatarStatusText }}</div>
            </div>
          </div>

          <div class="conference-right">
            <div class="chat-panel" ref="chatPanelRef">
              <div v-for="(m, idx) in messages" :key="idx" class="msg" :class="m.role === 'user' ? 'msg-user' : 'msg-ai'">
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
                  :placeholder="
                    isRecording ? '录音中…' : '输入回答，Enter 发送 · Shift+Enter 换行'
                  "
                  :disabled="streaming || isRecording"
                  class="composer-field"
                  @keydown.enter.exact.prevent="sendMessage"
                />
                <div class="composer-toolbar">
                  <el-button
                    circle
                    :type="isRecording ? 'danger' : 'default'"
                    :disabled="streaming"
                    class="composer-tool-btn"
                    :title="isRecording ? '停止并发送' : '语音回答'"
                    @click="toggleVoiceRecord"
                  >
                    <el-icon><Microphone /></el-icon>
                  </el-button>
                  <el-button
                    circle
                    type="primary"
                    :disabled="streaming || isRecording || !userInput.trim()"
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
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Microphone, Right } from '@element-plus/icons-vue';
import {
  startInterviewApi,
  streamInterviewAnswer,
  streamInterviewVoiceAnswer,
  getInterviewSessionApi,
  endInterviewSessionApi,
  startAvatarInterviewSessionApi,
  refreshAvatarInterviewSessionApi,
  endAvatarInterviewSessionApi,
  type StartInterviewBody,
  type InterviewAnswerStreamEvent,
} from '@/api/interviewAi';
import { useUserStore } from '@/store/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const jobName = computed(() => (route.query.jobName as string) || '');
/** 会话 ID：路由 query 与「pending 创建后立即回填」合并，避免仅有 pending 时 query 仍为空导致发语音/文字静默 return、网络里看不到请求 */
const effectiveSessionId = ref(String(route.query.sessionId || ''));
watch(
  () => route.query.sessionId,
  (q) => {
    if (q != null && String(q).trim()) effectiveSessionId.value = String(q).trim();
  }
);
const userAvatar = computed(() => userStore.userInfo?.avatarUrl || '');
const aiAvatarSrc = computed(() => '/img/mentor-a.png');
const hasPendingStart = ref(false);
const isAvatarInterview = computed(() => String(route.query.interviewMode || '') === 'avatar');
const selectedAvatarId = computed(() => String(route.query.avatarId || '110592024'));
const avatarReady = ref(false);
const avatarStatusText = ref('');
const avatarSessionId = ref('');
const avatarStageRef = ref<HTMLElement | null>(null);
const avatarMountedBySdk = ref(false);
const AVATAR_SDK_SCRIPT_URL =
  (import.meta.env.VITE_AVATAR_SDK_SCRIPT_URL as string | undefined)?.trim() || '';
// 按当前需求：在前端写死虚拟人鉴权信息（注意：存在泄露风险，仅建议内网/临时联调）
const AVATAR_API_KEY_HARDCODED = 'edd0a5f6b5dc07c433756fedfb59887c';
const AVATAR_API_SECRET_HARDCODED = 'NmRmZTY4YzMyNDM0NDI5ZWYzZWQyNzQ5';
let avatarRefreshTimer: number | null = null;
let avatarSdkInstance: { destroy?: () => void; stop?: () => void; updateToken?: (token: string) => void } | null =
  null;
let avatarPlayerInstance: { resume?: () => void } | null = null;
let avatarSdkModuleCtor: unknown = null;

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
const chatPanelRef = ref<HTMLElement | null>(null);
const showThinkingHint = computed(() => streaming.value && !streamingText.value);
const canRenderInterview = computed(
  () => Boolean(effectiveSessionId.value || hasPendingStart.value)
);
const showMissingSessionAlert = computed(() => !canRenderInterview.value);

const isRecording = ref(false);
const waveformBars = ref<number[]>(Array.from({ length: 24 }, () => 0));
let mediaRecorder: MediaRecorder | null = null;
let recordStream: MediaStream | null = null;
let recordChunks: Blob[] = [];
let recordStartedAt = 0;
let audioContext: AudioContext | null = null;
let audioAnalyser: AnalyserNode | null = null;
let audioSourceNode: MediaStreamAudioSourceNode | null = null;
let meterRafId: number | null = null;

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
      for (let i = start; i < end; i++) sum += dataArray[i];
      next.push(sum / (end - start) / 255);
    }
    waveformBars.value = next;
    meterRafId = requestAnimationFrame(tick);
  };
  meterRafId = requestAnimationFrame(tick);
}

onBeforeUnmount(() => {
  clearAvatarRefreshTimer();
  if (isAvatarInterview.value && effectiveSessionId.value) {
    void endAvatarInterviewSessionApi(effectiveSessionId.value).catch(() => {});
  }
  try {
    avatarSdkInstance?.stop?.();
    avatarSdkInstance?.destroy?.();
  } catch {
    /* ignore */
  }
  avatarSdkInstance = null;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.onstop = null;
    mediaRecorder.stop();
  }
  recordChunks = [];
  isRecording.value = false;
  stopMicTracks();
});

function stopMicTracks() {
  stopAudioMeter();
  recordStream?.getTracks().forEach((t) => t.stop());
  recordStream = null;
  mediaRecorder = null;
}

async function renderStreamingText(text: string) {
  const full = String(text || '');
  streamingText.value = '';
  if (!full) return;
  for (let i = 0; i < full.length; i += 1) {
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
  const id = route.params.id;
  if (id) router.push({ name: 'InterviewSettings', params: { id: String(id) } });
  else router.push({ name: 'Home' });
}

function clearAvatarRefreshTimer() {
  if (avatarRefreshTimer != null) {
    window.clearTimeout(avatarRefreshTimer);
    avatarRefreshTimer = null;
  }
}

async function ensureAvatarSdkLoaded() {
  if (!AVATAR_SDK_SCRIPT_URL) {
    throw new Error('未配置 VITE_AVATAR_SDK_SCRIPT_URL');
  }
  if (avatarSdkModuleCtor) return;
  const win = window as unknown as Record<string, unknown>;
  const ctorFromGlobal =
    (win.AvatarPlatform as unknown) ||
    (win.XnrptAvatarSDK as unknown) ||
    (win.VirtualHumanSDK as unknown) ||
    (win.xnrptAvatarSDK as unknown);
  if (ctorFromGlobal) {
    avatarSdkModuleCtor = ctorFromGlobal;
    return;
  }

  // 1) ESM 方式：用 module 脚本导入并挂到 window，避免 “Cannot use import statement outside a module”
  const key = encodeURIComponent(AVATAR_SDK_SCRIPT_URL);
  const doneEvent = `__avatar_sdk_es_loaded__${key}`;
  const failEvent = `__avatar_sdk_es_failed__${key}`;
  const existingEs = document.querySelector(`script[data-avatar-sdk-es="${AVATAR_SDK_SCRIPT_URL}"]`);
  if (!existingEs) {
    const ms = document.createElement('script');
    ms.type = 'module';
    ms.dataset.avatarSdkEs = AVATAR_SDK_SCRIPT_URL;
    ms.textContent = `
      import AvatarCtor, * as AvatarNs from '${AVATAR_SDK_SCRIPT_URL}';
      window.__avatarSdkCtor = AvatarCtor || AvatarNs?.AvatarPlatform || AvatarNs?.default || AvatarNs;
      window.dispatchEvent(new CustomEvent('${doneEvent}'));
    `;
    ms.onerror = () => {
      window.dispatchEvent(new CustomEvent(failEvent));
    };
    document.head.appendChild(ms);
  }
  const esmLoaded = await new Promise<boolean>((resolve) => {
    const onDone = () => {
      window.removeEventListener(doneEvent, onDone as EventListener);
      window.removeEventListener(failEvent, onFail as EventListener);
      resolve(true);
    };
    const onFail = () => {
      window.removeEventListener(doneEvent, onDone as EventListener);
      window.removeEventListener(failEvent, onFail as EventListener);
      resolve(false);
    };
    window.addEventListener(doneEvent, onDone as EventListener, { once: true });
    window.addEventListener(failEvent, onFail as EventListener, { once: true });
    // 已经加载成功的情况，立即返回
    if ((window as unknown as Record<string, unknown>).__avatarSdkCtor) onDone();
  });
  if (esmLoaded) {
    avatarSdkModuleCtor = (window as unknown as Record<string, unknown>).__avatarSdkCtor as unknown;
    if (avatarSdkModuleCtor) return;
  }

  // 2) 回退：全局 script 注入（UMD 版本）
  if (win.AvatarPlatform || win.XnrptAvatarSDK || win.VirtualHumanSDK || win.xnrptAvatarSDK) return;
  await new Promise<void>((resolve, reject) => {
    const exists = document.querySelector(`script[data-avatar-sdk="${AVATAR_SDK_SCRIPT_URL}"]`);
    if (exists) {
      exists.addEventListener('load', () => resolve(), { once: true });
      exists.addEventListener('error', () => reject(new Error('虚拟人SDK脚本加载失败')), { once: true });
      return;
    }
    const s = document.createElement('script');
    s.src = AVATAR_SDK_SCRIPT_URL;
    s.async = true;
    s.dataset.avatarSdk = AVATAR_SDK_SCRIPT_URL;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('虚拟人SDK脚本加载失败'));
    document.head.appendChild(s);
  });
}

async function initAvatarSdk(started: {
  avatar_id: string;
  sdk_config: {
    app_id: string;
    server_url: string;
    signed_url: string;
    scene_id: string;
    vcn: string;
    protocol: 'xrtc' | 'webrtc';
    alpha: 0 | 1;
    token: string;
  };
}) {
  if (!avatarStageRef.value) throw new Error('虚拟人容器未就绪');
  await ensureAvatarSdkLoaded();
  const win = window as unknown as Record<string, unknown>;
  const sdk =
    (avatarSdkModuleCtor as Record<string, unknown> | undefined) ||
    (win.AvatarPlatform as Record<string, unknown> | undefined) ||
    (win.XnrptAvatarSDK as Record<string, unknown> | undefined) ||
    (win.VirtualHumanSDK as Record<string, unknown> | undefined) ||
    (win.xnrptAvatarSDK as Record<string, unknown> | undefined);
  if (!sdk) throw new Error('未找到虚拟人SDK全局对象');
  const mountEl = avatarStageRef.value;
  mountEl.innerHTML = '';
  // 文档标准流程：创建实例 -> setApiInfo -> setGlobalParams -> start
  if (typeof sdk === 'function') {
    avatarSdkInstance = new (sdk as new (opt?: unknown) => {
      setApiInfo?: (p: unknown) => void;
      setGlobalParams?: (p: unknown) => void;
      start?: (p: unknown) => Promise<unknown>;
      writeText?: (text: string, ext?: unknown) => Promise<unknown>;
      on?: (evt: string, cb: (...args: unknown[]) => void) => void;
      player?: { resume?: () => void };
      destroy?: () => void;
      stop?: () => void;
      updateToken?: (token: string) => void;
    })({ useInlinePlayer: true });
  } else if (typeof (sdk.create as unknown) === 'function') {
    avatarSdkInstance = (await (sdk.create as (opt: unknown) => Promise<unknown> | unknown)({
      useInlinePlayer: true,
    })) as {
      setApiInfo?: (p: unknown) => void;
      setGlobalParams?: (p: unknown) => void;
      start?: (p: unknown) => Promise<unknown>;
      writeText?: (text: string, ext?: unknown) => Promise<unknown>;
      on?: (evt: string, cb: (...args: unknown[]) => void) => void;
      player?: { resume?: () => void };
      destroy?: () => void;
      stop?: () => void;
      updateToken?: (token: string) => void;
    };
  } else {
    throw new Error('SDK缺少实例创建方法，请按文档适配');
  }
  if (typeof (avatarSdkInstance as { setApiInfo?: (p: unknown) => void }).setApiInfo === 'function') {
    (avatarSdkInstance as { setApiInfo: (p: unknown) => void }).setApiInfo({
      appId: started.sdk_config.app_id,
      apiKey: AVATAR_API_KEY_HARDCODED,
      apiSecret: AVATAR_API_SECRET_HARDCODED,
      sceneId: started.sdk_config.scene_id,
      serverUrl: started.sdk_config.server_url,
      signedUrl: undefined,
    });
  }
  if (
    typeof (avatarSdkInstance as { setGlobalParams?: (p: unknown) => void }).setGlobalParams ===
    'function'
  ) {
    (avatarSdkInstance as { setGlobalParams: (p: unknown) => void }).setGlobalParams({
      stream: {
        protocol: started.sdk_config.protocol || 'xrtc',
        alpha: started.sdk_config.alpha ?? 1,
      },
      avatar: {
        avatar_id: started.avatar_id,
      },
      tts: {
        vcn: started.sdk_config.vcn,
      },
    });
  }
  if (typeof (avatarSdkInstance as { on?: (evt: string, cb: (...args: unknown[]) => void) => void }).on === 'function') {
    (avatarSdkInstance as { on: (evt: string, cb: (...args: unknown[]) => void) => void }).on('playNotAllowed', () => {
      avatarStatusText.value = '浏览器拦截自动播放，请点击页面后继续';
    });
  }
  if (typeof (avatarSdkInstance as { start?: (p: unknown) => Promise<unknown> }).start === 'function') {
    await (avatarSdkInstance as { start: (p: unknown) => Promise<unknown> }).start({ wrapper: mountEl });
  }
  avatarPlayerInstance =
    ((avatarSdkInstance as { player?: { resume?: () => void } }).player as { resume?: () => void } | undefined) ||
    null;
  avatarMountedBySdk.value = true;
}

function speakByAvatarSdk(text: string, interrupt = true) {
  if (!avatarSdkInstance || !text.trim()) return;
  avatarPlayerInstance?.resume?.();
  if (typeof (avatarSdkInstance as { writeText?: (t: string, ext?: unknown) => Promise<unknown> }).writeText !== 'function') return;
  void (avatarSdkInstance as { writeText: (t: string, ext?: unknown) => Promise<unknown> })
    .writeText(text, { nlp: false, interrupt })
    .catch((e) => {
      avatarStatusText.value = `虚拟人口播失败：${(e as Error)?.message || '未知错误'}`;
    });
}

function scheduleAvatarRefresh(sessionId: string, delayMs: number) {
  clearAvatarRefreshTimer();
  avatarRefreshTimer = window.setTimeout(async () => {
    if (!avatarSessionId.value) return;
    try {
      const refreshed = await refreshAvatarInterviewSessionApi(sessionId, avatarSessionId.value);
      avatarSdkInstance?.updateToken?.(refreshed.sdk_config.token);
      const now = Math.floor(Date.now() / 1000);
      const nextMs = Math.max(10_000, (refreshed.sdk_config.expire_at - now - 30) * 1000);
      avatarStatusText.value = '虚拟人会话续签成功';
      scheduleAvatarRefresh(sessionId, nextMs);
    } catch (e: unknown) {
      avatarStatusText.value = `虚拟人续签失败：${(e as Error).message || '未知错误'}`;
    }
  }, Math.max(10_000, delayMs));
}

async function initAvatarSession(sessionId: string) {
  if (!isAvatarInterview.value) return;
  try {
    avatarStatusText.value = '正在申请虚拟人会话...';
    const data = await startAvatarInterviewSessionApi(sessionId, selectedAvatarId.value);
    avatarSessionId.value = data.avatar_session_id;
    avatarMountedBySdk.value = false;
    await initAvatarSdk(data);
    avatarReady.value = true;
    avatarStatusText.value = `虚拟人SDK初始化完成（vendor: ${data.vendor}）`;
    const now = Math.floor(Date.now() / 1000);
    const nextMs = Math.max(10_000, (data.sdk_config.expire_at - now - 30) * 1000);
    scheduleAvatarRefresh(sessionId, nextMs);
  } catch (e: unknown) {
    avatarReady.value = false;
    avatarMountedBySdk.value = false;
    avatarStatusText.value = `虚拟人初始化失败：${(e as Error).message || '未知错误'}`;
    ElMessage.warning(avatarStatusText.value);
  }
}

function formatVoiceDuration(sec?: number): string {
  const s = Math.max(1, Number.isFinite(sec as number) ? Math.round(sec as number) : 1);
  return `${s}"`;
}

function createVoicePlaceholderMessage(voiceDurationSec?: number): ChatMessage {
  return { role: 'user', content: '语音消息', kind: 'voice', voiceDurationSec };
}

function extByMimeType(mimeType: string): 'webm' | 'ogg' | 'wav' {
  const t = (mimeType || '').toLowerCase();
  if (t.includes('wav')) return 'wav';
  if (t.includes('ogg')) return 'ogg';
  return 'webm';
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
    try {
      streaming.value = true;
      const payload = JSON.parse(pending) as StartInterviewBody;
      if (!payload.interview_mode && route.query.interviewMode) {
        payload.interview_mode = String(route.query.interviewMode) as 'text' | 'voice' | 'avatar';
      }
      if (!payload.avatar_id && route.query.avatarId) {
        payload.avatar_id = String(route.query.avatarId);
      }
      const started = await startInterviewApi(payload);
      sid = started.session_id;
      effectiveSessionId.value = sid;
      sessionStorage.removeItem('pendingInterviewStart');
      hasPendingStart.value = false;
      await router.replace({
        query: {
          ...route.query,
          sessionId: sid,
          jobName: payload.position,
          interviewMode: payload.interview_mode || route.query.interviewMode || 'text',
          avatarId: payload.avatar_id || route.query.avatarId || '110592024',
        },
      });
    } catch (e: unknown) {
      sessionStorage.removeItem('pendingInterviewStart');
      hasPendingStart.value = false;
      streaming.value = false;
      ElMessage.error((e as Error).message || '创建面试会话失败');
      return;
    }
  }
  try {
    await initAvatarSession(sid);
    const info = await getInterviewSessionApi(sid);
    (info.history || []).forEach((h) => {
      messages.value.push({ role: 'assistant', content: h.question, kind: 'text' });
      messages.value.push({ role: 'user', content: h.answer, kind: 'text' });
    });
    if (info.current_question) messages.value.push({ role: 'assistant', content: info.current_question, kind: 'text' });
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '恢复会话失败');
  } finally {
    streaming.value = false;
  }
});

function attachAnswerStreamHandler(voiceMessageIndex: number | null = null) {
  let uiChain: Promise<void> = Promise.resolve();
  const onEvent = (evt: InterviewAnswerStreamEvent) => {
    updateVoiceTranscriptAt(voiceMessageIndex, pickTranscriptText(evt.data));
    if (evt.type === 'voice_processing' || evt.type === 'analyzing') {
      const hint = String(evt.data.message || '').trim();
      if (hint) streamingText.value = hint;
    } else if (evt.type === 'analysis_result') {
      const feedback = String(evt.data.feedback || '').trim();
      if (feedback) {
        if (isAvatarInterview.value && effectiveSessionId.value && avatarReady.value) {
          speakByAvatarSdk(feedback, false);
        }
        uiChain = uiChain.then(async () => {
          await renderStreamingText(feedback);
          messages.value.push({ role: 'assistant', content: feedback });
          streamingText.value = '';
          scrollToBottom();
        });
      }
    } else if (evt.type === 'followup') {
      const msg = String(evt.data.message || '').trim();
      if (msg) {
        if (isAvatarInterview.value && effectiveSessionId.value && avatarReady.value) {
          speakByAvatarSdk(msg, false);
        }
        uiChain = uiChain.then(async () => {
          await renderStreamingText(msg);
          messages.value.push({ role: 'assistant', content: msg });
          streamingText.value = '';
          scrollToBottom();
        });
      }
    } else if (evt.type === 'question') {
      const msg = String(evt.data.answer || evt.data.question || '').trim();
      if (msg) {
        if (isAvatarInterview.value && effectiveSessionId.value && avatarReady.value) {
          speakByAvatarSdk(msg, true);
        }
        uiChain = uiChain.then(async () => {
          await renderStreamingText(msg);
          messages.value.push({ role: 'assistant', content: msg });
          scrollToBottom();
        });
      }
    } else if (evt.type === 'error') {
      const msg = String(evt.data.message || '').trim() || '处理失败';
      streamingText.value = '';
      messages.value.push({ role: 'assistant', content: msg, tone: 'error' });
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
  const text = userInput.value.trim();
  if (!text || streaming.value) return;

  messages.value.push({ role: 'user', content: text, kind: 'text' });
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
    scrollToBottom();
  }
}

async function sendVoiceFile(file: File, voiceDurationSec?: number) {
  const sid = effectiveSessionId.value;
  if (!sid) {
    ElMessage.warning('会话尚未就绪，无法发送语音');
    return;
  }
  if (streaming.value) return;

  messages.value.push(createVoicePlaceholderMessage(voiceDurationSec));
  const voiceMsgIndex = messages.value.length - 1;
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
    scrollToBottom();
  }
}

async function startVoiceRecord() {
  if (!effectiveSessionId.value) {
    ElMessage.warning('会话尚未就绪，无法开始录音');
    return;
  }
  if (streaming.value) return;
  try {
    recordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime =
      typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : '';
    mediaRecorder = mime
      ? new MediaRecorder(recordStream, { mimeType: mime })
      : new MediaRecorder(recordStream);
    recordChunks = [];
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordChunks.push(e.data);
    };
    mediaRecorder.onstop = () => {
      void finalizeRecordingAndSendVoice();
    };
    recordStartedAt = Date.now();
    mediaRecorder.start(250);
    startAudioMeter(recordStream);
    isRecording.value = true;
  } catch (e: unknown) {
    stopMicTracks();
    ElMessage.error('无法使用麦克风：' + ((e as Error).message || '请检查权限'));
  }
}

function stopVoiceRecorderOnly() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    return;
  }
  isRecording.value = false;
  stopMicTracks();
}

async function finalizeRecordingAndSendVoice() {
  const mr = mediaRecorder;
  const mimeType = mr?.mimeType || 'audio/webm';
  mediaRecorder = null;
  const blob = new Blob(recordChunks, { type: mimeType });
  recordChunks = [];
  stopMicTracks();
  isRecording.value = false;
  const durationSec = Math.max(1, Math.round((Date.now() - recordStartedAt) / 1000));
  recordStartedAt = 0;

  if (!blob.size) {
    ElMessage.warning('录音过短或未采集到音频');
    return;
  }
  // 文件后缀与真实 MIME 一致，避免后端按错误容器解码导致“噪音”
  const ext = extByMimeType(mimeType);
  const file = new File([blob], `frontend-record.${ext}`, { type: mimeType });
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
    avatarPlayerInstance?.resume?.();
    await ElMessageBox.confirm('是否保存当前面试进度后离开？', '离开面试', {
      confirmButtonText: '保存并离开',
      cancelButtonText: '不保存并离开',
      distinguishCancelAndClose: true,
      type: 'warning',
      closeOnClickModal: false,
    });
    // 保存并离开：保留会话，直接返回设置页
    if (sid && isAvatarInterview.value) {
      void endAvatarInterviewSessionApi(sid).catch(() => {});
    }
    backToSettings();
  } catch (e) {
    // 点击“取消”分支按“不保存并离开”处理；关闭弹窗则不做操作
    if (e !== 'cancel') return;
    if (sid) {
      try {
        if (isAvatarInterview.value) {
          await endAvatarInterviewSessionApi(sid);
        }
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
.interview-session-page { width: 100%; height: 100%; margin: 0; }
.session-card { width: 100%; min-height: 72vh; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; }
.leave-btn { color: #606266; }
.header-placeholder { width: 48px; }
.job-info { margin-bottom: 8px; }
.job-name { font-weight: 600; }
.toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.mb-16 { margin-bottom: 16px; }
.session-workspace { display: block; }
.conference-layout {
  display: grid;
  grid-template-columns: 400px minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
}
.conference-left {
  display: grid;
  grid-template-rows: 160px minmax(0, 1fr);
  gap: 12px;
}
.conference-right {
  display: grid;
  grid-template-rows: minmax(320px, 1fr) auto;
  gap: 10px;
}
.participant-card {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
}
.participant-title {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}
.participant-stage {
  height: 116px;
  border-radius: 8px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.participant-avatar { border: 2px solid #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
.avatar-panel {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  min-height: 260px;
}
.avatar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #303133;
  font-weight: 600;
}
.avatar-stage {
  position: relative;
  width: 100%;
  height: 220px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
}
.avatar-sdk-mount {
  position: absolute;
  inset: 0;
  z-index: 2;
}
.avatar-video { width: 100%; height: 100%; object-fit: cover; background: #000; }
.avatar-sdk-mount :deep(video),
.avatar-sdk-mount :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover;
  object-position: center top;
  transform: scale(1.18);
  transform-origin: center top;
}
.avatar-placeholder {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 13px;
}
.avatar-tip { margin-top: 6px; color: #909399; font-size: 12px; }
.chat-panel { min-height: 360px; max-height: 520px; overflow-y: auto; padding: 12px; background: #f5f7fa; border-radius: 8px; margin-bottom: 16px; }
.conference-right .chat-panel { margin-bottom: 0; max-height: none; }
.msg { margin-bottom: 14px; }
.msg-row { display: inline-flex; align-items: flex-start; gap: 8px; }
.msg-user { text-align: right; }
.msg-user .msg-row { flex-direction: row-reverse; }
.msg-user .msg-bubble { background: #409eff; color: #fff; margin-left: auto; }
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
}
.voice-icon { font-size: 14px; line-height: 1; }
.voice-duration { font-size: 14px; }
.msg-transcript {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.35);
  padding-top: 8px;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-ai .msg-bubble { background: #fff; border: 1px solid #ebeef5; }
.msg-ai .msg-bubble.msg-bubble-error {
  background: #fef0f0;
  border-color: #fde2e2;
  color: #c45656;
}
.msg-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.msg-user .msg-label { text-align: right; }
.msg-avatar { margin-top: 2px; flex: 0 0 30px; width: 30px; height: 30px; min-width: 30px; min-height: 30px; overflow: hidden; }
.msg-avatar :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.msg-bubble { display: inline-block; max-width: 85%; padding: 10px 14px; border-radius: 10px; text-align: left; white-space: pre-wrap; word-break: break-word; line-height: 1.5; font-size: 14px; }
.thinking-hint { color: #909399; font-size: 12px; }
.streaming .cursor { animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
.composer-integrated { margin-top: 4px; }
.composer-shell {
  border: 1px solid var(--el-border-color);
  border-radius: 16px;
  padding: 10px 12px 8px;
  background: var(--el-bg-color);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.composer-shell:focus-within {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}
.composer-shell--recording {
  border-color: var(--el-color-danger-light-5);
  box-shadow: 0 0 0 1px var(--el-color-danger-light-7);
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
  background: linear-gradient(180deg, var(--el-color-primary-light-3), var(--el-color-primary));
  transform-origin: center bottom;
  transition: transform 0.06s ease-out;
}
.composer-shell--recording .composer-wave-bar {
  background: linear-gradient(180deg, #f89898, var(--el-color-danger));
}
.composer-rec-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
}
.composer-field :deep(.el-textarea__inner):focus {
  box-shadow: none;
}
.composer-field :deep(.el-input__wrapper) {
  box-shadow: none;
  padding: 0;
  background: transparent;
}
.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 2px;
}
.composer-tool-btn {
  width: 40px;
  height: 40px;
  padding: 0;
}
.composer-send-btn.el-button--primary {
  --el-button-hover-bg-color: var(--el-color-primary-light-3);
}
</style>
