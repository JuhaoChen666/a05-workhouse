<template>
  <section class="hero fade-in-up delay-1">
    <div class="hero-left theme-card">
      <h1>今天开始一次高质量模拟面试</h1>
      <p>选择岗位方向与面试模式，10 秒进入训练。</p>
      <el-button type="primary" class="theme-primary-btn">立即开始面试</el-button>
    </div>
    <div class="hero-right">
      <div class="kpi-title">右上角数据卡片</div>
      <div class="kpi-variants">
        <article class="kpi-card theme-card">
          <h4>本周进度概览</h4>
          <p>本周完成 2 / 5</p>
          <div ref="chartARef" class="mini-chart"></div>
        </article>
      </div>
    </div>
  </section>

  <section class="section fade-in-up delay-1">
    <h3>快速入口</h3>
    <div class="mode-grid">
      <article class="card theme-card" v-for="mode in modes" :key="mode.title">
        <h4>{{ mode.title }}</h4>
        <p>{{ mode.desc }}</p>
        <el-button>开始</el-button>
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
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';

const chartARef = ref<HTMLElement | null>(null);
let chartA: echarts.ECharts | null = null;

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
  { title: 'AI面试', desc: '智能追问与结构化反馈' },
  { title: '虚拟人面试', desc: '更接近真实面试场景' },
  { title: '简历优化', desc: 'AI 诊断简历并给出优化建议' },
  { title: '面试押题', desc: '按岗位方向生成高频面试题' },
];

function initCharts() {
  if (!chartARef.value) return;
  chartA = echarts.init(chartARef.value);
  chartA.setOption({
    grid: { left: 6, right: 6, top: 6, bottom: 6 },
    xAxis: { type: 'category', show: false, data: ['一', '二', '三', '四', '五'] },
    yAxis: { type: 'value', show: false },
    series: [{ type: 'line', smooth: true, symbol: 'none', data: [2, 3, 1, 4, 2], areaStyle: {} }],
  });
}

function resizeCharts() {
  chartA?.resize();
}

onMounted(() => {
  initCharts();
  window.addEventListener('resize', resizeCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts);
  chartA?.dispose();
});
</script>

<style scoped>
.hero { display: grid; grid-template-columns: 1.1fr 1.3fr; gap: 16px; margin-bottom: 16px; }
.hero-left, .hero-right, .panel, .card { padding: 16px; }
.hero-left h1 { margin: 0 0 10px; font-size: 28px; }
.hero-left p { margin: 0 0 14px; color: #4b5563; }
.kpi-title { font-size: 13px; color: #6b7280; margin-bottom: 10px; }
.kpi-variants { display: grid; gap: 10px; }
.kpi-card { padding: 12px; }
.kpi-card h4 { margin: 0 0 4px; font-size: 14px; }
.kpi-card p { margin: 0 0 8px; color: #6b7280; font-size: 12px; }
.mini-chart { height: 62px; }
.section { margin-bottom: 16px; }
.section h3, .panel h3 { margin-top: 0; }
.mode-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.card h4 { margin: 0 0 8px; }
.card p { margin: 0 0 12px; color: #6b7280; font-size: 13px; }
.main-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; }
.calendar-placeholder { background: #fafafa; border: 1px dashed #d1d5db; border-radius: 10px; padding: 12px; }
.calendar-placeholder ul { margin: 8px 0 0; padding-left: 0; list-style: none; }
.calendar-placeholder li { margin: 6px 0; font-size: 13px; color: #4b5563; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.done { background: #10b981; }
.plan { background: #3b82f6; }
.miss { background: #f59e0b; }
.today-plan h4 { margin: 14px 0 8px; }
.today-plan p { margin: 0 0 6px; color: #4b5563; font-size: 14px; }
.job-tip { margin: 0 0 10px; color: #6b7280; font-size: 13px; }
.job-tags { display: flex; flex-wrap: wrap; gap: 10px; }
.job-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #ddd6fe;
  border-radius: 10px;
  padding: 7px 12px;
  background: #f5f3ff;
  color: #5b21b6;
  cursor: pointer;
  transition: all 0.2s ease;
}
.job-tag:hover { background: #ede9fe; border-color: #c4b5fd; transform: translateY(-1px); }
.job-tag-name { font-size: 13px; font-weight: 600; }
.job-tag-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  border-radius: 6px;
  font-size: 12px;
  background: #7c3aed;
  color: #fff;
  padding: 0 6px;
}
</style>
