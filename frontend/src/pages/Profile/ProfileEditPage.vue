<template>
  <div class="profile-edit-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">账号与安全设置 <span>Account</span></h2>
      <div class="theme-section-decoration"></div>
    </div>

    <!-- 头像与基本信息 -->
    <el-card class="section-card theme-card fade-in-up delay-1" shadow="hover">
      <template #header><span>头像与基本信息</span></template>
      <div class="profile-header" v-if="profile">
        <div class="avatar-area">
          <el-avatar :size="80" :src="avatarFullUrl" class="avatar">
            {{ profile.username.slice(0, 2) || '?' }}
          </el-avatar>
          <el-upload
            class="avatar-upload"
            :show-file-list="false"
            :http-request="handleAvatarUpload"
            accept="image/*"
          >
            <el-button size="small" type="primary">修改头像</el-button>
          </el-upload>
        </div>
        <div class="profile-form">
          <el-form label-width="80px">
            <el-form-item label="用户名">{{ profile.username }}</el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profile.email" placeholder="找回密码时将使用该邮箱" disabled />
            </el-form-item>
          </el-form>
          <div class="tip">如需绑定或修改邮箱，请通过找回密码流程补充/更新邮箱。</div>
        </div>
      </div>
      <el-empty v-else description="加载中..." :image-size="60" />
    </el-card>

    <!-- 修改密码（需要邮箱验证码） -->
    <el-card class="section-card theme-card fade-in-up delay-2" shadow="hover">
      <template #header><span>修改密码</span></template>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="110px">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" placeholder="请输入原密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
        <el-form-item label="邮箱验证码" prop="code">
          <div class="code-row">
            <el-input v-model="pwdForm.code" placeholder="请输入验证码" class="code-input" />
            <el-button
              class="code-btn"
              :disabled="sendCodeLoading || !!codeTimer || !profile"
              @click="onSendCode"
            >
              {{ sendCodeText }}
            </el-button>
          </div>
          <template #error>
            <div class="tip">请先在个人中心或找回密码流程中绑定邮箱。</div>
          </template>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwdLoading" @click="onSubmitPassword">确认修改</el-button>
          <el-button @click="goBack">返回个人中心</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { getProfileApi, uploadAvatarApi, changePasswordApi, sendCodeApi, type ChangePasswordRequest } from '@/api/auth';
import type { UserInfo } from '@/types/auth';
import { useUserStore } from '@/store/user';

const router = useRouter();
const userStore = useUserStore();

const profile = ref<UserInfo | null>(null);
const pwdFormRef = ref<FormInstance>();
const pwdLoading = ref(false);
const sendCodeLoading = ref(false);
const sendCodeText = ref('发送验证码');
let codeTimer: number | null = null;

const avatarFullUrl = computed(() => profile.value?.avatarUrl || userStore.userInfo?.avatarUrl || '');

const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  code: '',
});

const pwdRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, v, cb) => (v !== pwdForm.newPassword ? cb(new Error('两次输入不一致')) : cb()),
      trigger: 'blur',
    },
  ],
  code: [{ required: true, message: '请输入邮箱验证码', trigger: 'blur' }],
};

async function loadProfile() {
  try {
    const res = await getProfileApi();
    profile.value = res;
    if (res?.avatarUrl) {
      userStore.setUserInfo({ ...userStore.userInfo!, avatarUrl: res.avatarUrl });
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取用户信息失败');
  }
}

async function handleAvatarUpload({ file }: { file: File }) {
  const form = new FormData();
  form.append('file', file);
  try {
    const res = await uploadAvatarApi(form);
    if (res?.avatarUrl) {
      profile.value = { ...profile.value!, avatarUrl: res.avatarUrl };
      userStore.setUserInfo({ ...userStore.userInfo!, avatarUrl: res.avatarUrl });
      ElMessage.success('头像已更新');
    }
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败');
  }
}

const onSendCode = async () => {
  if (!profile.value || sendCodeLoading.value || codeTimer) return;
  if (!profile.value.email) {
    ElMessage.warning('请先绑定邮箱后再获取验证码，可通过找回密码流程绑定邮箱。');
    return;
  }
  sendCodeLoading.value = true;
  try {
    await sendCodeApi({
      scene: 'reset',
      username: profile.value.username,
      email: profile.value.email || undefined,
    });
    ElMessage.success('验证码已发送，请查收（示例中在后端日志中查看）');
    let left = 60;
    sendCodeText.value = `${left}s 后可重发`;
    if (codeTimer) window.clearInterval(codeTimer);
    codeTimer = window.setInterval(() => {
      left -= 1;
      if (left <= 0) {
        if (codeTimer) window.clearInterval(codeTimer);
        sendCodeText.value = '发送验证码';
        codeTimer = null;
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

function onSubmitPassword() {
  pwdFormRef.value?.validate(async (valid) => {
    if (!valid) return;
    pwdLoading.value = true;
    try {
      await changePasswordApi(pwdForm as unknown as ChangePasswordRequest);
      ElMessage.success('密码已修改，请重新登录');
      pwdForm.oldPassword = '';
      pwdForm.newPassword = '';
      pwdForm.confirmPassword = '';
      pwdForm.code = '';
    } catch (e: any) {
      ElMessage.error(e.message || '修改密码失败');
    } finally {
      pwdLoading.value = false;
    }
  });
}

function goBack() {
  router.push({ name: 'Profile' });
}

onMounted(() => {
  loadProfile();
});
</script>

<style scoped>
.profile-edit-page { max-width: 1000px; }
.section-card {
  margin-bottom: 16px;
}
.profile-header {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.avatar-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.avatar-upload {
  margin-top: 4px;
}
.profile-form {
  flex: 1;
}
.tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
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

