<template>
  <div class="home-page">
    <!-- Banner -->
    <div class="banner">
      <h1>AI 模拟面试平台</h1>
      <p>智能面试练习，助力求职进阶</p>
      <el-button type="primary" size="large" @click="goInterview">开始模拟面试</el-button>
    </div>

    <!-- 下方两栏：左侧热门岗位 | 右侧最近报告 -->
    <el-row :gutter="20" class="main-row">
      <el-col :span="16">
        <div class="section-title">热门岗位</div>
        <el-row :gutter="16" class="job-cards">
          <el-col v-for="j in hotJobs" :key="j.id" :span="12">
            <el-card shadow="hover" class="job-card" @click="goJobDetail(j.id)">
              <div class="job-card-header">
                <span class="job-name">{{ j.name }}</span>
                <span class="company-name">{{ j.companyName }}</span>
              </div>
              <p class="job-desc">{{ (j.jobContent || '').slice(0, 60) }}...</p>
              <div class="job-salary">
                {{ (j.salaryMin / 1000).toFixed(0) }}k - {{ (j.salaryMax / 1000).toFixed(0) }}k / 月
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
      <el-col :span="8">
        <div class="section-title">最近一次面试报告</div>
        <el-card v-loading="reportLoading" shadow="hover" class="report-card">
          <template v-if="latestReport">
            <div class="report-score">综合得分：{{ latestReport.totalScore ?? '--' }} 分</div>
            <p class="report-summary">{{ latestReport.summary || '暂无总结' }}</p>
            <el-button type="primary" link @click="goReport">查看完整报告</el-button>
          </template>
          <el-empty v-else description="暂无面试报告" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getHotJobsApi, type HotJobItem } from '@/api/jobs';
import { getReportByRecordIdApi } from '@/api/report';
import { getInterviewRecordListApi } from '@/api/interview';

const router = useRouter();
const hotJobs = ref<HotJobItem[]>([]);
const reportLoading = ref(false);
const latestReport = ref<{ totalScore?: number; summary?: string } | null>(null);
const latestRecordId = ref<number | null>(null);

function goInterview() {
  router.push({ name: 'Interview' });
}
function goJobDetail(id: number) {
  router.push({ name: 'JobDetail', params: { id: String(id) } });
}
function goReport() {
  if (latestRecordId.value) router.push({ name: 'ReportDetail', params: { id: String(latestRecordId.value) } });
}

onMounted(async () => {
  try {
    const list = await getHotJobsApi({ limit: 6 });
    hotJobs.value = list ?? [];
  } catch {}

  reportLoading.value = true;
  try {
    const listRes = await getInterviewRecordListApi({ page: 1, pageSize: 1 });
    const first = (listRes.list ?? [])[0];
    if (first?.id) {
      latestRecordId.value = first.id;
      const rep = await getReportByRecordIdApi(first.id);
      if (rep?.content) {
        latestReport.value = {
          totalScore: rep.content.totalScore,
          summary: rep.content.summary,
        };
      }
    }
  } catch {
    latestReport.value = null;
  } finally {
    reportLoading.value = false;
  }
});
</script>

<style scoped>
.home-page { padding-bottom: 24px; }
.banner {
  background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 100%);
  color: #fff;
  padding: 48px 24px;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 24px;
}
.banner h1 { margin: 0 0 8px; font-size: 28px; }
.banner p { margin: 0 0 20px; opacity: 0.9; }
.main-row { margin-top: 8px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #303133; }
.job-cards { margin-bottom: 16px; }
.job-card { cursor: pointer; margin-bottom: 16px; }
.job-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.job-name { font-weight: 600; }
.company-name { font-size: 12px; color: #909399; }
.job-desc { font-size: 13px; color: #606266; margin: 0 0 8px; line-height: 1.4; }
.job-salary { color: #e6a23c; font-size: 14px; font-weight: 500; }
.report-card { min-height: 180px; }
.report-score { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
.report-summary { font-size: 13px; color: #606266; margin: 0 0 12px; line-height: 1.5; }
</style>
