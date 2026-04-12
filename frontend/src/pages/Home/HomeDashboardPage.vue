<template>
  <div class="home-dashboard-page">
    <section class="hero fade-in-up delay-1">
      <div class="hero-left theme-card">
        <h1>今天开始一次高质量模拟面试</h1>
        <p>选择岗位方向与面试模式，10 秒进入训练。</p>
        <el-button type="primary" class="theme-primary-btn" @click="goInterviewSettings">立即开始面试</el-button>
      </div>
      <div class="hero-right">
        <div class="kpi-variants">
          <article class="kpi-card theme-card ">
            <p>{{ scoreTrendDesc }}</p>
            <div ref="chartARef" class="mini-chart"></div>
          </article>
        </div>
      </div>
    </section>

    <section class="section fade-in-up delay-1">
      <h3>快速入口</h3>
      <div class="mode-grid">
        <article
          v-for="mode in modes"
          :key="mode.title"
          class="quick-card theme-card"
          role="button"
          tabindex="0"
          @click="handleQuickEntry(mode.key)"
          @keydown.enter.prevent="handleQuickEntry(mode.key)"
        >
          <div class="quick-card-head">
            <h4>{{ mode.title }}</h4>
            <p>{{ mode.desc }}</p>
          </div>
        </article>
      </div>
    </section>

    <section class="main-grid fade-in-up delay-2">
      <div class="panel theme-card">
        <h3>训练日历</h3>
        <div class="calendar-placeholder">
          <p>这里放日历组件（如 Element Plus Calendar）</p>
          <ul>
            <li><span class="dot done"></span>已完成面试</li>
            <li><span class="dot plan"></span>已规划</li>
            <li><span class="dot miss"></span>待完成</li>
          </ul>
        </div>
        <div class="today-plan">
          <h4>今日计划</h4>
          <p>19:30 后端开发 · 语音面试</p>
          <p>20:10 系统设计 · 文本面试</p>
        </div>
      </div>

      <div class="panel theme-card">
        <h3>热门岗位方向</h3>
        <p class="job-tip">按岗位大类聚合统计，点击标签可进入对应方向。</p>
        <div class="job-tags">
          <button class="job-tag" v-for="job in hotCategories" :key="job.name">
            <span class="job-tag-name">{{ job.name }}</span>
            <span class="job-tag-count">{{ job.count }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import { useUserStore } from '@/store/user';
import { getUserEvaluationTrendApi } from '@/api/interviewAi';

const chartARef = ref<HTMLElement | null>(null);
let chartA: echarts.ECharts | null = null;
const router = useRouter();
const userStore = useUserStore();
const scoreList = ref<number[]>([]);
const scoreTrendDesc = computed(() => {
  if (!scoreList.value.length) return '';
  const latest = scoreList.value[scoreList.value.length - 1] ?? 0;
  return `最近一次得分：${Number(latest).toFixed(1)}`;
});

const hotCategories = [
  { name: '后端开发', count: 128 },
  { name: '前端开发', count: 103 },
  { name: 'Android开发', count: 67 },
  { name: 'iOS开发', count: 54 },
  { name: '测试开发', count: 49 },
  { name: '算法工程师', count: 73 },
  { name: '数据开发', count: 41 },
  { name: '运维开发', count: 36 },
];

const modes = [
  { key: 'ai', title: 'AI面试', desc: '智能追问与结构化反馈' },
  { key: 'avatar', title: '虚拟人面试', desc: '更接近真实面试场景' },
  { key: 'resume', title: '简历优化', desc: 'AI 诊断简历并给出优化建议' },
  { key: 'question', title: '面试押题', desc: '按岗位方向生成高频面试题' },
];

function initCharts() {
  if (!chartARef.value) return;
  chartA = echarts.init(chartARef.value);
  chartA.setOption({
    grid: { left: 8, right: 8, top: 10, bottom: 8 },
    xAxis: { type: 'category', show: false, data: ['1', '2', '3', '4', '5'] },
    yAxis: { type: 'value', show: false },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#6366f1' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 102, 241, 0.25)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.02)' },
          ]),
        },
        data: [0, 0, 0, 0, 0],
      },
    ],
  });
}

async function loadScoreTrend() {
  const userId = userStore.userInfo?.id;
  if (!userId) return;
  try {
    const trend = await getUserEvaluationTrendApi(userId);
    const yData = Array.isArray(trend?.series?.[0]?.data) ? trend.series![0]!.data! : [];
    const scores = yData.map((n) => Number(n) || 0).slice(-8);
    scoreList.value = scores;
    const xData = scores.map((_v, i) => String(i + 1));
    chartA?.setOption({
      xAxis: { data: xData.length ? xData : ['1', '2', '3', '4', '5'] },
      series: [{ data: scores.length ? scores : [0, 0, 0, 0, 0] }],
    });
  } catch {
    scoreList.value = [];
  }
}

function resizeCharts() {
  chartA?.resize();
}

function goInterviewSettings() {
  router.push({ name: 'HomeInterview' });
}

function handleQuickEntry(key: string) {
  if (key === 'ai') {
    router.push({ name: 'HomeInterviewType', query: { mode: 'text' } });
    return;
  }
  if (key === 'avatar') {
    router.push({ name: 'HomeInterviewType', query: { mode: 'avatar' } });
    return;
  }
  if (key === 'resume') {
    router.push({ name: 'HomeResumeOptimize' });
    return;
  }
  if (key === 'question') {
    router.push({ name: 'HomeQuestion' });
  }
}

onMounted(() => {
  initCharts();
  void loadScoreTrend();
  window.addEventListener('resize', resizeCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts);
  chartA?.dispose();
});
</script>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: 1.1fr 1.3fr;
  gap: clamp(10px, 1vw, 14px);
  margin-bottom: clamp(12px, 1.1vw, 16px);
  align-items: stretch;
  min-height: clamp(200px, 22vw, 220px);
}
.hero-left, .panel { padding: clamp(10px, 0.9vw, 14px); }
.hero-left {
  height: 100%;
  margin: 0 !important;
  box-sizing: border-box;
  overflow: auto;
}
.hero-right {
  height: 100%;
  margin: 0 !important;
  box-sizing: border-box;
  display: grid;
  min-height: 0;
}
.hero-left h1 { margin: 0 0 10px; font-size: clamp(22px, 2vw, 30px); }
.hero-left p { margin: 0 0 14px; color: #4b5563; font-size: clamp(13px, 1vw, 15px); }
.kpi-title { font-size: clamp(12px, 0.9vw, 13px); color: #6b7280; margin-bottom: 10px; }
.kpi-variants {
  display: grid;
  gap: 10px;
  width: 100%;
  height: 100%;
}
.kpi-card {
  padding: clamp(8px, 0.8vw, 10px);
  height: 100%;
  margin: 0 !important;
  min-height: 0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  overflow: visible;
}
.kpi-card h4 { margin: 0 0 4px; font-size: clamp(13px, 1vw, 15px); }
.kpi-card p { margin: 0 0 8px; color: #6b7280; font-size: clamp(12px, 0.9vw, 13px); }
.mini-chart { flex: 1; min-height: clamp(40px, 3.6vw, 56px); }
.section {
  margin-bottom: clamp(12px, 1.2vw, 18px);
  padding-top: clamp(4px, 0.5vw, 8px);
}
.section h3,
.panel h3 {
  margin: 0;
}
.section h3 {
  margin-bottom: clamp(10px, 0.9vw, 14px);
  line-height: 1.25;
}
.mode-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: clamp(10px, 1vw, 14px); }

.quick-card {
  margin: 0 !important;
  padding: clamp(14px, 1.1vw, 18px) clamp(12px, 1vw, 16px);
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 55%, #f3f4f6 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0;
  min-height: clamp(100px, 9vw, 120px);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  outline: none;
}
.quick-card:hover {
  border-color: #c4b5fd;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
  transform: translateY(-2px);
}
.quick-card:focus-visible {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.2);
}
.quick-card-head h4 {
  margin: 0 0 6px;
  font-size: clamp(15px, 1.1vw, 17px);
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.02em;
}
.quick-card-head p {
  margin: 0;
  color: #6b7280;
  font-size: clamp(12px, 0.9vw, 13px);
  line-height: 1.55;
}
.main-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: clamp(12px, 1.2vw, 18px); }
.calendar-placeholder { background: #fafafa; border: 1px dashed #d1d5db; border-radius: 10px; padding: clamp(10px, 1vw, 14px); }
.calendar-placeholder ul { margin: 8px 0 0; padding-left: 0; list-style: none; }
.calendar-placeholder li { margin: 6px 0; font-size: clamp(12px, 0.9vw, 13px); color: #4b5563; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.done { background: #10b981; }
.plan { background: #3b82f6; }
.miss { background: #f59e0b; }
.today-plan h4 { margin: 14px 0 8px; }
.today-plan p { margin: 0 0 6px; color: #4b5563; font-size: clamp(13px, 1vw, 14px); }
.job-tip { margin: 0 0 10px; color: #6b7280; font-size: clamp(12px, 0.9vw, 13px); }
.job-tags { display: flex; flex-wrap: wrap; gap: clamp(8px, 0.8vw, 12px); }
.job-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #ddd6fe;
  border-radius: 10px;
  padding: clamp(6px, 0.7vw, 8px) clamp(10px, 1vw, 14px);
  background: #f5f3ff;
  color: #5b21b6;
  cursor: pointer;
  transition: all 0.2s ease;
}
.job-tag:hover { background: #ede9fe; border-color: #c4b5fd; transform: translateY(-1px); }
.job-tag-name { font-size: clamp(12px, 0.9vw, 13px); font-weight: 600; }
.job-tag-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: clamp(18px, 1.4vw, 22px);
  height: clamp(18px, 1.4vw, 22px);
  border-radius: 6px;
  font-size: clamp(11px, 0.8vw, 12px);
  background: #7c3aed;
  color: #fff;
  padding: 0 6px;
}

/* 与 constants/breakpoints.ts MOBILE_MAX_WIDTH_PX 保持一致 */
@media (max-width: 768px) {
  .mode-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .hero,
  .main-grid {
    grid-template-columns: 1fr;
  }
  .hero {
    max-height: none;
    overflow: visible;
  }
  .hero-left,
  .hero-right,
  .kpi-card {
    overflow: visible;
  }
}
</style>
