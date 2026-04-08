<template>
  <section class="placeholder-page theme-card fade-in-up delay-1">
    <h3>{{ title }}（占位页面）</h3>
    <p>{{ desc }}</p>
    <el-button type="primary" class="theme-primary-btn">开发中</el-button>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  desc: string;
}>();
</script>

<style scoped>
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
</style>
