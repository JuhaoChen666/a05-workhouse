<template>
  <div class="profile-page">
    <h2 class="page-title">个人中心</h2>

    <!-- 用户资料卡片：头像 + 基本信息 -->
    <el-card class="section-card profile-card" shadow="hover">
      <template #header>
        <span>用户资料</span>
        <el-button type="primary" link style="float: right;" @click="goAccountSettings">
          账号与安全设置
        </el-button>
      </template>
      <div class="profile-header">
        <div class="avatar-area">
          <el-avatar :size="80" :src="avatarFullUrl" class="avatar">
            {{ profile?.username?.slice(0, 2) || '?' }}
          </el-avatar>
        </div>
        <div class="profile-form" v-if="profile">
          <el-form label-width="80px">
            <el-form-item label="用户名">{{ profile.username }}</el-form-item>
            <el-form-item label="邮箱">{{ profile.email || '未绑定' }}</el-form-item>
            <el-form-item label="角色">{{ profile.roleName ?? '普通用户' }}</el-form-item>
          </el-form>
        </div>
      </div>
    </el-card>

    <!-- 数据统计面板 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.totalCount }}</div>
          <div class="stat-label">总面试次数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.avgScore ?? '--' }}</div>
          <div class="stat-label">平均得分</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.finishedCount }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.lastAt ? formatDate(stats.lastAt) : '--' }}</div>
          <div class="stat-label">最近面试</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近几次面试分数 - 折线图 -->
    <el-card class="section-card" shadow="hover">
      <template #header><span>最近面试得分趋势</span></template>
      <div ref="lineChartRef" class="chart" style="height: 260px;"></div>
    </el-card>

    <!-- 能力分析：柱状图 + 雷达图 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card class="section-card" shadow="hover">
          <template #header><span>能力分析（柱状图）</span></template>
          <div ref="barChartRef" class="chart" style="height: 280px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="section-card" shadow="hover">
          <template #header><span>能力分析（六边形雷达图）</span></template>
          <div ref="radarChartRef" class="chart" style="height: 280px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近几次面试记录 + 链接查看全部 -->
    <el-card class="section-card" shadow="hover">
      <template #header>
        <span>最近面试记录</span>
        <el-button type="primary" link style="float: right;" @click="goAllRecords">查看全部面试记录</el-button>
      </template>
      <el-table v-loading="listLoading" :data="recentRecords" stripe max-height="320">
        <el-table-column prop="positionName" label="岗位" width="120" />
        <el-table-column prop="startedAt" label="开始时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.startedAt) }}</template>
        </el-table-column>
        <el-table-column prop="endedAt" label="结束时间" width="170">
          <template #default="{ row }">{{ row.endedAt ? formatDateTime(row.endedAt) : '--' }}</template>
        </el-table-column>
        <el-table-column prop="totalScore" label="得分" width="80">
          <template #default="{ row }">{{ row.totalScore ?? '--' }}</template>
        </el-table-column>
        <el-table-column label="报告" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="goReport(row.id)">查看报告</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { getProfileApi, changePasswordApi, uploadAvatarApi, type ChangePasswordRequest } from '@/api/auth';
import { getInterviewRecordListApi, getInterviewStatsApi, getRecentScoresApi, type InterviewRecordItem } from '@/api/interview';
import { getAbilityAnalysisApi } from '@/api/user';
import { apiOrigin } from '@/api/request';
import type { UserInfo } from '@/types/auth';
import { useUserStore } from '@/store/user';

const router = useRouter();
const userStore = useUserStore();

const profile = ref<UserInfo | null>(null);
const listLoading = ref(false);
const recentRecords = ref<InterviewRecordItem[]>([]);
const statsData = ref({ totalCount: 0, finishedCount: 0, avgScore: null as number | null, lastAt: null as string | null });
const lineChartRef = ref<HTMLElement | null>(null);
const barChartRef = ref<HTMLElement | null>(null);
const radarChartRef = ref<HTMLElement | null>(null);

const avatarFullUrl = computed(() => {
  const url = profile.value?.avatarUrl ?? userStore.userInfo?.avatarUrl;
  if (!url) return '';
  return url.startsWith('http') ? url : apiOrigin + url;
});

const stats = computed(() => ({
  totalCount: statsData.value.totalCount,
  avgScore: statsData.value.avgScore != null ? String(statsData.value.avgScore) : null,
  finishedCount: statsData.value.finishedCount,
  lastAt: statsData.value.lastAt,
}));

function formatDate(iso: string) {
  if (!iso) return '--';
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function formatDateTime(iso: string) {
  if (!iso) return '--';
  const d = new Date(iso);
  return `${formatDate(iso)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

async function loadProfile() {
  try {
    const res = await getProfileApi();
    profile.value = res as UserInfo;
    if (res && (res as UserInfo).avatarUrl) userStore.setUserInfo({ ...userStore.userInfo!, avatarUrl: (res as UserInfo).avatarUrl });
  } catch (e: any) {
    ElMessage.error(e.message || '获取用户信息失败');
  }
}

async function loadStats() {
  try {
    const res = await getInterviewStatsApi();
    statsData.value = {
      totalCount: res.totalCount ?? 0,
      finishedCount: res.finishedCount ?? 0,
      avgScore: res.avgScore ?? null,
      lastAt: res.lastAt ?? null,
    };
  } catch {}
}

async function fetchRecentRecords() {
  listLoading.value = true;
  try {
    const res = await getInterviewRecordListApi({ page: 1, pageSize: 5 });
    recentRecords.value = res.list ?? [];
    if (statsData.value.totalCount === 0 && (res.total ?? 0) > 0) {
      statsData.value.totalCount = res.total ?? 0;
      const withScore = (res.list ?? []).filter((r) => r.totalScore != null && r.endedAt);
      const sum = withScore.reduce((s, r) => s + (r.totalScore ?? 0), 0);
      statsData.value.avgScore = withScore.length ? sum / withScore.length : null;
      statsData.value.lastAt = (res.list ?? [])[0]?.startedAt ?? null;
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取面试记录失败');
  } finally {
    listLoading.value = false;
  }
}

function goAccountSettings() {
  router.push({ name: 'ProfileEdit' });
}

function goAllRecords() {
  router.push({ name: 'InterviewRecordList' });
}
function goReport(recordId: number) {
  router.push({ name: 'ReportDetail', params: { id: String(recordId) } });
}

// 折线图：最近几次面试分数
function initLineChart() {
  if (!lineChartRef.value) return;
  const chart = echarts.init(lineChartRef.value);
  getRecentScoresApi({ limit: 10 }).then((list) => {
    const data = (list ?? []).reverse();
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: data.map((d) => (d.startedAt ? formatDateTime(d.startedAt).slice(0, 16) : '')),
      },
      yAxis: { type: 'value', min: 0, max: 100, name: '得分' },
      series: [{ name: '得分', type: 'line', data: data.map((d) => d.totalScore), smooth: true }],
    });
  }).catch(() => {
    chart.setOption({ title: { text: '暂无数据', left: 'center' } });
  });
}

function initBarChart() {
  if (!barChartRef.value) return;
  const chart = echarts.init(barChartRef.value);
  getAbilityAnalysisApi().then((res) => {
    const bar = res?.bar ?? [];
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: bar.map((b) => b.name) },
      yAxis: { type: 'value', max: 100, name: '分数' },
      series: [{ type: 'bar', data: bar.map((b) => b.value) }],
    });
  }).catch(() => {
    chart.setOption({ title: { text: '暂无数据', left: 'center' } });
  });
}

function initRadarChart() {
  if (!radarChartRef.value) return;
  const chart = echarts.init(radarChartRef.value);
  getAbilityAnalysisApi().then((res) => {
    const radar = res?.radar ?? [];
    const indicator = radar.map((r) => ({ name: r.name, max: r.max ?? 100 }));
    const values = radar.map((r) => r.value);
    chart.setOption({
      tooltip: {},
      radar: { indicator },
      series: [{ type: 'radar', data: [{ value: values, name: '能力' }] }],
    });
  }).catch(() => {
    chart.setOption({ title: { text: '暂无数据', left: 'center' } });
  });
}

onMounted(() => {
  loadProfile();
  loadStats();
  fetchRecentRecords();
  setTimeout(() => {
    initLineChart();
    initBarChart();
    initRadarChart();
  }, 100);
});
</script>

<style scoped>
.profile-page { max-width: 1200px; }
.page-title { margin-top: 0; margin-bottom: 16px; }
.profile-card .profile-header { display: flex; gap: 24px; align-items: flex-start; }
.avatar-area { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.avatar-upload { margin-top: 4px; }
.profile-form { flex: 1; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 24px; font-weight: bold; color: #0d2137; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.section-card { margin-bottom: 16px; }
.chart { width: 100%; }
</style>
