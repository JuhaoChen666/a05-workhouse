<template>
  <div class="auth-page">
    <!-- Textured Background -->
    <div class="bg-pattern"></div>
    <div class="bg-layer"></div>

    <div class="auth-container">
      <div class="back-link" @click="goLogin">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回登录</span>
      </div>

      <div class="auth-card">
        <div class="auth-header">
          <div class="logo">
            <el-icon class="logo-icon"><Platform /></el-icon>
            <span class="logo-text">AI 面试官</span>
          </div>
          <h2 class="title">找回密码</h2>
          <p class="subtitle">请输入相关信息以重置您的密码</p>
        </div>

        <el-form 
          :model="form" 
          :rules="rules" 
          ref="formRef" 
          class="auth-form"
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
          
          <el-form-item prop="email">
            <el-input 
              v-model="form.email" 
              placeholder="如未绑定邮箱，请填入邮箱以验证" 
              size="large"
            >
              <template #prefix>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item prop="code">
            <div class="code-row">
              <el-input 
                v-model="form.code" 
                placeholder="请输入验证码" 
                class="code-input"
                size="large"
              >
                <template #prefix>
                  <el-icon><Key /></el-icon>
                </template>
              </el-input>
              <el-button
                class="code-btn"
                size="large"
                :disabled="sendCodeLoading || !form.username || !!timer"
                @click="onSendCode"
              >
                {{ sendCodeText }}
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item prop="newPassword">
            <el-input 
              v-model="form.newPassword" 
              type="password" 
              placeholder="请输入新密码" 
              size="large"
              show-password
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item prop="confirmPassword">
            <el-input 
              v-model="form.confirmPassword" 
              type="password" 
              placeholder="请再次确认新密码" 
              size="large"
              show-password
            >
              <template #prefix>
                <el-icon><Select /></el-icon>
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
              确认重置
            </el-button>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { sendCodeApi, verifyCodeResetApi } from '@/api/auth';
import { 
  Platform, ArrowLeft, User, Message, Key, Lock, Select
} from '@element-plus/icons-vue';

const router = useRouter();
const formRef = ref<FormInstance>();
const loading = ref(false);
const sendCodeLoading = ref(false);
const sendCodeText = ref('发送验证码');
let timer: number | null = null;

const form = reactive({
  username: '',
  email: '',
  code: '',
  newPassword: '',
  confirmPassword: '',
});

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback();
          return;
        }
        const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
        if (!ok) callback(new Error('邮箱格式不正确'));
        else callback();
      },
      trigger: 'blur',
    },
  ],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.newPassword) callback(new Error('两次输入的密码不一致'));
        else callback();
      },
      trigger: 'blur',
    },
  ],
};

const onSendCode = async () => {
  if (!form.username || sendCodeLoading.value || timer) return;
  sendCodeLoading.value = true;
  try {
    await sendCodeApi({
      scene: 'reset',
      username: form.username,
      email: form.email || undefined,
    });
    ElMessage.success('验证码已发送，请查收');
    let left = 60;
    sendCodeText.value = `${left}s 后可重发`;
    if (timer) window.clearInterval(timer);
    timer = window.setInterval(() => {
      left -= 1;
      if (left <= 0) {
        if (timer) window.clearInterval(timer);
        sendCodeText.value = '发送验证码';
        timer = null;
      } else {
        sendCodeText.value = `${left}s 后可重发`;
      }
    }, 1000);
  } catch (e: any) {
    ElMessage.error(e.message || '发送验证码失败');
  } finally {
    sendCodeLoading.value = false;
  }
};

const onSubmit = () => {
  if (loading.value) return;
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await verifyCodeResetApi({
        username: form.username,
        code: form.code,
        newPassword: form.newPassword,
        confirmPassword: form.confirmPassword,
      });
      ElMessage.success('密码重置成功，请使用新密码登录');
      router.push({ name: 'Login' });
    } catch (e: any) {
      ElMessage.error(e.message || '密码重置失败');
    } finally {
      loading.value = false;
    }
  });
};

const goLogin = () => {
  router.push({ name: 'Login' });
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
  gap: 8px;
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  letter-spacing: -0.5px;
  margin-bottom: 24px;
}

.logo-icon {
  font-size: 24px;
  color: #111827;
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

.code-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.code-input {
  flex: 1;
}

.code-btn {
  height: 46px;
  padding: 0 20px;
  border-radius: 8px;
  font-weight: 500;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #4b5563;
  transition: all 0.2s ease;
}

.code-btn:hover:not(:disabled) {
  color: #111827;
  background: #f9fafb;
  border-color: #d1d5db;
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
</style>

