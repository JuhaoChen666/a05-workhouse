<template>
  <div class="profile-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">个人信息</h2>
      <div class="theme-section-decoration"></div>
    </div>

    <!-- 用户资料卡片：头像 + 基本信息 -->
    <el-card class="section-card profile-card theme-card fade-in-up delay-1" shadow="hover">
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

    <el-row :gutter="16">
      <!-- 用户评分趋势图 -->
      <el-col :span="12">
        <el-card class="section-card theme-card fade-in-up delay-1" shadow="hover">
          <template #header><span>用户评分趋势</span></template>
          <div ref="lineChartRef" class="chart" style="height: 220px;"></div>
        </el-card>
      </el-col>

      <!-- 能力雷达图 -->
      <el-col :span="12">
        <el-card class="section-card theme-card fade-in-up delay-2" shadow="hover">
          <template #header><span>能力雷达图</span></template>
          <div ref="radarChartRef" class="chart" style="height: 220px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近面试记录 + 链接查看全部 -->
    <el-card class="section-card theme-card fade-in-up delay-2" shadow="hover">
      <template #header>
        <span>最近面试记录</span>
        <el-button type="primary" link style="float: right;" @click="goAllRecords">查看全部面试记录</el-button>
      </template>
      <el-table v-loading="listLoading" :data="recentRecords" stripe max-height="320">
        <el-table-column prop="session_id" label="会话ID" min-width="240" show-overflow-tooltip />
        <el-table-column label="岗位" min-width="140">
          <template #default="{ row }">{{ row.position_name || row.position || '--' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="开始时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ row.updated_at ? formatDateTime(row.updated_at) : '--' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="onRecordClick(row)">
              {{ row.status === 'completed' ? '查看报告' : '继续面试' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as echarts from 'echarts';
import { getProfileApi } from '@/api/auth';
import {
  getUserEvaluationTrendApi,
  getSessionEvaluationRadarApi,
  getUserInterviewSessionsPageApi,
  endInterviewSessionApi,
  type SessionEvaluationRadarData,
  type UserInterviewSessionItem,
} from '@/api/interviewAi';
import { apiOrigin } from '@/api/request';
import type { UserInfo } from '@/types/auth';
import { useUserStore } from '@/store/user';

const router = useRouter();
const userStore = useUserStore();

const profile = ref<UserInfo | null>(null);
const listLoading = ref(false);
const recentRecords = ref<UserInterviewSessionItem[]>([]);
const lineChartRef = ref<HTMLElement | null>(null);
const radarChartRef = ref<HTMLElement | null>(null);

const avatarFullUrl = computed(() => {
  const url = profile.value?.avatarUrl ?? userStore.userInfo?.avatarUrl;
  if (!url) return '';
  return url.startsWith('http') ? url : apiOrigin + url;
});

function formatDateTime(iso: string) {
  if (!iso) return '--';
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

async function loadProfile() {
  try {
    const res = await getProfileApi();
    profile.value = res;
    if (res?.avatarUrl) userStore.setUserInfo({ ...userStore.userInfo!, avatarUrl: res.avatarUrl });
  } catch (e: any) {
    ElMessage.error(e.message || '获取用户信息失败');
  }
}

async function fetchRecentRecords() {
  const userId = userStore.userInfo?.id;
  if (!userId) return;
  listLoading.value = true;
  try {
    const res = await getUserInterviewSessionsPageApi(userId, { page: 1, pageSize: 5 });
    recentRecords.value = res.list ?? [];
  } catch (e: any) {
    ElMessage.error(e.message || '获取面试报告记录失败');
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

async function onRecordClick(row: UserInterviewSessionItem) {
  const sid = String(row.session_id || '').trim();
  if (!sid) return;
  const job = (row.position_name || row.position || '').trim();
  if (row.status === 'completed') {
    router.push({
      name: 'InterviewEvaluation',
      params: { sessionId: sid },
      query: { jobName: job || undefined },
    });
    return;
  }
  try {
    await ElMessageBox.confirm('该面试尚未完成。你可以继续当前会话，或直接结束本次面试。', '面试未完成', {
      confirmButtonText: '继续面试',
      cancelButtonText: '结束面试',
      distinguishCancelAndClose: true,
      type: 'warning',
    });
    router.push({
      name: 'InterviewSession',
      params: { id: sid },
      query: {
        sessionId: sid,
        jobName: job || undefined,
        fromRecord: '1',
      },
    });
  } catch (e) {
    if (e !== 'cancel') return;
    try {
      await endInterviewSessionApi(sid);
      ElMessage.success('已结束本次面试');
      await fetchRecentRecords();
    } catch (err: unknown) {
      ElMessage.error((err as Error).message || '结束面试失败');
    }
  }
}

function initLineChart() {
  if (!lineChartRef.value) return;
  const chart = echarts.init(lineChartRef.value);
  const userId = userStore.userInfo?.id;
  if (!userId) {
    chart.setOption({ title: { text: '暂无数据', left: 'center' } });
    return;
  }
  getUserEvaluationTrendApi(userId)
    .then((res) => {
      const xData = res?.xAxis?.data ?? [];
      const yData = res?.series?.[0]?.data ?? [];
      chart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: xData },
        yAxis: { type: 'value', name: '评分' },
        series: [{ name: '评分', type: 'line', data: yData, smooth: true, showSymbol: true }],
      });
    })
    .catch(() => {
      chart.setOption({ title: { text: '暂无数据', left: 'center' } });
    });
}

function initRadarChart() {
  if (!radarChartRef.value) return;
  const chart = echarts.init(radarChartRef.value);
  const userId = userStore.userInfo?.id;
  if (!userId) {
    chart.setOption({ title: { text: '暂无可用会话', left: 'center' } });
    return;
  }
  const applyRadar = (data: SessionEvaluationRadarData) => {
    let indicator = (data.indicator || [])
      .map((i) => ({ name: String(i.name || '').trim(), max: Number(i.max ?? 100) || 100 }))
      .filter((i) => i.name);
    let values = (data.value || []).map((v) => Number(v) || 0);

    if ((!indicator.length || !values.length) && data.radar && !Array.isArray(data.radar)) {
      indicator = (data.radar.indicator || [])
        .map((i) => ({ name: String(i.name || '').trim(), max: Number(i.max ?? 100) || 100 }))
        .filter((i) => i.name);
    }
    if ((!indicator.length || !values.length) && Array.isArray(data.radar) && data.radar.length) {
      indicator = data.radar
        .map((r) => ({ name: String(r.name || '').trim(), max: Number(r.max ?? 100) || 100 }))
        .filter((i) => i.name);
      values = data.radar.map((r) => Number(r.value ?? 0) || 0);
    }
    if (
      !values.length &&
      Array.isArray(data.series) &&
      Array.isArray(data.series[0]?.data) &&
      data.series[0]!.data![0]?.value?.length
    ) {
      values = data.series[0]!.data![0]!.value!.map((v) => Number(v) || 0);
    }
    if (!values.length && Array.isArray(data.series) && data.series[0]?.value?.length) {
      values = data.series[0].value!.map((v) => Number(v) || 0);
    }
    if (!indicator.length || !values.length) {
      chart.setOption({ title: { text: '暂无雷达图数据', left: 'center' } });
      return;
    }
    chart.setOption({
      tooltip: {},
      radar: { indicator },
      series: [{ type: 'radar', data: [{ value: values, name: '能力评估' }] }],
    });
  };

  getUserInterviewSessionsPageApi(userId, { page: 1, pageSize: 20 })
    .then(async (res) => {
      const latestCompleted = (res.list || []).find((it) => it.status === 'completed');
      if (!latestCompleted?.session_id) {
        chart.setOption({ title: { text: '暂无已完成面试', left: 'center' } });
        return;
      }
      const radarData = await getSessionEvaluationRadarApi(latestCompleted.session_id);
      applyRadar(radarData);
    })
    .catch(() => {
      chart.setOption({ title: { text: '雷达图加载失败', left: 'center' } });
    });
}

onMounted(() => {
  loadProfile();
  fetchRecentRecords();
  setTimeout(() => {
    initLineChart();
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
.section-card { margin-bottom: 16px; }
.chart { width: 100%; }
</style>
