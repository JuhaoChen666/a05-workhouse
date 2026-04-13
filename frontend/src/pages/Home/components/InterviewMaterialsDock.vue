<template>
  <template v-if="visible">
    <Transition name="material-dock-backdrop">
      <div
        v-show="open"
        class="material-dock-backdrop"
        aria-hidden="true"
        @click="emit('update:open', false)"
      />
    </Transition>
    <Transition name="material-dock-slide">
      <aside v-show="open" class="material-dock-panel" aria-label="资料与助手">
        <div class="material-dock-header">
          <span class="material-dock-header-title">面试助手</span>
          <el-button
            text
            circle
            class="material-dock-collapse-btn"
            title="折叠"
            aria-label="折叠资料面板"
            @click="emit('update:open', false)"
          >
            <el-icon><DArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="material-dock-body">
          <section class="material-dock-section">
            <div class="material-dock-section-head">
              <h4 class="material-dock-section-title">个人简历</h4>
              <el-button
                v-if="hasSessionResume"
                size="small"
                type="primary"
                plain
                class="material-zoom-btn"
                @click="resumeZoomOpen = true"
              >
                查看
              </el-button>
            </div>
            <div v-if="sessionResumeLoading" class="material-dock-hint">加载中…</div>
            <div v-else-if="sessionResumeError" class="material-dock-error">{{ sessionResumeError }}</div>
            <template v-else-if="sessionResumePdfSrc">
              <div class="material-resume-pdf-thumb" role="region" aria-label="简历 PDF 预览">
                <div class="material-resume-pdf-toolbar">
                  <div class="material-resume-pdf-toolbar-zoom">
                    <el-button size="small" text class="material-resume-pdf-tool-btn" @click="emit('zoom-out')">
                      <el-icon><Minus /></el-icon>
                    </el-button>
                    <span class="material-resume-pdf-zoom-label">{{ resumeThumbZoomPercent }}%</span>
                    <el-button size="small" text class="material-resume-pdf-tool-btn" @click="emit('zoom-in')">
                      <el-icon><Plus /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" text type="primary" class="material-resume-pdf-reset" @click="emit('zoom-reset')">
                    重置
                  </el-button>
                </div>
                <p class="material-resume-pdf-hint">拖动平移 · 滚轮缩放</p>
                <div
                  class="material-resume-pdf-viewport"
                  :class="{ 'is-dragging': resumeThumbDragging }"
                  @wheel.prevent="emit('thumb-wheel', $event)"
                  @pointerdown="emit('thumb-pointer-down', $event)"
                  @pointermove="emit('thumb-pointer-move', $event)"
                  @pointerup="emit('thumb-pointer-up', $event)"
                  @pointercancel="emit('thumb-pointer-up', $event)"
                >
                  <div
                    class="material-resume-pdf-pan-layer"
                    :style="{
                      transform: `translate(${resumeThumbPanX}px, ${resumeThumbPanY}px) scale(${resumeThumbScale})`,
                    }"
                  >
                    <ResumePdfPreview :src="sessionResumePdfSrc" variant="sidebar" />
                  </div>
                </div>
              </div>
            </template>
            <pre v-else-if="sessionResumePlainText" class="material-resume-text">{{ sessionResumePlainText }}</pre>
            <el-empty
              v-else
              description="暂无本场简历快照，请从面试设置重新进入"
              :image-size="56"
              class="material-resume-empty"
            />
          </section>
          <section class="material-dock-section material-dock-section--ai">
            <h4 class="material-dock-section-title">面试助手</h4>
            <div class="ai-assistant-card" />
          </section>
        </div>
      </aside>
    </Transition>
    <button
      type="button"
      class="material-dock-tab"
      :class="{ 'material-dock-tab--panel-open': open }"
      :aria-expanded="open"
      :aria-label="open ? '折叠资料' : '展开资料'"
      :title="open ? '折叠资料' : '展开资料'"
      @click="emit('update:open', !open)"
    >
      <el-icon class="material-dock-tab-chevron">
        <DArrowLeft v-if="!open" />
        <DArrowRight v-else />
      </el-icon>
    </button>

    <el-dialog
      v-model="resumeZoomOpen"
      :title="sessionResumeTitle || '简历预览'"
      width="min(96vw, 920px)"
      append-to-body
      class="resume-zoom-dialog"
    >
      <ResumePdfPreview v-if="sessionResumePdfSrc" :src="sessionResumePdfSrc" variant="zoom" />
      <pre v-else-if="sessionResumePlainText" class="resume-zoom-text">{{ sessionResumePlainText }}</pre>
      <div v-else class="material-dock-hint">暂无可展示内容</div>
    </el-dialog>
  </template>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { DArrowLeft, DArrowRight, Plus, Minus } from '@element-plus/icons-vue';
import ResumePdfPreview from '@/components/ResumePdfPreview.vue';

defineProps<{
  visible: boolean;
  open: boolean;
  hasSessionResume: boolean;
  sessionResumeLoading: boolean;
  sessionResumeError: string;
  sessionResumePdfSrc: string;
  sessionResumePlainText: string;
  sessionResumeTitle: string;
  resumeThumbZoomPercent: number;
  resumeThumbDragging: boolean;
  resumeThumbPanX: number;
  resumeThumbPanY: number;
  resumeThumbScale: number;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  'zoom-in': [];
  'zoom-out': [];
  'zoom-reset': [];
  'thumb-wheel': [evt: WheelEvent];
  'thumb-pointer-down': [evt: PointerEvent];
  'thumb-pointer-move': [evt: PointerEvent];
  'thumb-pointer-up': [evt: PointerEvent];
}>();

const resumeZoomOpen = ref(false);
</script>

<style scoped>
.material-dock-backdrop { display:none; }
.material-dock-backdrop-enter-active,
.material-dock-backdrop-leave-active { transition:opacity .26s ease; }
.material-dock-backdrop-enter-from,
.material-dock-backdrop-leave-to { opacity:0; }
.material-dock-slide-enter-active.material-dock-panel,
.material-dock-slide-leave-active.material-dock-panel { transition:transform .28s cubic-bezier(0.32,0.72,0,1),opacity .22s ease; }
.material-dock-slide-enter-from.material-dock-panel,
.material-dock-slide-leave-to.material-dock-panel { transform:translate(100%,-50%);opacity:0;pointer-events:none; }
.material-dock-panel { position:fixed;right:0;top:50%;transform:translateY(-50%);width:280px;height:min(86vh, calc(100vh - 24px));max-height:calc(100vh - 16px);z-index:2000;display:flex;flex-direction:column;background:linear-gradient(215deg,#fff 0%,#f9fafb 100%);border-left:1px solid #e5e7eb;border-radius:16px 0 0 16px;box-shadow:-4px 0 24px rgba(0,0,0,.04),-4px 0 32px -8px rgba(59,130,246,.1),-4px 0 28px -12px rgba(168,85,247,.08),inset 0 1px 0 rgba(255,255,255,.9); }
.material-dock-header { display:flex;align-items:flex-start;justify-content:space-between;gap:8px;padding:14px 12px 12px;border-bottom:1px solid #e5e7eb;background:linear-gradient(180deg,#fff 0%,#fafafa 100%); }
.material-dock-header-title { font-size:13px;font-weight:800;color:#111827; }
.material-dock-header-title::after { content:'';display:block;width:40px;height:3px;margin-top:8px;border-radius:2px;background:linear-gradient(90deg,#3b82f6,#a855f7); }
.material-dock-collapse-btn { color:#6b7280 !important; }
.material-dock-body { flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:12px 10px 16px;display:flex;flex-direction:column;gap:14px;scrollbar-gutter:stable; }
.material-dock-section-title { margin:0;font-size:12px;font-weight:800;color:#374151;letter-spacing:.04em; }
.material-dock-section-head { display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px; }
.material-dock-hint { font-size:12px;color:#6b7280;padding:8px 0; }
.material-dock-error { font-size:12px;color:#b91c1c;line-height:1.45; }
.material-resume-pdf-thumb { display:flex;flex-direction:column;gap:4px;height:268px;max-height:268px;padding:6px 6px 8px;overflow:hidden;border-radius:10px;border:1px solid #e5e7eb;background:#f3f4f6; }
.material-resume-pdf-toolbar { display:flex;align-items:center;justify-content:space-between;gap:6px; }
.material-resume-pdf-toolbar-zoom { display:flex;align-items:center;gap:2px; }
.material-resume-pdf-tool-btn { padding:4px 8px !important;min-height:28px !important; }
.material-resume-pdf-zoom-label { font-size:11px;font-weight:700;font-variant-numeric:tabular-nums;color:#374151;min-width:38px;text-align:center; }
.material-resume-pdf-hint { margin:0;font-size:10px;color:#9ca3af;line-height:1.3; }
.material-resume-pdf-viewport { flex:1;min-height:0;overflow:hidden;border-radius:8px;background:#e5e7eb;cursor:grab;touch-action:none;user-select:none; }
.material-resume-pdf-viewport.is-dragging { cursor:grabbing; }
.material-resume-pdf-pan-layer { transform-origin:0 0;will-change:transform;width:max-content;max-width:none; }
.material-resume-pdf-pan-layer :deep(.resume-pdf-preview--sidebar) { min-height:240px;width:232px;overflow:visible; }
.material-resume-text { max-height:240px;overflow:auto;margin:0;padding:10px;font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-word;background:#f9fafb;border-radius:10px;border:1px solid #e5e7eb;color:#1f2937;font-family:inherit; }
.material-dock-section--ai { padding-top:4px;border-top:1px dashed #e5e7eb; }
.ai-assistant-card { padding:10px;border-radius:12px;background:linear-gradient(145deg,#f8fafc 0%,#f1f5f9 100%);border:1px solid #e2e8f0;min-height:44px; }
.material-dock-tab { position:fixed;right:0;top:50%;z-index:2001;transform:translateY(-50%);display:flex;align-items:center;justify-content:center;width:26px;min-height:64px;padding:6px 0;border:1px solid #d8dbe3;border-right:none;border-radius:10px 0 0 10px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.04);cursor:pointer;color:#374151;line-height:1;transition:right .22s ease,border-color .2s ease,box-shadow .2s ease,color .2s ease,transform .2s ease; }
.material-dock-tab--panel-open { right:280px; }
.material-dock-tab-chevron { font-size:16px;color:#2563eb; }
.resume-zoom-text { max-height:min(78vh,720px);overflow:auto;margin:0;padding:8px;font-size:13px;line-height:1.55;white-space:pre-wrap;word-break:break-word;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb; }
@media (max-width: 768px) {
  .material-dock-backdrop { display:block;position:fixed;inset:0;z-index:1999;background:rgba(15,23,42,.35); }
  .material-dock-panel { width:min(288px,86vw);top:0;bottom:0;right:0;height:auto;max-height:none;transform:none;border-radius:12px 0 0 12px; }
  .material-dock-tab--panel-open { right:min(288px,86vw); }
  .material-dock-slide-enter-from.material-dock-panel,
  .material-dock-slide-leave-to.material-dock-panel { transform:translateX(100%); }
}
</style>
