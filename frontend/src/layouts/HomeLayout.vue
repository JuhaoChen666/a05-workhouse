<template>
  <div class="home-layout">
    <el-container>
      <!-- 左侧深蓝菜单 -->
      <el-aside width="200px" class="aside">
        <div class="logo">AI 面试平台</div>
        <el-menu
          :default-active="activeMenu"
          class="aside-menu"
          background-color="#0d2137"
          text-color="#b0c4de"
          active-text-color="#fff"
          router
        >
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/interview">
            <el-icon><Microphone /></el-icon>
            <span>模拟面试</span>
          </el-menu-item>
          <el-menu-item index="/question-bank">
            <el-icon><Collection /></el-icon>
            <span>题库</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container direction="vertical">
        <el-header class="header">
          <div class="header-right">
            <el-dropdown trigger="hover" @command="handleUserCommand">
              <span class="avatar-wrap">
                <el-avatar :size="36" class="avatar" :src="avatarSrc">
                  {{ avatarText }}
                </el-avatar>
                <span class="username" v-if="userStore.userInfo">
                  {{ userStore.userInfo.username }}
                </span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon>
                    个人中心
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        <el-main class="main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessageBox, ElMessage } from 'element-plus';
import {
  HomeFilled,
  Microphone,
  Collection,
  User,
  SwitchButton,
  ArrowDown,
} from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';
import { apiOrigin } from '@/api/request';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const activeMenu = computed(() => route.path);

const avatarSrc = computed(() => {
  const url = userStore.userInfo?.avatarUrl;
  if (!url) return undefined;
  return url.startsWith('http') ? url : apiOrigin + url;
});

const avatarText = computed(() => {
  const name = userStore.userInfo?.username;
  if (!name) return '?';
  return name.length >= 2 ? name.slice(0, 2) : name;
});

function handleUserCommand(command: string) {
  if (command === 'profile') {
    router.push({ name: 'Profile' });
  } else if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
      .then(() => {
        userStore.logout();
        ElMessage.success('已退出登录');
        router.push({ name: 'Login' });
      })
      .catch(() => {});
  }
}
</script>

<style scoped>
.home-layout {
  height: 100vh;
  overflow: hidden;
}
.aside {
  background-color: #0d2137;
  height: 100vh;
}
.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-weight: bold;
  font-size: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.aside-menu {
  border-right: none;
}
.aside-menu .el-menu-item {
  height: 52px;
  line-height: 52px;
}
.aside-menu .el-menu-item:hover,
.aside-menu .el-menu-item.is-active {
  background-color: #1a3a5c !important;
}
.header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
.avatar-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.avatar {
  background: linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%);
  color: #fff;
}
.username {
  font-size: 14px;
  color: #303133;
}
.main {
  background: #f5f7fa;
  padding: 20px;
  overflow: auto;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
