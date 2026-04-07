<template>
  <div class="job-detail-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">岗位详情 <span>Job Detail</span></h2>
      <div class="theme-section-decoration"></div>
    </div>
    <div class="theme-top-actions fade-in-up">
      <el-button @click="goBack" class="theme-back-btn">← 返回</el-button>
    </div>
    <el-card v-loading="loading" shadow="hover" class="theme-card fade-in-up delay-1">
      <template v-if="job">
        <div class="job-header">
          <div class="job-header-left">
            <h2 class="job-title">{{ job.name }}</h2>
            <div class="company">
              <el-image
                v-if="job.companyLogo"
                :src="`/img/${job.companyLogo}.ico`"
                class="company-logo"
                fit="contain"
              />
              <span class="company-name">{{ job.companyName }}</span>
            </div>
            <div class="salary">
              薪资：{{ formatSalaryRange(job.salaryMin, job.salaryMax) }}
            </div>
          </div>
          <div class="job-header-right">
            <el-button type="primary" class="theme-primary-btn" @click="startInterview">
              开始模拟面试
            </el-button>
          </div>
        </div>
        <el-divider />
        <h3>工作内容</h3>
        <p class="job-content">{{ job.jobContent }}</p>
      </template>
      <el-empty v-else-if="!loading" description="岗位不存在" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getJobDetailApi, formatSalaryRange, type HotJobItem } from '@/api/jobs';

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const job = ref<HotJobItem | null>(null);

function goBack() {
  router.push({ name: 'Home' });
}

// 从岗位详情页进入模拟面试流程
function startInterview() {
  if (!job.value) return;
  router.push({
    name: 'InterviewSettings',
    params: { id: String(job.value.id) },
  });
}

onMounted(async () => {
  const id = Number(route.params.id);
  if (!id) return;
  try {
    const res = await getJobDetailApi(id);
    job.value = res;
  } catch {
    job.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.job-detail-page { max-width: 1000px; }
.job-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.job-header-left {
  flex: 1;
}
.job-title { margin: 0 0 8px; }
.company { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.company-logo { width: 48px; height: 48px; }
.salary { color: #e6a23c; font-weight: 500; }
.job-content { white-space: pre-wrap; color: #606266; line-height: 1.6; }
h3 { margin: 16px 0 8px; }
</style>
