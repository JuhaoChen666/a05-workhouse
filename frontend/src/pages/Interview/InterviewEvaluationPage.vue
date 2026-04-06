<template>
  <div class="evaluation-page">
    <div class="evaluation-header">
      <el-button link type="primary" @click="goBack">← 返回</el-button>
      <h1 class="evaluation-title">面试评估报告</h1>
      <p v-if="jobName" class="evaluation-sub">岗位：{{ jobName }}</p>
      <p class="evaluation-meta">会话 ID：{{ sessionId }}</p>
    </div>

    <el-skeleton v-if="loading" :rows="10" animated />
    <el-alert v-else-if="errorText" :title="errorText" type="error" show-icon class="mb-16" />
    <template v-else-if="data">
      <el-card class="score-card" shadow="never">
        <div class="score-row">
          <span class="score-label">综合得分</span>
          <span class="score-value">{{ formatScore(data.overall_score) }}</span>
        </div>
        <div v-if="data.recommendation" class="recommendation">
          <el-tag type="warning" size="large">{{ data.recommendation }}</el-tag>
        </div>
      </el-card>

      <el-card v-if="data.overall_comment" class="block-card" shadow="never">
        <template #header>总评</template>
        <p class="paragraph">{{ data.overall_comment }}</p>
      </el-card>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card class="block-card" shadow="never">
            <template #header>优势</template>
            <ul v-if="data.strengths?.length" class="bullet-list">
              <li v-for="(s, i) in data.strengths" :key="i">{{ s }}</li>
            </ul>
            <el-empty v-else description="暂无" :image-size="48" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="block-card" shadow="never">
            <template #header>待提升</template>
            <ul v-if="data.weaknesses?.length" class="bullet-list">
              <li v-for="(w, i) in data.weaknesses" :key="i">{{ w }}</li>
            </ul>
            <el-empty v-else description="暂无" :image-size="48" />
          </el-card>
        </el-col>
      </el-row>

      <el-card v-if="data.technical_evaluation" class="block-card" shadow="never">
        <template #header>技术能力评价</template>
        <p class="paragraph">{{ data.technical_evaluation }}</p>
      </el-card>

      <el-card v-if="data.communication_evaluation" class="block-card" shadow="never">
        <template #header>沟通表达评价</template>
        <p class="paragraph">{{ data.communication_evaluation }}</p>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getInterviewEvaluationApi, type InterviewEvaluationData } from '@/api/interviewAi';

const route = useRoute();
const router = useRouter();

const sessionId = computed(() => String(route.params.sessionId || '').trim());
const jobName = computed(() => String(route.query.jobName || '').trim());

const loading = ref(true);
const errorText = ref('');
const data = ref<InterviewEvaluationData | null>(null);

function formatScore(n: number | undefined) {
  if (n == null || Number.isNaN(Number(n))) return '--';
  return String(n);
}

function goBack() {
  router.back();
}

async function load() {
  const sid = sessionId.value;
  if (!sid) {
    errorText.value = '缺少会话 ID';
    loading.value = false;
    return;
  }
  loading.value = true;
  errorText.value = '';
  try {
    data.value = await getInterviewEvaluationApi(sid);
  } catch (e: unknown) {
    const msg = (e as Error).message || '加载报告失败';
    errorText.value = msg;
    ElMessage.error(msg);
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.evaluation-page {
  max-width: 920px;
  margin: 0 auto;
  padding: 8px 0 32px;
}

.evaluation-header {
  margin-bottom: 20px;
}

.evaluation-title {
  margin: 8px 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.evaluation-sub {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.evaluation-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}

.mb-16 {
  margin-bottom: 16px;
}

.score-card {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f0f7ff 0%, #fff 100%);
  border: 1px solid #e4e7ed;
}

.score-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.score-label {
  font-size: 15px;
  color: #606266;
}

.score-value {
  font-size: 32px;
  font-weight: 700;
  color: #409eff;
}

.recommendation {
  margin-top: 12px;
}

.block-card {
  margin-bottom: 16px;
}

.paragraph {
  margin: 0;
  line-height: 1.75;
  color: #303133;
  white-space: pre-wrap;
}

.bullet-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.7;
  color: #303133;
}
</style>
