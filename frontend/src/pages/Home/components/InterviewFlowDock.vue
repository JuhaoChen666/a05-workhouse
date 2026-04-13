<template>
  <template v-if="visible">
    <Transition name="flow-dock-backdrop">
      <div
        v-show="open"
        class="flow-dock-backdrop"
        aria-hidden="true"
        @click="emit('update:open', false)"
      />
    </Transition>
    <Transition name="flow-dock-slide">
      <aside v-show="open" class="flow-dock-panel" aria-label="面试流程">
        <div class="flow-dock-duration-bar" aria-live="polite">
          <span class="flow-dock-duration-label">面试时长</span>
          <span class="flow-dock-duration-value">{{ durationDisplay }}</span>
        </div>
        <div class="flow-dock-focus" aria-live="polite">
          <div class="flow-dock-focus-head">
            <span class="flow-dock-focus-label">当前主题</span>
            <span class="flow-dock-focus-status">{{ focusStatus }}</span>
          </div>
          <p v-if="focusTopic" class="flow-dock-focus-topic">{{ focusTopic }}</p>
        </div>
        <div class="flow-dock-header">
          <span class="flow-dock-header-title">面试进度</span>
        </div>
        <div ref="flowDockBodyRef" class="flow-dock-body">
          <div class="flow-rail-list">
            <el-tooltip
              v-for="(node, i) in nodes"
              :key="node.id"
              placement="right-start"
              :show-after="180"
              :disabled="tooltipLines(node).length === 0"
              popper-class="flow-node-tooltip-popper"
              effect="light"
            >
              <template #content>
                <div class="flow-node-tooltip-content">
                  <div
                    v-for="(line, li) in tooltipLines(node)"
                    :key="li"
                    class="flow-node-tooltip-line"
                  >
                    {{ line }}
                  </div>
                </div>
              </template>
              <div
                class="flow-step"
                :data-flow-node-id="node.id"
                :class="{
                  'flow-step--ai': node.side === 'ai',
                  'flow-step--user': node.side === 'user',
                  'flow-step--thinking': node.status === 'thinking',
                  'flow-step--has-anchor': node.messageIndex !== null,
                }"
                role="button"
                tabindex="0"
                @click="emit('activate-node', node)"
                @keydown.enter.prevent="emit('activate-node', node)"
              >
                <div class="flow-step-grid">
                  <div class="flow-step-side flow-step-side--left">
                    <span v-if="node.side === 'ai'" class="flow-step-label flow-step-label--ai">{{ node.title }}</span>
                  </div>
                  <div class="flow-track">
                    <div class="flow-dot-wrap">
                      <span v-if="node.status === 'thinking'" class="flow-dot flow-dot--thinking" aria-hidden="true">
                        <el-icon class="flow-spin-icon is-loading"><Loading /></el-icon>
                      </span>
                      <span v-else class="flow-dot" :class="node.side === 'user' ? 'flow-dot--user' : 'flow-dot--ai'" />
                    </div>
                    <div v-if="i < nodes.length - 1" class="flow-vert-line" />
                  </div>
                  <div class="flow-step-side flow-step-side--right">
                    <span v-if="node.side === 'user'" class="flow-step-label flow-step-label--user">{{ node.title }}</span>
                  </div>
                </div>
              </div>
            </el-tooltip>
          </div>
        </div>
      </aside>
    </Transition>
    <button
      type="button"
      class="flow-dock-tab"
      :class="{ 'flow-dock-tab--panel-open': open }"
      :aria-expanded="open"
      :aria-label="open ? '折叠流程' : '展开流程'"
      :title="open ? '折叠流程' : '展开流程'"
      @click="emit('update:open', !open)"
    >
      <el-icon class="flow-dock-tab-chevron">
        <DArrowRight v-if="!open" />
        <DArrowLeft v-else />
      </el-icon>
    </button>
  </template>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Loading, DArrowLeft, DArrowRight } from '@element-plus/icons-vue';

type FlowNode = {
  id: string;
  side: 'ai' | 'user';
  title: string;
  status: 'thinking' | 'done';
  messageIndex: number | null;
};

defineProps<{
  visible: boolean;
  open: boolean;
  durationDisplay: string;
  focusStatus: string;
  focusTopic: string;
  nodes: FlowNode[];
  tooltipLines: (node: FlowNode) => string[];
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  'activate-node': [node: FlowNode];
}>();

const flowDockBodyRef = ref<HTMLElement | null>(null);

defineExpose({
  flowDockBodyRef,
});
</script>

<style scoped>
.flow-dock-backdrop {
  display: none;
}
.flow-dock-backdrop-enter-active,
.flow-dock-backdrop-leave-active {
  transition: opacity 0.26s ease;
}
.flow-dock-backdrop-enter-from,
.flow-dock-backdrop-leave-to {
  opacity: 0;
}
.flow-dock-slide-enter-active.flow-dock-panel,
.flow-dock-slide-leave-active.flow-dock-panel {
  transition:
    transform 0.28s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.22s ease;
}
.flow-dock-slide-enter-from.flow-dock-panel,
.flow-dock-slide-leave-to.flow-dock-panel {
  transform: translate(-100%, -50%);
  opacity: 0;
  pointer-events: none;
}
.flow-dock-panel {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 280px;
  height: min(86vh, calc(100vh - 24px));
  max-height: calc(100vh - 16px);
  z-index: 2000;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  border: 1px solid #d1d5db;
  border-radius: 0 16px 16px 0;
  box-shadow:
    4px 0 24px rgba(0, 0, 0, 0.04),
    4px 0 32px -8px rgba(59, 130, 246, 0.1),
    4px 0 28px -12px rgba(168, 85, 247, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.flow-dock-duration-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(90deg, rgba(245, 243, 255, 0.85) 0%, rgba(239, 246, 255, 0.75) 100%);
}
.flow-dock-duration-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6b7280;
}
.flow-dock-duration-value {
  font-size: 15px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #111827;
  background: linear-gradient(90deg, #6d28d9, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.flow-dock-focus {
  flex-shrink: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.65);
}
.flow-dock-focus-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.flow-dock-focus-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9ca3af;
  flex-shrink: 0;
}
.flow-dock-focus-status {
  font-size: 11px;
  font-weight: 600;
  color: #6d28d9;
  text-align: right;
  line-height: 1.35;
  min-width: 0;
}
.flow-dock-focus-topic {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #374151;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.flow-dock-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 12px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}
.flow-dock-header-title {
  display: block;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #111827;
}
.flow-dock-header-title::after {
  content: '';
  display: block;
  width: 40px;
  height: 3px;
  margin-top: 8px;
  border-radius: 2px;
  background: linear-gradient(90deg, #a855f7, #3b82f6);
}
.flow-dock-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px 8px 14px;
  scrollbar-gutter: stable;
}
.flow-dock-tab {
  position: fixed;
  left: 0;
  top: 50%;
  z-index: 2001;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  min-height: 64px;
  padding: 6px 0;
  margin: 0;
  border: 1px solid #d8dbe3;
  border-left: none;
  border-radius: 0 10px 10px 0;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  color: #374151;
  line-height: 1;
  transition:
    left 0.22s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}
.flow-dock-tab:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  box-shadow: 0 6px 16px rgba(124, 58, 237, 0.12);
  transform: translateY(calc(-50% - 1px));
}
.flow-dock-tab--panel-open {
  left: 280px;
}
.flow-dock-tab-chevron {
  font-size: 16px;
  color: #7c3aed;
}
.flow-dock-tab:hover .flow-dock-tab-chevron {
  color: #6d28d9;
}

.flow-rail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.flow-step {
  user-select: none;
  cursor: pointer;
  padding: 6px 4px;
  margin: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  transition: color 0.18s ease;
}
.flow-step:focus-visible {
  outline: 2px solid rgba(139, 92, 246, 0.5);
  outline-offset: 2px;
}
.flow-step:hover .flow-step-label--ai {
  color: #5b21b6;
  font-weight: 700;
}
.flow-step:hover .flow-step-label--user {
  color: #1d4ed8;
  font-weight: 700;
}
.flow-step:hover .flow-dot--ai {
  transform: scale(1.35);
  box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.32);
}
.flow-step:hover .flow-dot--user {
  transform: scale(1.35);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.32);
}
.flow-step:hover .flow-dot--thinking .flow-spin-icon {
  color: #9333ea;
}
.flow-step--has-anchor:hover .flow-step-label--ai,
.flow-step--has-anchor:hover .flow-step-label--user {
  text-decoration: underline;
  text-decoration-color: rgba(124, 58, 237, 0.45);
  text-underline-offset: 2px;
}
.flow-step-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 18px minmax(0, 1fr);
  align-items: start;
  gap: 4px 6px;
  min-height: 28px;
}
.flow-step-side {
  min-width: 0;
  font-size: 11px;
  line-height: 1.4;
  padding-top: 2px;
}
.flow-step-side--left {
  text-align: right;
}
.flow-step-side--right {
  text-align: left;
}
.flow-step-label {
  display: inline-block;
  max-width: 100%;
  word-break: break-word;
}
.flow-step-label--ai {
  color: #6d28d9;
  font-weight: 600;
}
.flow-step-label--user {
  color: #2563eb;
  font-weight: 600;
}
.flow-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 18px;
  flex-shrink: 0;
}
.flow-dot-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 18px;
}
.flow-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.flow-dot--ai {
  background: linear-gradient(145deg, #c084fc, #7c3aed);
}
.flow-dot--user {
  background: linear-gradient(145deg, #93c5fd, #2563eb);
}
.flow-dot--thinking {
  width: auto;
  height: auto;
  background: transparent;
  box-shadow: none;
}
.flow-spin-icon {
  font-size: 15px;
  color: #8b5cf6;
  transition: color 0.18s ease;
}
.flow-vert-line {
  width: 2px;
  flex: 1;
  min-height: 10px;
  margin: 4px 0 0;
  border-radius: 2px;
  background: linear-gradient(180deg, rgba(168, 85, 247, 0.55), rgba(59, 130, 246, 0.5));
}
.flow-step--thinking .flow-step-label--ai {
  color: #7c3aed;
}

@media (max-width: 768px) {
  .flow-dock-backdrop { display:block;position:fixed;inset:0;z-index:1999;background:rgba(15,23,42,.35); }
  .flow-dock-panel { width:min(288px, 86vw);top:0;bottom:0;left:0;height:auto;max-height:none;transform:none;border-radius:0 12px 12px 0; }
  .flow-dock-tab--panel-open { left:min(288px, 86vw); }
  .flow-dock-slide-enter-from.flow-dock-panel,
  .flow-dock-slide-leave-to.flow-dock-panel { transform:translateX(-100%); }
}
</style>
