<template>
  <div class="auth-page">
    <!-- Textured Background -->
    <div class="bg-pattern"></div>
    <div class="bg-layer"></div>

    <div class="auth-container">
      <div class="back-link" @click="goLanding">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回首页</span>
      </div>

      <div class="auth-card">
        <div class="auth-header">
          <div class="logo">
            <img :src="loginBrandLogo" alt="" class="logo-img" role="presentation" />
            <span class="logo-text">面智通途</span>
          </div>
          <h2 class="title">欢迎回来</h2>
          <p class="subtitle">登录您的账号，继续智能面试之旅</p>
        </div>

        <el-form 
          :model="form" 
          :rules="rules" 
          ref="formRef" 
          class="auth-form"
          @keyup.enter="onSubmit"
        >
          <el-form-item prop="username">
            <el-input 
              v-model="form.username" 
              placeholder="请输入用户名" 
              size="large"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input 
              v-model="form.password" 
              type="password" 
              placeholder="请输入密码" 
              size="large"
              show-password
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <div class="form-actions">
            <el-button 
              class="submit-btn" 
              type="primary" 
              size="large" 
              :loading="loading" 
              @click="onSubmit"
            >
              登录
            </el-button>
            <div class="footer-links">
              <el-button class="link-btn" type="primary" link @click="goRegister">
                没有账号？去注册
              </el-button>
              <span class="divider"></span>
              <el-button class="link-btn" type="primary" link @click="goForgot">
                忘记密码？
              </el-button>
            </div>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { loginApi, getProfileApi } from '@/api/auth';
import { syncUserAvatarFromAdminApi } from '@/utils/syncUserAvatar';
import { useUserStore } from '@/store/user';
import { throttle } from '@/utils/throttle';
import { ArrowLeft, User, Lock } from '@element-plus/icons-vue';
import loginBrandLogo from '@/assets/logo2 .webp';

const router = useRouter();
const userStore = useUserStore();

const formRef = ref<FormInstance>();
const loading = ref(false);

// 表单数据
const form = reactive({
  username: '',
  password: '',
});

// 简单校验规则
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};


// 实际提交逻辑（节流包装前）
const doSubmit = () => {
  if (loading.value) return;
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await loginApi(form);
      userStore.setToken(res.token);
      if (res.user) {
        userStore.setUserInfo(res.user);
      } else {
        try {
          const profile = await getProfileApi();
          userStore.setUserInfo(profile);
        } catch {
          /* 仅有 token 时也允许进入首页 */
        }
      }
      await syncUserAvatarFromAdminApi();
      ElMessage.success('登录成功');
      await nextTick();
      await router.replace({ name: 'Home' }).catch(() => {});
    } catch (e: any) {
      ElMessage.error(e.message || '登录失败');
    } finally {
      loading.value = false;
    }
  });
};

// 节流：500ms 内多次点击/回车只触发一次
const onSubmit = throttle(doSubmit, 500);

const goRegister = () => {
  router.push({ name: 'Register' });
};

const goForgot = () => {
  router.push({ name: 'ForgotPassword' });
};
const goLanding = () => {
  router.push({ name: 'Landing' });
};
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #fafafa;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  position: relative;
  overflow: hidden;
}

/* --- Textured Background --- */
.bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background-image: radial-gradient(#d1d5db 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.5;
  pointer-events: none;
}

.bg-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle at 80% -10%, rgba(147, 51, 234, 0.15) 0%, transparent 50%),
              radial-gradient(circle at 20% 110%, rgba(59, 130, 246, 0.1) 0%, transparent 40%);
}

.auth-container {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  padding: 0 20px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 24px;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s ease;
}

.back-link:hover {
  color: #111827;
}

.auth-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0,0,0,0.02);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.logo-img {
  display: block;
  max-height: 48px;
  width: auto;
  max-width: min(160px, 40vw);
  object-fit: contain;
  flex-shrink: 0;
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.02em;
  line-height: 1.2;
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.subtitle {
  font-size: 14px;
  color: #6b7280;
}

.auth-form {
  margin-top: 20px;
}

.auth-form :deep(.el-input__wrapper) {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), inset 0 0 0 1px #e5e7eb;
  padding: 1px 11px;
  border-radius: 8px;
  background-color: #f9fafb;
  transition: all 0.2s ease;
}

.auth-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), inset 0 0 0 1px #d1d5db;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  background-color: #ffffff;
  box-shadow: 0 0 0 2px rgba(147, 51, 234, 0.2), inset 0 0 0 1px #9333ea;
}

.auth-form :deep(.el-input__inner) {
  color: #111827;
  height: 44px;
}

.form-actions {
  margin-top: 32px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(180deg, #1f2937, #000000);
  border: 1px solid #000000;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}

.submit-btn:hover {
  background: #333333;
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.15);
  border-color: #333;
}

.footer-links {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.link-btn {
  color: #6b7280;
  font-weight: 500;
  font-size: 14px;
  transition: color 0.2s;
}

.link-btn:hover {
  color: #111827;
}

.divider {
  display: inline-block;
  width: 1px;
  height: 14px;
  background: #e5e7eb;
  margin: 0 16px;
}
</style>