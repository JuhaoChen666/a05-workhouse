<template>
  <div ref="container" class="resume-thumbnail-frame" aria-hidden="true">
    <img class="resume-thumbnail" :src="imageSrc" alt="" @error="onImageError" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { buildInterviewAssetUrl } from '@/api/resumeAssets';
import { useUserStore } from '@/store/user';
import { queueResumeThumbnail } from '@/utils/resumeThumbnailQueue';
import placeholder from '@/assets/resume-document-placeholder.svg';

const props = defineProps<{ url?: string | null }>();
const userStore = useUserStore();
const container = ref<HTMLElement>();
const objectUrl = ref('');
const failed = ref(false);
const imageSrc = computed(() => failed.value ? placeholder : objectUrl.value || placeholder);
let observer: IntersectionObserver | undefined;
let controller: AbortController | undefined;
let cancelQueued: (() => void) | undefined;
let requestedUrl = '';
let activated = false;

function revokeObjectUrl() {
  if (!objectUrl.value) return;
  URL.revokeObjectURL(objectUrl.value);
  objectUrl.value = '';
}

function resetRequest() {
  cancelQueued?.();
  cancelQueued = undefined;
  controller?.abort();
  controller = undefined;
  requestedUrl = '';
  failed.value = false;
  revokeObjectUrl();
}

function loadThumbnail() {
  const url = props.url?.trim();
  if (!url || !url.startsWith('/api/resume-library/thumbnail/') || requestedUrl === url) return;
  requestedUrl = url;
  cancelQueued = queueResumeThumbnail(async () => {
    if (!container.value || !props.url || props.url.trim() !== url) return;
    const current = new AbortController();
    controller = current;
    try {
      const response = await fetch(buildInterviewAssetUrl(url), {
        headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
        signal: current.signal,
      });
      if (!response.ok) throw new Error(`Thumbnail request failed: ${response.status}`);
      const blob = await response.blob();
      if (current.signal.aborted || !container.value || props.url?.trim() !== url) return;
      objectUrl.value = URL.createObjectURL(blob);
    } catch {
      if (!current.signal.aborted) failed.value = true;
    } finally {
      if (controller === current) controller = undefined;
    }
  });
}

function onImageError() {
  if (objectUrl.value) failed.value = true;
}

watch(() => props.url, () => {
  resetRequest();
  if (activated) loadThumbnail();
});

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') {
    activated = true;
    loadThumbnail();
    return;
  }
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) {
      activated = true;
      observer?.disconnect();
      loadThumbnail();
    }
  }, { rootMargin: '160px' });
  if (container.value) observer.observe(container.value);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  resetRequest();
});
</script>

<style scoped>
.resume-thumbnail-frame { flex: 0 0 184px; height: 184px; display: grid; place-items: center; overflow: hidden; border-radius: 11px; background: linear-gradient(145deg, #f8f8fc, #f3f2f8); }
.resume-thumbnail { display: block; width: auto; height: 100%; max-width: 100%; object-fit: contain; filter: drop-shadow(0 5px 12px rgba(35, 30, 65, .13)); }
</style>
