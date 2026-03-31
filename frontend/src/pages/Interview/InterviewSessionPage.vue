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
                  :class="{ 'msg-bubble-error': m.role === 'assistant' && m.tone === 'error' }"
                >
                  {{ m.content }}
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

const messages = ref<{ role: 'user' | 'assistant'; content: string; tone?: 'error' }[]>([]);
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

onMounted(async () => {
  hasPendingStart.value = !!sessionStorage.getItem('pendingInterviewStart');
  let sid = effectiveSessionId.value;
  if (!sid) {
    const pending = sessionStorage.getItem('pendingInterviewStart');
    if (!pending) return;
    try {
      streaming.value = true;
      const payload = JSON.parse(pending) as StartInterviewBody;
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
    const info = await getInterviewSessionApi(sid);
    (info.history || []).forEach((h) => {
      messages.value.push({ role: 'assistant', content: h.question });
      messages.value.push({ role: 'user', content: h.answer });
    });
    if (info.current_question) messages.value.push({ role: 'assistant', content: info.current_question });
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '恢复会话失败');
  } finally {
    streaming.value = false;
  }
});

function attachAnswerStreamHandler() {
  let uiChain: Promise<void> = Promise.resolve();
  const onEvent = (evt: InterviewAnswerStreamEvent) => {
    if (evt.type === 'voice_processing' || evt.type === 'analyzing') {
      const hint = String(evt.data.message || '').trim();
      if (hint) streamingText.value = hint;
    } else if (evt.type === 'analysis_result') {
      const feedback = String(evt.data.feedback || '').trim();
      if (feedback) {
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

  messages.value.push({ role: 'user', content: text });
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

async function sendVoiceFile(file: File) {
  const sid = effectiveSessionId.value;
  if (!sid) {
    ElMessage.warning('会话尚未就绪，无法发送语音');
    return;
  }
  if (streaming.value) return;

  messages.value.push({ role: 'user', content: '[语音回答]' });
  streaming.value = true;
  streamingText.value = '';

  try {
    const { onEvent, drain } = attachAnswerStreamHandler();
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

  if (!blob.size) {
    ElMessage.warning('录音过短或未采集到音频');
    return;
  }
  // 与 Apifox 示例 `fronten.wav` 一致；实际多为 webm 数据，type 保持真实 MIME，供后端识别转码
  const file = new File([blob], 'fronten.wav', { type: mimeType });
  await sendVoiceFile(file);
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
    // 保存并离开：保留会话，直接返回设置页
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
.interview-session-page { max-width: 800px; margin: 0 auto; }
.session-card { width: 100%; min-height: 72vh; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; }
.leave-btn { color: #606266; }
.header-placeholder { width: 48px; }
.job-info { margin-bottom: 8px; }
.job-name { font-weight: 600; }
.toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.mb-16 { margin-bottom: 16px; }
.chat-panel { min-height: 360px; max-height: 520px; overflow-y: auto; padding: 12px; background: #f5f7fa; border-radius: 8px; margin-bottom: 16px; }
.msg { margin-bottom: 14px; }
.msg-row { display: inline-flex; align-items: flex-start; gap: 8px; }
.msg-user { text-align: right; }
.msg-user .msg-row { flex-direction: row-reverse; }
.msg-user .msg-bubble { background: #409eff; color: #fff; margin-left: auto; }
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
