<template>
  <div class="job-detail-page">
    <el-button type="primary" link @click="goBack" class="back-btn">← 返回</el-button>
    <el-card v-loading="loading" shadow="hover">
      <template v-if="job">
        <div class="job-header">
          <h2 class="job-title">{{ job.name }}</h2>
          <div class="company">
            <span class="company-name">{{ job.companyName }}</span>
            <el-image v-if="job.companyLogo" :src="job.companyLogo" class="company-logo" fit="contain" />
          </div>
          <div class="salary">
            薪资：{{ (job.salaryMin / 1000).toFixed(0) }}k - {{ (job.salaryMax / 1000).toFixed(0) }}k / 月
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
import { getJobDetailApi, type HotJobItem } from '@/api/jobs';

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const job = ref<HotJobItem | null>(null);

function goBack() {
  router.push({ name: 'Home' });
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
.job-detail-page { max-width: 800px; }
.back-btn { margin-bottom: 8px; }
.job-header { margin-bottom: 16px; }
.job-title { margin: 0 0 8px; }
.company { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.company-logo { width: 48px; height: 48px; }
.salary { color: #e6a23c; font-weight: 500; }
.job-content { white-space: pre-wrap; color: #606266; line-height: 1.6; }
h3 { margin: 16px 0 8px; }
</style>
