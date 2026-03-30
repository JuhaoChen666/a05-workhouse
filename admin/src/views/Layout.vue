<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">管理后台</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1a1a2e"
        text-color="#e4e7ed"
        active-text-color="#409eff"
      >
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/positions">
          <el-icon><Briefcase /></el-icon>
          <span>岗位管理</span>
        </el-menu-item>
        <el-menu-item index="/question-bank">
          <el-icon><Document /></el-icon>
          <span>题库管理</span>
        </el-menu-item>
        <el-menu-item index="/learning-resource">
          <el-icon><Reading /></el-icon>
          <span>学习资源</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
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
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { User, Briefcase, Document, Reading } from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const activeMenu = computed(() => route.path);

const pageTitle = computed(() => (route.meta.title as string) || '管理后台');

const onLogout = () => {
  userStore.logout();
  router.push({ name: 'Login' });
};
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

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
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
</style>
