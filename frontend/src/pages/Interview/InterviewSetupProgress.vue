<template>
  <div class="setup-progress theme-card">
    <el-steps :active="active" finish-status="success" simple>
      <el-step title="选择面试类型" />
      <el-step title="设置面试岗位" />
      <el-step title="设置面试难度" />
    </el-steps>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  active: number;
}>();
</script>

<style scoped>
.setup-progress {
  margin-bottom: 12px;
  padding: 8px 12px;
}
</style>
