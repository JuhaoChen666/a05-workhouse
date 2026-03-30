<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <el-button @click="goLanding">返回</el-button>
      <h2 class="title">登录</h2>
      <!-- 登录表单 -->
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" @keyup.enter="onSubmit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">登录</el-button>
          <el-button type="text" @click="goRegister">没有账号？去注册</el-button>
          <el-button type="text" @click="goForgot">忘记密码？</el-button>
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
import { loginApi } from '@/api/auth';
import { useUserStore } from '@/store/user';
import { throttle } from '@/utils/throttle';

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
      userStore.setUserInfo(res.user);
      ElMessage.success('登录成功');
      router.push({ name: 'Home' });
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
}
.auth-card {
  width: 400px;
}
.title {
  text-align: center;
  margin-bottom: 16px;
}
</style>