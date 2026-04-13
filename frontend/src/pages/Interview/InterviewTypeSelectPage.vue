<template>
  <div class="setup-page">
    <InterviewSetupProgress :active="0" />
    <div class="card-grid">
      <article class="type-card theme-card" @click="chooseMode('text')">
        <h3>AI面试</h3>
        <p>文本/语音交互，支持智能追问和结构化反馈。</p>
      </article>

      <article class="type-card theme-card" @click="chooseMode('avatar')">
        <h3>虚拟人面试</h3>
        <p>更接近真实面试氛围，支持虚拟人口播互动。</p>
      </article>

      <article class="type-card theme-card is-disabled">
        <h3>第三种面试类型</h3>
        <p>待开发，后续开放更多能力。</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { saveInterviewSetupDraft } from './setupState';
import InterviewSetupProgress from './InterviewSetupProgress.vue';

const route = useRoute();
const router = useRouter();

function chooseMode(mode: 'text' | 'avatar') {
  saveInterviewSetupDraft({ mode });
  router.push({ name: 'HomeInterviewPosition' });
}

onMounted(() => {
  const mode = String(route.query.mode || '');
  if (mode === 'text' || mode === 'avatar') {
    chooseMode(mode);
  }
});
</script>

<style scoped>
.setup-page { display: block; }
.card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.type-card {
  position: relative;
  overflow: hidden;
  padding: 22px;
  min-height: 240px;
  cursor: pointer;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  border: 1px solid #d1d5db !important;
  background: linear-gradient(160deg, #ffffff 0%, #f7f8ff 100%) !important;
  box-shadow: 0 10px 24px -16px rgba(31, 41, 55, 0.35) !important;
}
.type-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #8b5cf6, #3b82f6);
  opacity: 0.75;
}
.type-card:hover {
  transform: translateY(-2px);
  border-color: #b9a8fd !important;
  box-shadow: 0 16px 30px -16px rgba(76, 29, 149, 0.28) !important;
}
.type-card h3 {
  margin: 0 0 12px;
  color: #111827;
  font-weight: 800;
  letter-spacing: 0.2px;
}
.type-card p {
  margin: 0;
  color: #4b5563;
  line-height: 1.7;
  min-height: 58px;
}
.is-disabled {
  opacity: .78;
  cursor: not-allowed;
  border-color: #e5e7eb !important;
}
.is-disabled::before {
  background: linear-gradient(90deg, #9ca3af, #d1d5db);
  opacity: 0.6;
}
/* 与 constants/breakpoints.ts MOBILE_MAX_WIDTH_PX 保持一致 */
@media (max-width: 768px) { .card-grid { grid-template-columns: 1fr; } }
</style>
