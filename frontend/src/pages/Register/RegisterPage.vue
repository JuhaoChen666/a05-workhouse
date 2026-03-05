<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2 class="title">注册</h2>
      <!-- 注册表单 -->
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" @keyup.enter="onSubmit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item v-if="form.email" label="验证码" prop="emailCode">
          <div class="code-row">
            <el-input v-model="form.emailCode" placeholder="请输入验证码" class="code-input" />
            <el-button
              class="code-btn"
              :disabled="sendCodeLoading || !form.email || !!sendCodeTimer"
              @click="onSendRegisterCode"
            >
              {{ sendCodeText }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">注册</el-button>
          <el-button type="text" @click="goLogin">已有账号？去登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { registerApi, sendCodeApi } from '@/api/auth';
import { throttle } from '@/utils/throttle';

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
  if (!form.email || sendCodeLoading.value || sendCodeTimer) return;
  // 先校验邮箱格式
  await formRef.value?.validateField('email').catch(() => {});
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return;
  sendCodeLoading.value = true;
  try {
    await sendCodeApi({ scene: 'register', email: form.email });
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
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}
.auth-card {
  width: 400px;
}
.title {
  text-align: center;
  margin-bottom: 16px;
}
.code-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.code-input {
  flex: 1;
}
.code-btn {
  white-space: nowrap;
  padding: 0 12px;
}
</style>