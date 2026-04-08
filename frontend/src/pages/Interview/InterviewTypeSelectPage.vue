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
.type-card { padding: 22px; min-height: 240px; cursor: pointer; transition: transform .2s ease; display: flex; flex-direction: column; justify-content: flex-start; }
.type-card:hover { transform: translateY(-2px); }
.type-card h3 { margin: 0 0 12px; }
.type-card p { margin: 0; color: #6b7280; line-height: 1.7; min-height: 58px; }
.is-disabled { opacity: .7; cursor: not-allowed; }
@media (max-width: 1100px) { .card-grid { grid-template-columns: 1fr; } }
</style>
