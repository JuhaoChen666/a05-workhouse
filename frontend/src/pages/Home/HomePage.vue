<template>
  <div class="home-page">
    <el-container>
      <el-header class="header">
        <div class="left">
          <span class="logo">AI 面试平台</span>
        </div>
        <div class="right">
          <span class="username" v-if="userStore.userInfo">
            欢迎，{{ userStore.userInfo.username }}
          </span>
          <el-button type="text" @click="onLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <el-card>
          <h2>首页</h2>
          <p>这里可以作为 AI 面试平台的主控制台，例如展示面试记录、启动新面试等。</p>
          <el-button type="primary">开始一场新的面试（占位按钮）</el-button>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { ElMessageBox, ElMessage } from 'element-plus';

const router = useRouter();
const userStore = useUserStore();

const onLogout = () => {
  // 简单的确认退出提示
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    type: 'warning',
  })
    .then(() => {
      userStore.logout();
      ElMessage.success('已退出登录');
      router.push({ name: 'Login' });
    })
    .catch(() => {});
};
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.logo {
  font-weight: bold;
}
.username {
  margin-right: 16px;
}
.main {
  padding-top: 16px;
}
</style>