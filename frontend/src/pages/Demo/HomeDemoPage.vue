<template>
  <div class="home-demo-shell">
    <aside
      class="demo-sidebar"
      :class="{ collapsed: !sidebarExpanded }"
      @mouseenter="sidebarExpanded = true"
      @mouseleave="sidebarExpanded = false"
    >
      <div class="sidebar-top">
        <el-icon class="collapse-icon"><Fold /></el-icon>
      </div>

      <nav class="menu-list">
        <button
          v-for="item in menuItems"
          :key="item.key"
          class="menu-item"
          :class="{ active: activeMenu === item.key }"
          @click="activeMenu = item.key"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="sidebarExpanded">{{ item.label }}</span>
        </button>
      </nav>
    </aside>

    <div class="demo-main theme-page-shell">
      <div class="theme-section-header fade-in-up">
        <h2 class="theme-section-title">{{ pageHeaderText }} <span>{{ pageSubtitle }}</span></h2>
        <div class="theme-section-decoration"></div>
      </div>

      <template v-if="activeMenu === 'home'">
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

      <section v-else-if="activeMenu === 'resume'" class="resume-page fade-in-up delay-1">
        <div class="resume-toolbar theme-card">
          <p>支持上传、在线编辑与管理。</p>
          <div class="resume-upload-area">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              accept=".pdf,application/pdf"
              :on-change="handleResumeFileChange"
            >
              <el-button type="primary" class="theme-primary-btn">上传简历</el-button>
            </el-upload>
            <span class="resume-upload-tip">仅支持 PDF 格式文件</span>
          </div>
        </div>

        <el-table :data="resumeList" stripe>
          <el-table-column prop="name" label="文件名" min-width="280" show-overflow-tooltip />
          <el-table-column prop="updatedAt" label="更新时间" width="180" />
          <el-table-column prop="content" label="摘要">
            <template #default="{ row }">
              {{ row.content.slice(0, 60) || '暂无内容' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" @click="removeResume(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="resumeList.length === 0" description="暂无简历，请先上传" :image-size="72" />
      </section>

      <section v-else class="placeholder-page theme-card fade-in-up delay-1">
        <h3>{{ currentPageTitle }}（占位页面）</h3>
        <p>{{ currentPageDesc }}</p>
        <el-button type="primary" class="theme-primary-btn">开发中</el-button>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue';
import * as echarts from 'echarts';
import { HomeFilled, Collection, Document, Suitcase, Notebook, Fold } from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';
import { ElMessage } from 'element-plus';

const userStore = useUserStore();
const sidebarExpanded = ref(false);
const activeMenu = ref('home');
const menuItems = [
  { key: 'home', label: '首页', icon: HomeFilled },
  { key: 'question', label: '题库', icon: Collection },
  { key: 'resume', label: '简历', icon: Document },
  { key: 'job', label: '岗位', icon: Suitcase },
  { key: 'docs', label: '帮助文档', icon: Notebook },
];

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

const menuPageMeta: Record<string, { subtitle: string; title: string; desc: string }> = {
  home: { subtitle: 'Dashboard', title: '首页', desc: '首页看板内容展示。' },
  question: { subtitle: 'Question Bank', title: '题库', desc: '题库页面占位：后续可接筛选、分类与练习入口。' },
  resume: { subtitle: 'Resume', title: '简历列表', desc: '简历页面占位：后续可接上传、解析与优化建议。' },
  job: { subtitle: 'Jobs', title: '岗位', desc: '岗位页面占位：后续可接岗位列表、热度和推荐。' },
  docs: { subtitle: 'Docs', title: '帮助文档', desc: '帮助文档占位：后续可接使用指南、FAQ 与操作说明。' },
};

const pageSubtitle = computed(() => menuPageMeta[activeMenu.value]?.subtitle || 'Dashboard');
const currentPageTitle = computed(() => menuPageMeta[activeMenu.value]?.title || '页面');
const currentPageDesc = computed(() => menuPageMeta[activeMenu.value]?.desc || '页面建设中');
const APP_TITLE = 'AI 模拟面试平台';
type ResumeItem = { id: number; name: string; content: string; updatedAt: string };
const resumeList = ref<ResumeItem[]>([]);

const greetingText = computed(() => {
  const hour = new Date().getHours();
  const username = userStore.userInfo?.username || '同学';
  let greet = '早上好! ';
  if (hour >= 12 && hour < 23) greet = '中午好! ';
  if (hour >= 23 || hour < 5) greet = '还不睡觉吗? ';
  return `${greet} ${username}`;
});

const pageHeaderText = computed(() => (activeMenu.value === 'home' ? greetingText.value : currentPageTitle.value));

function initCharts() {
  if (chartARef.value) {
    chartA = echarts.init(chartARef.value);
    chartA.setOption({
      grid: { left: 6, right: 6, top: 6, bottom: 6 },
      xAxis: { type: 'category', show: false, data: ['一', '二', '三', '四', '五'] },
      yAxis: { type: 'value', show: false },
      series: [{ type: 'line', smooth: true, symbol: 'none', data: [2, 3, 1, 4, 2], areaStyle: {} }],
    });
  }
}

function resizeCharts() {
  chartA?.resize();
}

function nowText() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function handleResumeFileChange(file: { name?: string; raw?: File }) {
  const raw = file.raw;
  const filename = String(file?.name || '').trim().toLowerCase();
  const isPdf = filename.endsWith('.pdf') || raw?.type === 'application/pdf';
  if (!isPdf) {
    ElMessage.error('仅支持上传 PDF 格式简历');
    return;
  }
  const name = String(file?.name || '').trim() || '未命名简历';
  const item: ResumeItem = {
    id: Date.now(),
    name,
    content: `来自上传文件：${name}\n（Demo：此处可接入解析后的简历内容）`,
    updatedAt: nowText(),
  };
  resumeList.value.unshift(item);
  ElMessage.success('简历已添加到列表');
}

function removeResume(id: number) {
  resumeList.value = resumeList.value.filter((r) => r.id !== id);
  ElMessage.success('简历已删除');
}

onMounted(() => {
  initCharts();
  window.addEventListener('resize', resizeCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts);
  chartA?.dispose();
});

watch(
  currentPageTitle,
  (title) => {
    document.title = `${title} - ${APP_TITLE}`;
  },
  { immediate: true }
);
</script>

<style scoped>
.home-demo-shell {
  position: relative;
  min-height: calc(100vh - 120px);
  padding-left: 64px; /* 预留收起侧栏宽度，展开时覆盖不挤压主内容 */
}
.demo-sidebar {
  position:fixed;
  left: 0;
  top: 10%;
  bottom: 10%;
  z-index: 20;
  width: 80px;
  background: linear-gradient(180deg, #f8fafc, #f1f5f9);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  color: #475569;
  padding: 10px 8px;
  transition: width 0.22s ease, box-shadow 0.22s ease;
  overflow: hidden;
}
.demo-sidebar:hover {
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}
.demo-sidebar.collapsed { width: 52px; }
.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.collapse-icon { color: #94a3b8; }
.menu-list { display: grid; gap: 8px; }
.menu-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #475569;
  padding: 10px 6px;
  min-height: 56px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.menu-item span {
  font-size: 12px;
  line-height: 1.1;
}
.demo-sidebar.collapsed .menu-item {
  min-height: 44px;
  padding: 8px 4px;
}
.menu-item:hover { background: #eef2ff; color: #4338ca; }
.menu-item.active {
  background: linear-gradient(90deg, #ede9fe, #dbeafe);
  border-color: #c4b5fd;
  color: #4338ca;
}

.demo-main { color: #1f2937; flex: 1; min-width: 0; }
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
.job-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
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
.job-tag:hover {
  background: #ede9fe;
  border-color: #c4b5fd;
  transform: translateY(-1px);
}
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
.placeholder-page {
  padding: 28px;
}
.placeholder-page h3 {
  margin: 0 0 10px;
  font-size: 22px;
}
.placeholder-page p {
  margin: 0 0 16px;
  color: #6b7280;
  line-height: 1.7;
}
.resume-page {
  display: grid;
  gap: 14px;
}
.resume-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
}
.resume-toolbar h3 {
  margin: 0 0 6px;
}
.resume-toolbar p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}
.resume-upload-area {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.resume-upload-tip {
  font-size: 12px;
  color: #909399;
}
</style>
