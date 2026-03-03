<template>
  <div class="landing">
    <header class="landing-header">
      <div class="logo">AI 面试平台</div>
      <div class="actions">
        <el-button type="primary" @click="goLogin">登录</el-button>
        <el-button @click="goRegister">注册</el-button>
      </div>
    </header>

    <main class="landing-main">
      <section class="hero">
        <h1>提升你的面试成功率</h1>
        <p>通过 AI 模拟真实技术面试，获取客观反馈与改进建议。</p>
        <el-button type="primary" size="large" @click="goLogin">
          立即开始
        </el-button>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const goLogin = () => {
  router.push({ name: 'Login' });
};

const goRegister = () => {
  router.push({ name: 'Register' });
};
</script>

<style scoped>
.landing {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.landing-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.logo {
  font-size: 20px;
  font-weight: bold;
}
.landing-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero {
  text-align: center;
  max-width: 600px;
}
.hero h1 {
  font-size: 32px;
  margin-bottom: 16px;
}
.hero p {
  color: #666;
  margin-bottom: 24px;
}
</style>