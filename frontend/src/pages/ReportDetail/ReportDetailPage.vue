<template>
  <div class="report-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">AI 面试报告 <span>Report</span></h2>
      <div class="theme-section-decoration"></div>
    </div>
    <div class="theme-top-actions fade-in-up">
      <el-button @click="goBack" class="theme-back-btn">← 返回</el-button>
    </div>
    <el-card v-loading="loading" shadow="hover" class="theme-card fade-in-up delay-1">
      <template v-if="report">
        <div class="report-summary">
          <el-statistic title="综合得分" :value="content.totalScore ?? 0" suffix="分" />
        </div>
        <el-divider />
        <h3>各维度得分</h3>
        <el-table :data="content.dimensions || []" stripe>
          <el-table-column prop="name" label="维度" width="140" />
          <el-table-column prop="score" label="得分" width="100" />
          <el-table-column prop="comment" label="评语" />
        </el-table>
        <template v-if="content.summary">
          <h3>总结</h3>
          <p class="summary-text">{{ content.summary }}</p>
        </template>
        <template v-if="content.suggestions && content.suggestions.length">
          <h3>改进建议</h3>
          <ul>
            <li v-for="(s, i) in content.suggestions" :key="i">{{ s }}</li>
          </ul>
        </template>
      </template>
      <el-empty v-else-if="!loading" description="暂无报告数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getReportByRecordIdApi } from '@/api/report';
import type { ReportContent } from '@/api/report';

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const report = ref<{ id: number; interviewRecordId: number; content: ReportContent } | null>(null);

const content = computed(() => report.value?.content ?? {} as ReportContent);

function goBack() {
  router.push({ name: 'Profile' });
}

onMounted(async () => {
  const id = Number(route.params.id);
  if (!id) return;
  try {
    const res = await getReportByRecordIdApi(id);
    report.value = res;
  } catch {
    report.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.report-page { max-width: 1000px; }
.report-summary { margin-bottom: 16px; }
h3 { margin: 16px 0 8px; }
.summary-text { color: #606266; line-height: 1.6; }
ul { padding-left: 20px; }
</style>
