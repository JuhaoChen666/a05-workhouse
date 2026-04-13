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

/* 与 constants/breakpoints.ts MOBILE_MAX_WIDTH_PX 保持一致：移动端隐藏步骤条节省纵向空间 */
@media (max-width: 768px) {
  .setup-progress {
    display: none;
  }
}
</style>
