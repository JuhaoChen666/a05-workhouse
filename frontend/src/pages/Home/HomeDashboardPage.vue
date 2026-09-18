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
      <div class="panel theme-card intelligence-panel">
        <div class="intel-header">
          <h3>🔥 实时面试情报局</h3>
          <span class="live-badge">LIVE</span>
        </div>
        <p class="job-tip">全网高频考点追踪，掌握最新面试风向标</p>
        
        <div class="intel-viewport">
          <div class="intel-scroll-track">
            <template v-for="loop in 2" :key="loop">
              <div class="intel-item" v-for="(item, idx) in intelligenceList" :key="idx">
                <span class="intel-time">{{ item.time }}</span>
                <span :class="['intel-tag', item.type]">{{ item.tag }}</span>
                <span class="intel-text">{{ item.text }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="panel theme-card">
        <h3>热门岗位方向</h3>
        <p class="job-tip">按岗位大类聚合统计，点击标签可查看完整的岗位招聘内容。</p>
        <div class="job-tags">
          <button class="job-tag" v-for="(job, index) in displayJobs" :key="job.id || index" @click="handleJobClick(job)">
            <span class="job-tag-name">{{ job.name }}</span>
            <span class="job-tag-count" v-if="job.companyName">
              <img v-if="getLocalCompanyLogo(job.companyName, job.companyLogo)" :src="getLocalCompanyLogo(job.companyName, job.companyLogo)" class="mini-logo" alt="logo" />
              {{ job.companyName }}
            </span>
            <span class="job-tag-count" v-else>{{ job.count }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- 职位详情弹窗 -->
    <el-dialog
      v-model="jobDialogVisible"
      :title="selectedJob?.name || '岗位详情'"
      width="600px">
      <div v-if="selectedJob" class="job-detail-content">
        <template v-if="selectedJob.companyName">
          <div class="job-header">
            <h3>{{ selectedJob.name }}</h3>
            <div class="job-meta">
              <span class="company">
                <img v-if="getLocalCompanyLogo(selectedJob.companyName, selectedJob.companyLogo)" :src="getLocalCompanyLogo(selectedJob.companyName, selectedJob.companyLogo)" class="meta-logo" alt="logo" />
                企业：{{ selectedJob.companyName }}
              </span>
              <span class="salary" v-if="selectedJob.salaryMin || selectedJob.salaryMax">
                薪资：{{ formatSalaryRange(selectedJob.salaryMin, selectedJob.salaryMax) }}
              </span>
            </div>
          </div>
          <el-divider style="margin: 16px 0;" />
          <div class="job-html" v-html="selectedJob.jobContent?.replace(/\n/g, '<br>') || '暂无详细描述'"></div>
        </template>
        <template v-else>
          <div class="job-header">
            <h3>{{ selectedJob.name }}</h3>
            <p>这是一个聚合方向的统计数据模块，具体岗位内容请确认接入真实API后体验。</p>
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import { useUserStore } from '@/store/user';
import { getUserEvaluationTrendApi } from '@/api/interviewAi';
import { getHotJobsApi, getJobDetailApi, formatSalaryRange } from '@/api/jobs';

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


const intelligenceList = ref([
  { time: '10分钟前', tag: '命中', type: 'hit', text: '有同学通过模拟训练命中了腾讯 WXG 原题！' },
  { time: '半小时前', tag: '趋势', type: 'trend', text: '过去24小时，【Redis 缓存穿透】频频被考察' },
  { time: '1小时前', tag: '高频', type: 'hot', text: '字节跳动集中考察了【React Hooks 底层原理】' },
  { time: '2小时前', tag: '趋势', type: 'trend', text: '【MySQL 索引下推】成为后端一面必问题' },
  { time: '刚刚', tag: '更新', type: 'hit', text: '系统已收录最新阿里 P6 级架构设计题解' },
]);

const displayJobs = ref<any[]>([]);
const jobDialogVisible = ref(false);
const selectedJob = ref<any>(null);

function getLocalCompanyLogo(name?: string, fallbackUrl?: string) {
  if (!name) return fallbackUrl || '';
  const n = name.toLowerCase();
  if (n.includes('阿里') || n.includes('alibaba')) return '/img/Alibaba.ico';
  if (n.includes('字节') || n.includes('bytedance')) return '/img/ByteDance.ico';
  if (n.includes('华为') || n.includes('huawei')) return '/img/Huawei.ico';
  if (n.includes('美团') || n.includes('meituan')) return '/img/Meituan.ico';
  if (n.includes('腾讯') || n.includes('tencent')) return '/img/Tencent.ico';
  if (n.includes('网易') || n.includes('wangyi')) return '/img/Wangyi.ico';
  return fallbackUrl || '';
}

async function loadJobTags() {
  try {
    const list = await getHotJobsApi({ limit: 12 });
    if (list && list.length > 0) {
      displayJobs.value = list;
    }
  } catch (err) {
    console.error('Failed to load hot jobs', err);
  }
}

async function handleJobClick(job: any) {
  selectedJob.value = job;
  jobDialogVisible.value = true;
  if (job.id) {
    try {
      const detail = await getJobDetailApi(job.id);
      if (detail) {
        selectedJob.value = { ...job, ...detail };
      }
    } catch (err) {
      console.error('Failed to fetch job detail', err);
    }
  }
}

const modes = [
  { key: 'ai', title: 'AI面试', desc: '智能追问与结构化反馈' },
  { key: 'avatar', title: '虚拟人面试', desc: '更接近真实面试场景' },
  { key: 'resume', title: '简历优化', desc: 'AI 诊断简历并给出优化建议' },
  { key: 'question', title: 'AI押题', desc: '按岗位方向生成高频面试题' },
];

function initCharts() {
  if (!chartARef.value) return;
  chartA = echarts.init(chartARef.value);
  chartA.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      textStyle: { color: '#374151', fontSize: 13 },
      formatter: '{b} <br/> 综合评分: <b style="color: #6366f1">{c}</b>'
    },
    grid: { left: 35, right: 20, top: 45, bottom: 30 },
    xAxis: {
      type: 'category',
      show: true,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { color: '#9ca3af', fontSize: 11, margin: 8 },
      data: ['1', '2', '3', '4', '5']
    },
    yAxis: {
      type: 'value',
      show: true,
      splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } },
      axisLabel: { color: '#9ca3af', fontSize: 11 }
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#6366f1', borderWidth: 2, borderColor: '#fff' },
        lineStyle: { width: 3, color: '#6366f1', shadowColor: 'rgba(99, 102, 241, 0.2)', shadowBlur: 10 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.0)' },
          ]),
        },
        markPoint: {
          data: [{ type: 'max', name: '最高分' }],
          label: { color: '#fff', fontSize: 10 },
          itemStyle: { color: '#fbbf24' }
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
    
    const xDataRaw = Array.isArray(trend?.xAxis?.data) ? trend.xAxis!.data! : [];
    const formattedDates = xDataRaw.slice(-8).map((d: string) => {
      const parts = d.split('-');
      return parts.length >= 3 ? `${parts[1]}-${parts[2]}` : d;
    });

    const xData = formattedDates.length === scores.length ? formattedDates : scores.map((_v, i) => String(i + 1));
    
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
    router.push({ name: 'HomeResumeGeneration' });
    return;
  }
  if (key === 'question') {
    router.push({ name: 'HomeQuestion' });
  }
}

onMounted(() => {
  initCharts();
  void loadScoreTrend();
  void loadJobTags();
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
  min-height: clamp(250px, 28vw, 300px);
}

.panel {
  padding: clamp(8px, 0.75vw, 12px) clamp(10px, 0.9vw, 14px) clamp(12px, 0.95vw, 15px)
    clamp(8px, 0.75vw, 12px);
}

.hero-left {
  /* 上、右、下、左：略收紧左上，内容视觉上靠左上一些 */
  padding: clamp(12px, 1.8vw, 22px) clamp(18px, 2.8vw, 38px) clamp(22px, 3.2vw, 42px)
    clamp(14px, 2.2vw, 28px);
  height: 100%;
  margin: 0 !important;
  box-sizing: border-box;
  overflow: auto;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  width: 100%;
  min-width: 0;
}

.hero-left > .theme-primary-btn {
  align-self: flex-start;
}
.hero-right {
  height: 100%;
  margin: 0 !important;
  box-sizing: border-box;
  display: grid;
  min-height: 0;
}
.hero-left h1 { margin: 0 0 12px; font-size: clamp(22px, 2.5vw, 33px); line-height: 1.3; }
.hero-left p { margin: 0 0 24px; color: #4b5563; font-size: clamp(14px, 1.2vw, 16px); line-height: 1.5; }
.kpi-title { font-size: clamp(12px, 0.9vw, 13px); color: #6b7280; margin-bottom: 10px; }
.kpi-variants {
  display: grid;
  gap: 10px;
  width: 100%;
  height: 100%;
}
.kpi-card {
  padding: clamp(6px, 0.65vw, 8px) clamp(8px, 0.8vw, 10px) clamp(10px, 0.85vw, 12px)
    clamp(6px, 0.65vw, 8px);
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
.mini-chart { flex: 1; min-height: clamp(130px, 11vw, 160px); }
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

.job-header h3 {
  margin: 0 0 10px 0;
  font-size: clamp(16px, 1.2vw, 20px);
  color: #111827;
}
.job-meta {
  display: flex;
  gap: 15px;
  font-size: clamp(12px, 0.9vw, 14px);
}
.mini-logo {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  margin-right: 4px;
  object-fit: cover;
}
.meta-logo {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  margin-right: 6px;
  object-fit: cover;
}
.job-meta .company {
  display: inline-flex;
  align-items: center;
  font-weight: 500;
  color: #374151;
}
.job-meta .salary {
  color: #f59e0b;
  font-weight: bold;
}
.job-html {
  font-size: clamp(13px, 1vw, 15px);
  line-height: 1.6;
  color: #4b5563;
  word-break: break-all;
}

.intelligence-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.intel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.intel-header h3 {
  margin: 0;
  color: #ef4444;
}
.live-badge {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #f87171;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 800;
  border-radius: 4px;
  letter-spacing: 1px;
  animation: pulse-live 2s infinite;
}
@keyframes pulse-live {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}
.intel-viewport {
  flex: 1;
  margin-top: 10px;
  background: #fbfbfa;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  border: 1px solid #e5e7eb;
}
.intel-viewport::before, .intel-viewport::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 2;
  pointer-events: none;
}
.intel-viewport::before { top: 0; background: linear-gradient(to bottom, #fbfbfa, transparent); }
.intel-viewport::after { bottom: 0; background: linear-gradient(to top, #fbfbfa, transparent); }
.intel-scroll-track {
  animation: scroll-up 15s linear infinite;
}
.intel-scroll-track:hover {
  animation-play-state: paused;
}
@keyframes scroll-up {
  0% { transform: translateY(0); }
  100% { transform: translateY(-50%); } 
}
.intel-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px dashed #e5e7eb;
  font-size: clamp(12px, 0.9vw, 13px);
  color: #374151;
  transition: background 0.2s;
  cursor: default;
}
.intel-item:hover { background: #f3f4f6; }
.intel-time {
  color: #9ca3af;
  font-size: 11px;
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}
.intel-tag {
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-top: 2px;
}
.intel-tag.hit { background: #dcfce7; color: #166534; }
.intel-tag.trend { background: #e0e7ff; color: #3730a3; }
.intel-tag.hot { background: #fee2e2; color: #991b1b; }
.intel-text { line-height: 1.5; }

@media (max-width: 1200px) {
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
