<template>
  <!-- 后台管理整体布局：左侧菜单 + 顶部栏 + 内容区；窄屏侧栏收入抽屉 -->
  <el-container class="layout">
    <el-aside v-if="!isMobile" width="220px" class="aside">
      <div class="logo">管理后台</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1a1a2e"
        text-color="#e4e7ed"
        active-text-color="#409eff"
      >
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/resumes">
          <el-icon><Files /></el-icon>
          <span>简历管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/sessions">
          <el-icon><Memo /></el-icon>
          <span>会话管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/positions">
          <el-icon><Briefcase /></el-icon>
          <span>岗位管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button
            v-if="isMobile"
            text
            class="nav-toggle"
            aria-label="打开菜单"
            @click="drawerVisible = true"
          >
            <el-icon :size="22"><Menu /></el-icon>
          </el-button>
          <span class="page-title">{{ pageTitle }}</span>
        </div>
        <div class="right">
          <span class="username">{{ userStore.userInfo?.username }}</span>
          <el-tag v-if="userStore.userInfo?.roleName" size="small">{{ userStore.userInfo.roleName }}</el-tag>
          <el-button type="danger" link @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>

    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      size="260px"
      class="admin-drawer"
      :with-header="true"
      title="管理后台"
      append-to-body
    >
      <div class="drawer-menu-wrap">
        <el-menu
          :default-active="activeMenu"
          router
          background-color="#1a1a2e"
          text-color="#e4e7ed"
          active-text-color="#409eff"
          @select="drawerVisible = false"
        >
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/resumes">
            <el-icon><Files /></el-icon>
            <span>简历管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/sessions">
            <el-icon><Memo /></el-icon>
            <span>会话管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/positions">
            <el-icon><Briefcase /></el-icon>
            <span>岗位管理</span>
          </el-menu-item>
        </el-menu>
      </div>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { User, Briefcase, Menu, Files, Memo } from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';
import { useViewport } from '@/composables/useViewport';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const { isMobile } = useViewport();

const drawerVisible = ref(false);

const activeMenu = computed(() => route.path);

const pageTitle = computed(() => (route.meta.title as string) || '管理后台');

watch(
  () => route.path,
  () => {
    drawerVisible.value = false;
  }
);

function onLogout() {
  userStore.logout();
  router.push({ name: 'Login' });
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background-color: #1a1a2e;
}

.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  border-bottom: 1px solid #2c2c3e;
}

.drawer-menu-wrap {
  min-height: 100%;
  background-color: #1a1a2e;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.nav-toggle {
  flex-shrink: 0;
  padding: 8px !important;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.username {
  color: #606266;
  font-size: 14px;
}

.main {
  padding: 20px;
  background: #f5f7fa;
  overflow: auto;
}

@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }
  .main {
    padding: 12px;
  }
  .username {
    display: none;
  }
}
</style>

<style>
.admin-drawer.el-drawer .el-drawer__body {
  padding: 0;
  background-color: #1a1a2e;
}
</style>
