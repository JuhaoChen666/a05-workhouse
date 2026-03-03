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
import { registerApi } from '@/api/auth';
import { throttle } from '@/utils/throttle';

const router = useRouter();
const formRef = ref<FormInstance>();
const loading = ref(false);

// 表单数据
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
});

// 校验规则（包含确认密码校验）
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
};

const doSubmit = () => {
  if (loading.value) return;
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await registerApi(form);
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
</style>