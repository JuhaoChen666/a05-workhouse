<template>
  <div class="home-layout">
    <el-container>
      <el-container direction="vertical" class="main-wrapper" :class="{ 'main-wrapper-full': isInterviewSessionPage }">
        <el-header v-if="!isInterviewSessionPage" class="header">
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
        <el-main class="main" :class="{ 'main-full': isInterviewSessionPage }">
          <el-scrollbar class="main-scrollbar" always :class="{ 'main-scrollbar-full': isInterviewSessionPage }">
            <div class="main-inner" :class="{ 'main-inner-full': isInterviewSessionPage }">
              <router-view v-slot="{ Component }">
                <transition :name="transitionName" mode="out-in">
                  <component :is="Component" />
                </transition>
              </router-view>
            </div>
          </el-scrollbar>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessageBox, ElMessage } from 'element-plus';
import {
  User,
  SwitchButton,
  ArrowDown,
} from '@element-plus/icons-vue';
import { useUserStore } from '@/store/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const transitionName = ref('fade');

const FLOW_ROUTES = new Set(['InterviewSettings', 'InterviewSession']);

const isInterviewSessionPage = computed(() => route.name === 'InterviewSession');

const avatarSrc = computed(() => userStore.userInfo?.avatarUrl || undefined);

const avatarText = computed(() => {
  const name = userStore.userInfo?.username;
  if (!name) return '?';
  return name.length >= 2 ? name.slice(0, 2) : name;
});

watch(
  () => route.name,
  (to, from) => {
    const toName = String(to || '');
    const fromName = String(from || '');
    const toInFlow = FLOW_ROUTES.has(toName);
    const fromInFlow = FLOW_ROUTES.has(fromName);

    // 面试流程页进入：从右往左淡入；返回离开：反向
    if (toInFlow && !fromInFlow) {
      transitionName.value = 'slide-left-fade';
      return;
    }
    if (!toInFlow && fromInFlow) {
      transitionName.value = 'slide-right-fade';
      return;
    }
    if (fromName === 'InterviewSettings' && toName === 'InterviewSession') {
      transitionName.value = 'slide-left-fade';
      return;
    }
    if (fromName === 'InterviewSession' && toName === 'InterviewSettings') {
      transitionName.value = 'slide-right-fade';
      return;
    }
    transitionName.value = 'fade';
  },
  { immediate: true }
);

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
  background-color: #fafafa;
  position: relative;
}
.home-layout > .el-container {
  height: 100%;
  min-height: 0;
}
.main-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.main-wrapper-full { width: 100%; }
.header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  background: #ffffff;
  border-bottom: 1px solid #ebeef5;
  backdrop-filter: saturate(120%) blur(3px);
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
  background: transparent;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.main-scrollbar {
  flex: 1;
  min-height: 0;
}
.main-scrollbar :deep(.el-scrollbar__wrap) {
  overflow-x: hidden;
}
.main-inner {
  padding: 20px;
}
.main-inner-full {
  padding: 0;
  height: 100%;
}
.main-full { height: 100%; }
.main-scrollbar-full,
.main-scrollbar-full :deep(.el-scrollbar__wrap),
.main-scrollbar-full :deep(.el-scrollbar__view) {
  height: 100%;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-left-fade-enter-active,
.slide-left-fade-leave-active,
.slide-right-fade-enter-active,
.slide-right-fade-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.slide-left-fade-enter-from {
  opacity: 0;
  transform: translateX(28px);
}

.slide-left-fade-leave-to {
  opacity: 0;
  transform: translateX(-28px);
}

.slide-right-fade-enter-from {
  opacity: 0;
  transform: translateX(-28px);
}

.slide-right-fade-leave-to {
  opacity: 0;
  transform: translateX(28px);
}
</style>
