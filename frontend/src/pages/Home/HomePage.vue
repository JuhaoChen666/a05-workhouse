
<template>
  <div class="home-shell">
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

    <main class="home-main theme-page-shell">
      <div class="theme-section-header fade-in-up">
        <h2 class="theme-section-title">{{ pageHeaderText }} <span>{{ pageSubtitle }}</span></h2>
        <div class="theme-section-decoration"></div>
      </div>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, RouterLink, RouterView } from 'vue-router';
import { Collection, Document, Fold, HomeFilled, Notebook, Suitcase } from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';

const APP_TITLE = 'AI 模拟面试平台';
const route = useRoute();
const userStore = useUserStore();

const sidebarExpanded = ref(false);
const menuItems = [
  { name: 'Home', label: '首页', icon: HomeFilled },
  { name: 'HomeQuestion', label: '题库', icon: Collection },
  { name: 'HomeResume', label: '简历', icon: Document },
  { name: 'HomeJob', label: '岗位', icon: Suitcase },
  { name: 'HomeDoc', label: '文档', icon: Notebook },
];

const titleMap: Record<string, string> = {
  Home: '首页',
  HomeQuestion: '题库',
  HomeResume: '简历',
  HomeJob: '岗位',
  HomeDoc: '文档',
};

const activeRouteName = computed(() => String(route.name || 'Home'));
const currentPageTitle = computed(() => titleMap[activeRouteName.value] || '页面');
const greetingText = computed(() => {
  const hour = new Date().getHours();
  const username = userStore.userInfo?.username || userStore.userInfo?.name || '同学';
  if (hour < 11) return `早上好，${username}`;
  if (hour < 18) return `中午好，${username}`;
  return `还不睡觉吗，${username}`;
});
const pageHeaderText = computed(() => (activeRouteName.value === 'Home' ? greetingText.value : currentPageTitle.value));
const pageSubtitle = computed(() => (activeRouteName.value === 'Home' ? '今天也要比昨天更强一点' : '保持节奏，稳步提升面试竞争力'));

watch(
  currentPageTitle,
  (title) => {
    document.title = `${title} - ${APP_TITLE}`;
  },
  { immediate: true }
);
</script>

<style scoped>
.home-shell {
  min-height: calc(100vh - 120px);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 18px;
}
.home-sidebar {
  width: 64px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  padding: 14px 8px;
  transition: width 0.22s ease;
  overflow: hidden;
}
.home-sidebar.collapsed { width: 64px; }
.home-sidebar:not(.collapsed) { width: 104px; }
.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}
.collapse-icon {
  font-size: 16px;
  color: #6b7280;
}
.menu-list { display: grid; gap: 8px; }
.menu-item {
  text-decoration: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 100%;
  min-height: 52px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #4b5563;
  font-size: 12px;
  transition: all 0.2s ease;
}

.home-sidebar:not(.collapsed) .menu-item { min-height: 60px; }
.menu-item .el-icon { font-size: 17px; }
.menu-item:hover { background: #f3f4f6; }
.menu-item.active {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: #fff;
}
.home-main { min-width: 0; }
</style>
