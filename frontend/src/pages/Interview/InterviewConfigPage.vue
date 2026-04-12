<template>
  <div class="setup-page">
    <InterviewSetupProgress :active="2" />
    <el-card class="theme-card" shadow="hover">
      <el-form label-width="120px">
        <el-form-item label="面试难度：">
          <div class="difficulty-grid">
            <article
              class="difficulty-card"
              :class="{ active: difficulty === 'easy' }"
              @click="difficulty = 'easy'"
            >
              <h4>简单</h4>
              <p>适合初次练习，问题更基础。</p>
            </article>
            <article
              class="difficulty-card"
              :class="{ active: difficulty === 'medium' }"
              @click="difficulty = 'medium'"
            >
              <h4>中等</h4>
              <p>常规面试强度，覆盖核心能力。</p>
            </article>
            <article
              class="difficulty-card"
              :class="{ active: difficulty === 'hard' }"
              @click="difficulty = 'hard'"
            >
              <h4>困难</h4>
              <p>更偏实战，追问深度更高。</p>
            </article>
          </div>
        </el-form-item>

        <el-form-item label="麦克风：">
          <div class="mic-tools">
            <el-button
              class="mic-icon-btn"
              :class="{ on: micEnabled }"
              circle
              @click="toggleMic"
            >
              <el-icon>
                <Microphone v-if="micEnabled" />
                <Mute v-else />
              </el-icon>
            </el-button>
            <el-button class="mic-test" @click="toggleMicTest" :disabled="!micEnabled">
              {{ testing ? '停止测试' : '测试麦克风' }}
            </el-button>
            <span v-if="permissionTip" class="permission-tip">{{ permissionTip }}</span>
          </div>
          <div class="meter-track">
            <div class="meter-bar" :style="{ width: `${level}%` }"></div>
          </div>
        </el-form-item>

        <div class="actions">
          <el-button @click="goPrev">上一步</el-button>
          <el-button type="primary" class="theme-primary-btn" @click="startInterview">开始面试</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { Microphone, Mute } from '@element-plus/icons-vue';
import { loadInterviewSetupDraft, saveInterviewSetupDraft, type InterviewDifficulty } from './setupState';
import InterviewSetupProgress from './InterviewSetupProgress.vue';

const router = useRouter();
const userStore = useUserStore();
const draft = loadInterviewSetupDraft();

const difficulty = ref<InterviewDifficulty>(draft.difficulty);
const micEnabled = ref(false);
const testing = ref(false);
const level = ref(0);
const permissionTip = ref('');
let stream: MediaStream | null = null;
let audioCtx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let source: MediaStreamAudioSourceNode | null = null;
let rafId: number | null = null;

function goPrev() {
  router.push({ name: 'HomeInterviewPosition' });
}

async function requestMicPermission() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micEnabled.value = true;
    permissionTip.value = '';
    return true;
  } catch {
    micEnabled.value = false;
    permissionTip.value = '请先在浏览器中开启麦克风权限';
    ElMessage.warning(permissionTip.value);
    return false;
  }
}

function stopMeter() {
  if (rafId != null) cancelAnimationFrame(rafId);
  rafId = null;
  level.value = 0;
  source?.disconnect();
  analyser?.disconnect();
  audioCtx?.close().catch(() => {});
  source = null;
  analyser = null;
  audioCtx = null;
}

function stopMic() {
  testing.value = false;
  stopMeter();
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  micEnabled.value = false;
}

async function toggleMic() {
  if (micEnabled.value) {
    stopMic();
    return;
  }
  await requestMicPermission();
}

function runMeter() {
  if (!analyser) return;
  const data = new Uint8Array(analyser.fftSize);
  const tick = () => {
    if (!testing.value || !analyser) return;
    analyser.getByteTimeDomainData(data);
    let peak = 0;
    for (let i = 0; i < data.length; i += 1) {
      const v = Math.abs(data[i] - 128) / 128;
      if (v > peak) peak = v;
    }
    level.value = Math.min(100, Math.round(peak * 170));
    rafId = requestAnimationFrame(tick);
  };
  rafId = requestAnimationFrame(tick);
}

async function toggleMicTest() {
  if (testing.value) {
    testing.value = false;
    stopMeter();
    return;
  }
  if (!micEnabled.value) {
    const ok = await requestMicPermission();
    if (!ok) return;
  }
  if (!stream) return;
  stopMeter();
  audioCtx = new AudioContext();
  source = audioCtx.createMediaStreamSource(stream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);
  testing.value = true;
  runMeter();
}

function startInterview() {
  const latest = loadInterviewSetupDraft();
  if (!latest.positionName || !latest.positionDetail) {
    ElMessage.warning('请先完成岗位选择');
    router.push({ name: 'HomeInterviewPosition' });
    return;
  }
  if (!latest.resumeId) {
    ElMessage.warning('请先选择个人简历后再开始面试');
    router.push({ name: 'HomeInterviewPosition' });
    return;
  }
  saveInterviewSetupDraft({
    difficulty: difficulty.value,
  });

  const payload = {
    resume_id: Number(latest.resumeId),
    position: latest.positionName,
    collection_name: 'general_engineer',
    user_id: userStore.userInfo?.id,
    difficulty: difficulty.value,
  };
  sessionStorage.setItem('pendingInterviewStart', JSON.stringify(payload));
  router.push({
    name: 'InterviewSession',
    params: { id: 'new' },
    query: {
      jobName: latest.positionName,
      interviewMode: latest.mode,
      avatarId: latest.avatarId || '110592024',
    },
  });
}
</script>

<style scoped>
.tests { display: flex; gap: 10px; flex-wrap: wrap; }
.actions { display: flex; justify-content: flex-end; gap: 10px; }
.difficulty-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.difficulty-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all .2s ease;
  background: #fff;
}
.difficulty-card:hover { border-color: #c4b5fd; background: #faf5ff; }
.difficulty-card.active { border-color: #8b5cf6; background: #f5f3ff; }
.difficulty-card h4 { margin: 0 0 6px; }
.difficulty-card p { margin: 0; color: #6b7280; font-size: 12px; line-height: 1.5; }
.mic-tools { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mic-icon-btn { width: 36px; height: 36px; border: 1px solid #d1d5db; }
.mic-icon-btn.on { color: #10b981; border-color: #86efac; }
.mic-test{ margin: 10px;}
.permission-tip { color: #e67e22; font-size: 12px; }
.meter-track {
  width: 220px;
  height: 8px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}
.meter-bar {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #3b82f6);
  transition: width .08s linear;
}
/* 与 constants/breakpoints.ts MOBILE_MAX_WIDTH_PX 保持一致 */
@media (max-width: 768px) { .difficulty-grid { grid-template-columns: 1fr; } }
</style>
