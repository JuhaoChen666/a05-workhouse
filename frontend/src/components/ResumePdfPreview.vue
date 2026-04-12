<template>
  <div class="resume-pdf-preview" :class="rootClass">
    <VueOfficePdf v-if="normalizedSrc" :src="normalizedSrc" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import VueOfficePdf from '@vue-office/pdf';

const props = withDefaults(
  defineProps<{
    /** Blob URL、http(s) 等与「我的简历」在线预览一致的地址 */
    src: string;
    /**
     * dialog：与 ResumeManage 弹窗一致（70vh）
     * optimize：简历优化预览页（min(72vh, 720px)）
     * sidebar：侧栏小窗，高度由父级滚动容器约束
     * zoom：面试「放大查看」（min(78vh, 720px)）
     */
    variant?: 'dialog' | 'optimize' | 'sidebar' | 'zoom';
  }>(),
  { variant: 'dialog' }
);

const normalizedSrc = computed(() => String(props.src || '').trim());

const rootClass = computed(() => ({
  'resume-pdf-preview--dialog': props.variant === 'dialog',
  'resume-pdf-preview--optimize': props.variant === 'optimize',
  'resume-pdf-preview--sidebar': props.variant === 'sidebar',
  'resume-pdf-preview--zoom': props.variant === 'zoom',
}));
</script>

<style scoped>
/* 与 ResumeManagePage `.pdf-wrap` 一致 */
.resume-pdf-preview--dialog {
  height: 70vh;
  overflow: auto;
}
.resume-pdf-preview--optimize {
  height: min(72vh, 720px);
  overflow: auto;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}
.resume-pdf-preview--zoom {
  height: min(78vh, 720px);
  overflow: auto;
}
.resume-pdf-preview--sidebar {
  min-height: 320px;
  width: 100%;
  overflow: visible;
}
</style>
