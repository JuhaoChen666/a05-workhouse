<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2 class="title">找回密码</h2>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="如未绑定邮箱，请先在此填写并绑定" />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input v-model="form.code" placeholder="请输入验证码" class="code-input" />
            <el-button
              class="code-btn"
              :disabled="sendCodeLoading || !form.username || !!timer"
              @click="onSendCode"
            >
              {{ sendCodeText }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="form.newPassword" type="password" placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">确认重置</el-button>
          <el-button type="text" @click="goLogin">返回登录</el-button>
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
import { sendCodeApi, verifyCodeResetApi } from '@/api/auth';

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
    ElMessage.success('验证码已发送，请查收（示例中在后端日志中查看）');
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
}
.auth-card {
  width: 420px;
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

