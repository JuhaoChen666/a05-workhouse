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
            <el-icon class="logo-icon"><Platform /></el-icon>
            <span class="logo-text">AI 面试官</span>
          </div>
          <h2 class="title">创建您的账号</h2>
          <p class="subtitle">免费注册，开启您的智能面试之旅</p>
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
              placeholder="请设置用户名" 
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
              placeholder="请设置密码" 
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
              placeholder="请再次确认密码" 
              size="large"
              show-password
            >
              <template #prefix>
                <el-icon><Select /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item prop="email">
            <el-input 
              v-model="form.email" 
              placeholder="请输入您的邮箱" 
              size="large"
            >
              <template #prefix>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item v-if="form.email" prop="emailCode">
            <div class="code-row">
              <el-input 
                v-model="form.emailCode" 
                placeholder="邮箱验证码" 
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
                :disabled="sendCodeLoading || !form.username?.trim() || !form.email || !!sendCodeTimer"
                @click="onSendRegisterCode"
              >
                {{ sendCodeText }}
              </el-button>
            </div>
          </el-form-item>
          
          <div class="form-actions">
            <el-button 
              class="submit-btn" 
              type="primary" 
              size="large" 
              :loading="loading" 
              @click="onSubmit"
            >
              注册
            </el-button>
            <div class="footer-links">
              <span class="hint-text">已有账号？</span>
              <el-button class="link-btn" type="primary" link @click="goLogin">
                立即登录
              </el-button>
            </div>
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
import { registerApi, sendCodeApi } from '@/api/auth';
import { throttle } from '@/utils/throttle';
import { 
  Platform, ArrowLeft, User, Lock, Message, Key, Select
} from '@element-plus/icons-vue';

const router = useRouter();
const formRef = ref<FormInstance>();
const loading = ref(false);
const sendCodeLoading = ref(false);
const sendCodeText = ref('发送验证码');
let sendCodeTimer: number | null = null;

// 表单数据
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  emailCode: '',
});

// 校验规则（包含确认密码和邮箱验证码校验）
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback();
          return;
        }
        const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
        if (!ok) {
          callback(new Error('邮箱格式不正确'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
  emailCode: [
    {
      validator: (_rule, value, callback) => {
        if (!form.email) {
          callback();
          return;
        }
        if (!value) {
          callback(new Error('请输入邮箱验证码'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
};

const onSendRegisterCode = async () => {
  if (!form.username?.trim() || !form.email || sendCodeLoading.value || sendCodeTimer) return;
  await formRef.value?.validateField('username').catch(() => {});
  await formRef.value?.validateField('email').catch(() => {});
  if (!form.username.trim()) {
    ElMessage.warning('请先填写用户名');
    return;
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return;
  sendCodeLoading.value = true;
  try {
    await sendCodeApi({
      scene: 'register',
      email: form.email,
      username: form.username.trim(),
    });
    ElMessage.success('验证码已发送到邮箱，请查收');
    let left = 60;
    sendCodeText.value = `${left}s 后可重发`;
    if (sendCodeTimer) window.clearInterval(sendCodeTimer);
    sendCodeTimer = window.setInterval(() => {
      left -= 1;
      if (left <= 0) {
        if (sendCodeTimer) window.clearInterval(sendCodeTimer);
        sendCodeText.value = '发送验证码';
        sendCodeTimer = null;
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

const doSubmit = () => {
  if (loading.value) return;
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await registerApi(form as any);
      ElMessage.success('注册成功，请登录');
      router.push({ name: 'Login' });
    } catch (e: any) {
      ElMessage.error(e.message || '注册失败');
    } finally {
      loading.value = false;
    }
  });
};

const onSubmit = throttle(doSubmit, 500);

const goLogin = () => {
  router.push({ name: 'Login' });
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

.footer-links {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
}

.hint-text {
  color: #6b7280;
}

.link-btn {
  color: #9333ea;
  font-weight: 600;
  font-size: 14px;
}

.link-btn:hover {
  color: #7e22ce;
}
</style>