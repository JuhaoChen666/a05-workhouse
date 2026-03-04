<template>
  <div class="interview-session-page">
    <el-card class="session-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>模拟面试</span>
          <el-button type="primary" link @click="backToSettings">
            返回面试设置
          </el-button>
        </div>
      </template>

      <div v-if="jobName" class="job-info">
        当前面试岗位：
        <span class="job-name">{{ jobName }}</span>
      </div>
      <div class="resume-info">
        简历状态：
        <el-tag size="small" :type="withResume ? 'success' : 'info'">
          {{ withResume ? '已上传简历（详情待接入）' : '本次不提交简历' }}
        </el-tag>
      </div>

      <el-alert
        title="面试对话区域暂未实现"
        type="info"
        description="此页面作为模拟面试主界面的占位，后续可以在此接入 AI 问答、语音/视频等功能。"
        show-icon
        class="placeholder-alert"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

// 路由对象
const route = useRoute();
const router = useRouter();

// 是否带简历进入面试
const withResume = computed(() => route.query.withResume === '1');

// 面试岗位名称（当前从 query 读取，后续可根据 ID 请求后端）
const jobName = computed(() => (route.query.jobName as string) || '');

// 返回面试设置页
function backToSettings() {
  const id = route.params.id;
  if (id) {
    router.push({ name: 'InterviewSettings', params: { id: String(id) } });
  } else {
    router.push({ name: 'Home' });
  }
}
</script>

<style scoped>
.interview-session-page {
  max-width: 960px;
  margin: 0 auto;
}
.session-card {
  width: 100%;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.job-info {
  margin-bottom: 8px;
}
.job-name {
  font-weight: 600;
}
.resume-info {
  margin-bottom: 16px;
}
.placeholder-alert {
  margin-top: 8px;
}
</style>

