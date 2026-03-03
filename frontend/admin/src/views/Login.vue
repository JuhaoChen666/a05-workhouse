<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">AI 面试平台 · 管理后台</h1>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="onSubmit">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <p class="tip">请使用管理员账号登录（角色为「管理员」方可访问）</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import { loginApi } from '@/api/auth';
import { useUserStore } from '@/store/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: '',
  password: '',
});

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

const onSubmit = async () => {
  if (loading.value) return;
  await formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await loginApi(form);
      userStore.setToken(res.token);
      userStore.setUserInfo(res.user);
      if (res.user.roleId !== 2) {
        ElMessage.warning('当前账号非管理员，部分功能将不可用');
      }
      ElMessage.success('登录成功');
      const redirect = (route.query.redirect as string) || '/';
      router.push(redirect);
    } catch (e: unknown) {
      ElMessage.error((e as Error).message || '登录失败');
    } finally {
      loading.value = false;
    }
  });
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-card {
  width: 380px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.title {
  margin: 0 0 28px;
  font-size: 20px;
  text-align: center;
  color: #1a1a2e;
}

.tip {
  margin: 16px 0 0;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
</style>
