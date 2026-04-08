
<template>
  <div class="home-shell">
    <div class="home-sidebar-shell">
      <aside
        class="home-sidebar"
        :class="{ collapsed: !sidebarExpanded }"
        @mouseenter="sidebarExpanded = true"
        @mouseleave="sidebarExpanded = false"
      >
        <div class="sidebar-top">
          <el-icon class="collapse-icon"><Fold /></el-icon>
        </div>
        <nav class="menu-list">
          <RouterLink
            v-for="item in menuItems"
            :key="item.name"
            class="menu-item"
            :class="{ active: activeRouteName === item.name }"
            :to="{ name: item.name }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="sidebarExpanded">{{ item.label }}</span>
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
  Collection,
  Document,
  Fold,
  HomeFilled,
  Notebook,
  Suitcase,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/store/user";

const route = useRoute();
const userStore = useUserStore();

const sidebarExpanded = ref(false);
const menuItems = [
  { name: "Home", label: "首页", icon: HomeFilled },
  { name: "HomeInterviewType", label: "面试", icon: ChatDotRound },
  { name: "HomeQuestion", label: "题库", icon: Collection },
  { name: "HomeResume", label: "简历", icon: Document },
  { name: "HomeJob", label: "岗位", icon: Suitcase },
  { name: "HomeDoc", label: "帮助文档", icon: Notebook },
];

const titleMap: Record<string, string> = {
  Home: "首页",
  HomeInterviewType: "面试设置",
  HomeInterviewPosition: "面试设置",
  HomeInterviewConfig: "面试设置",
  HomeInterview: "面试设置",
  HomeQuestion: "题库",
  HomeResume: "简历",
  HomeJob: "岗位",
  HomeDoc: "帮助文档",
  Profile: "个人信息",
  ProfileEdit: "个人信息",
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
  () => titleMap[activeRouteName.value] || "页面"
);
const greetingText = computed(() => {
  const hour = new Date().getHours();
  const username =
    userStore.userInfo?.username || userStore.userInfo?.name || "同学";
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
      : "保持节奏，稳步提升面试竞争力"
);

watch(
  currentPageTitle,
  (title) => {
    document.title = title;
  },
  { immediate: true }
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
}
.collapse-icon {
  color: #94a3b8;
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
