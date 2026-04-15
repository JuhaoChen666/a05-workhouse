
<template>
  <div
    class="home-shell"
    :class="{
      'home-shell--mobile-expanded': isMobile && !sidebarMobileCollapsed,
      'home-shell--mobile-collapsed': isMobile && sidebarMobileCollapsed,
    }"
  >
    <div class="home-sidebar-shell">
      <aside
        class="home-sidebar"
        :class="{ collapsed: sidebarCollapsedVisual, 'home-sidebar--mobile': isMobile }"
        @mouseenter="onSidebarEnter"
        @mouseleave="onSidebarLeave"
      >
        <div
          class="sidebar-top"
          role="button"
          tabindex="0"
          :aria-label="isMobile ? (sidebarMobileCollapsed ? '展开侧栏文字' : '折叠侧栏仅图标') : undefined"
          @click="onCollapseTriggerClick"
          @keydown.enter.prevent="onCollapseTriggerClick"
        >
          <el-icon
            class="collapse-icon"
            :class="{ 'collapse-icon--folded': isMobile && sidebarMobileCollapsed }"
          >
            <Fold />
          </el-icon>
        </div>
        <nav class="menu-list">
          <RouterLink
            v-for="item in menuItems"
            :key="item.name"
            class="menu-item"
            :class="{ active: isMenuActive(item.name) }"
            :to="{ name: item.name }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="showSidebarLabels">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>
    </div>

    <main class="home-main theme-page-shell">
      <div class="theme-section-header fade-in-up">
        <h2 class="theme-section-title">
          {{ pageHeaderText }} <span v-if="pageSubtitle">{{ pageSubtitle }}</span>
        </h2>
        <div class="theme-section-decoration"></div>
      </div>
      <RouterView v-slot="{ Component }">
        <transition :name="transitionName" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, RouterLink, RouterView } from "vue-router";
import {
  ChatDotRound,
  Document,
  Fold,
  HomeFilled,
  Notebook,
  Opportunity,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/store/user";
import { loadInterviewSetupDraft } from "@/pages/Interview/setupState";
import { useViewport } from "@/composables/useViewport";

const route = useRoute();
const userStore = useUserStore();
const { isMobile } = useViewport();

/** 桌面端：悬停展开；移动端：默认展开显示文字，可点击折叠为仅图标 */
const sidebarExpanded = ref(false);
const sidebarMobileCollapsed = ref(false);

const showSidebarLabels = computed(
  () => (isMobile.value ? !sidebarMobileCollapsed.value : sidebarExpanded.value)
);
const sidebarCollapsedVisual = computed(() =>
  isMobile.value ? sidebarMobileCollapsed.value : !sidebarExpanded.value
);

function onSidebarEnter() {
  if (isMobile.value) return;
  sidebarExpanded.value = true;
}
function onSidebarLeave() {
  if (isMobile.value) return;
  sidebarExpanded.value = false;
}
function onCollapseTriggerClick() {
  if (!isMobile.value) return;
  sidebarMobileCollapsed.value = !sidebarMobileCollapsed.value;
}
const menuItems = [
  { name: "Home", label: "首页", icon: HomeFilled },
  { name: "HomeInterviewType", label: "面试", icon: ChatDotRound },
  { name: "HomeQuestion", label: "AI押题", icon: Opportunity },
  { name: "HomeResume", label: "简历管理", icon: Document },
  { name: "HomeDoc", label: "帮助文档", icon: Notebook },
];

function isMenuActive(name: string) {
  if (name === "HomeQuestion") {
    return activeRouteName.value === "HomeQuestion" || activeRouteName.value === "HomePredictQuestions";
  }
  return activeRouteName.value === name;
}

const titleMap: Record<string, string> = {
  Home: "首页",
  HomeInterviewType: "面试设置",
  HomeInterviewPosition: "面试设置",
  HomeInterviewConfig: "面试设置",
  HomeInterview: "面试设置",
  HomeQuestion: "AI押题",
  HomePredictQuestions: "面试押题",
  HomeResume: "简历管理",
  HomeResumeOptimize: "简历优化",
  HomeResumeOptimizeRun: "简历优化",
  HomeJob: "岗位检索",
  HomeDoc: "帮助文档",
  Profile: "个人中心",
  ProfileEdit: "编辑资料",
};

const activeRouteName = computed(() => String(route.name || "Home"));
const transitionName = ref("fade-slide");
const setupStepMap: Record<string, number> = {
  HomeInterviewType: 0,
  HomeInterviewPosition: 1,
  HomeInterviewConfig: 2,
};
const prevSetupStep = ref<number | null>(setupStepMap[activeRouteName.value] ?? null);
const currentPageTitle = computed(
  () => {
    if (activeRouteName.value.startsWith("HomeInterview")) {
      const mode = loadInterviewSetupDraft().mode;
      if (mode === "avatar") return "虚拟人面试设置";
      if (mode === "text") return "AI面试设置";
      return "面试设置";
    }
    return titleMap[activeRouteName.value] || "页面";
  }
);
const greetingText = computed(() => {
  const hour = new Date().getHours();
  const username = userStore.userInfo?.username || "同学";
  if (hour < 11) return `早上好，${username}`;
  if (hour < 14) return `中午好，${username}`;
  if (hour < 19) return `下午好，${username}`;
  return `还不睡觉吗，${username}`;
});
const pageHeaderText = computed(() =>
  activeRouteName.value === "Home" ? greetingText.value : currentPageTitle.value
);
const pageSubtitle = computed(() =>
  activeRouteName.value === "Home"
    ? "今天也要比昨天更强一点"
    : activeRouteName.value === "Profile" || activeRouteName.value === "ProfileEdit"
      ? ""
    : activeRouteName.value.startsWith("HomeInterview")
      ? ""
    : activeRouteName.value === "HomeQuestion" || activeRouteName.value === "HomePredictQuestions"
      ? ""
      : "保持节奏，稳步提升面试竞争力"
);

watch(
  activeRouteName,
  (name) => {
    const nextStep = setupStepMap[name];
    const prevStep = prevSetupStep.value;
    if (typeof nextStep === "number" && typeof prevStep === "number") {
      transitionName.value = nextStep >= prevStep ? "setup-slide-left" : "setup-slide-right";
    } else if (typeof nextStep === "number") {
      transitionName.value = "setup-slide-left";
    } else {
      transitionName.value = "fade-slide";
    }
    prevSetupStep.value = typeof nextStep === "number" ? nextStep : null;
  },
  { immediate: true }
);
</script>

<style scoped>
.home-shell {
  position: relative;
  min-height: calc(100vh - 120px);
  padding-left: 64px;
}
.home-sidebar-shell {
  width: 64px;
}
.home-sidebar {
  position: fixed;
  left: 0;
  top: 10%;
  bottom: 10%;
  z-index: 20;
  width: 80px;
  background: linear-gradient(180deg, #f8fafc, #f1f5f9);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  color: #475569;
  padding: 10px 8px;
  transition: width 0.22s ease, box-shadow 0.22s ease;
  overflow: hidden;
}
.home-sidebar:hover {
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}
.home-sidebar.collapsed {
  width: 52px;
}
.home-sidebar:not(.collapsed) {
  width: 80px;
}
.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
  cursor: default;
}
.collapse-icon {
  color: #94a3b8;
  transition: transform 0.2s ease;
}
.menu-list {
  display: grid;
  gap: 8px;
}
.menu-item {
  text-decoration: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #475569;
  min-height: 56px;
  transition: all 0.2s ease;
  display:flex;
}

.menu-item span { font-size: 12px; line-height: 1.1; }
.home-sidebar.collapsed .menu-item { min-height: 44px; padding: 8px 4px; }
.menu-item .el-icon {
  font-size: 17px;
}
.menu-item:hover {
  background: #eef2ff;
  color: #4338ca;
}
.menu-item.active {
  background: linear-gradient(90deg, #ede9fe, #dbeafe);
  border-color: #c4b5fd;
  color: #4338ca;
}

/* 移动端：侧栏更窄；文字默认显示；点击折叠仅图标；悬停不再改变宽度 */
.home-sidebar--mobile .sidebar-top {
  cursor: pointer;
  border-radius: 10px;
}
.home-sidebar--mobile .sidebar-top:active {
  background: rgba(148, 163, 184, 0.2);
}
.collapse-icon--folded {
  transform: rotate(-90deg);
}
.home-sidebar--mobile:not(.collapsed) {
  width: 62px !important;
  padding: 8px 4px;
}
.home-sidebar--mobile.collapsed {
  width: 42px !important;
  padding: 8px 4px;
}
.home-sidebar--mobile.collapsed .menu-item {
  min-height: 40px;
  padding: 6px 2px;
}
.home-sidebar--mobile:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
}
.home-sidebar--mobile .menu-item span {
  font-size: 10px;
  max-width: 100%;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.home-shell--mobile-expanded {
  padding-left: 68px;
}
.home-shell--mobile-collapsed {
  padding-left: 46px;
}
.home-shell--mobile-expanded .home-sidebar-shell,
.home-shell--mobile-collapsed .home-sidebar-shell {
  width: auto;
  min-width: 0;
}

.home-main {
  color: #1f2937;
  flex: 1;
  min-width: 0;
}

.setup-slide-left-enter-active,
.setup-slide-left-leave-active,
.setup-slide-right-enter-active,
.setup-slide-right-leave-active {
  transition: all .26s ease;
}
.setup-slide-left-enter-from {
  opacity: 0;
  transform: translateX(18px);
}
.setup-slide-left-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
.setup-slide-right-enter-from {
  opacity: 0;
  transform: translateX(-18px);
}
.setup-slide-right-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
