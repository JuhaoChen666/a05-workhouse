<template>
  <div class="profile-edit-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">账号与安全设置 <span>Account</span></h2>
      <div class="theme-section-decoration"></div>
    </div>

    <!-- 头像设置（独立于 profile 请求，可直接上传） -->
    <el-card class="section-card theme-card fade-in-up delay-1" shadow="hover">
      <template #header><span>头像设置</span></template>
      <div class="profile-header">
        <div class="avatar-area">
          <el-avatar :size="80" :src="avatarFullUrl" class="avatar">
            {{ displayUsername.slice(0, 2) || '?' }}
          </el-avatar>
          <el-upload
            class="avatar-upload"
            :show-file-list="false"
            :http-request="handleAvatarUpload"
            accept="image/*"
          >
            <el-button size="small" type="primary">修改头像</el-button>
          </el-upload>
          <div class="tip">头像大小不超过 10MB</div>
        </div>
      </div>
    </el-card>

    <!-- 基本信息（单独加载状态，不影响头像上传） -->
    <el-card class="section-card theme-card fade-in-up delay-1" shadow="hover">
      <template #header><span>基本信息</span></template>
      <div v-if="profileLoading" class="info-loading">基本信息加载中...</div>
      <div v-else-if="displayProfile" class="profile-form">
        <el-form label-width="80px">
          <el-form-item label="用户名">{{ displayProfile.username }}</el-form-item>
          <el-form-item label="邮箱">
            <el-input :model-value="displayProfile.email || ''" placeholder="找回密码时将使用该邮箱" disabled />
          </el-form-item>
        </el-form>
        <div class="tip">如需绑定或修改邮箱，请通过找回密码流程补充/更新邮箱。</div>
      </div>
      <el-empty v-else description="未获取到基本信息，请稍后重试" :image-size="60" />
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
              :disabled="sendCodeLoading || !!codeTimer || !profileInfo"
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
import { onMounted, reactive, ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import {
  getProfileAvatarApi,
  getProfileInfoApi,
  uploadAvatarApi,
  changePasswordApi,
  sendCodeApi,
  type ChangePasswordRequest,
} from '@/api/auth';
import type { UserInfo } from '@/types/auth';
import { useUserStore } from '@/store/user';
import { apiOrigin } from '@/api/request';

const router = useRouter();
const userStore = useUserStore();

const profileInfo = ref<Pick<UserInfo, 'id' | 'username' | 'email'> | null>(null);
const avatarProfile = ref<Pick<UserInfo, 'id' | 'username' | 'avatarUrl'> | null>(null);
const avatarLoading = ref(false);
const profileLoading = ref(false);
const pwdFormRef = ref<FormInstance>();
const pwdLoading = ref(false);
const sendCodeLoading = ref(false);
const sendCodeText = ref('发送验证码');
let codeTimer: number | null = null;
const avatarBust = ref(0);

const displayProfile = computed(() => profileInfo.value || userStore.userInfo || null);
const displayUsername = computed(
  () => avatarProfile.value?.username || profileInfo.value?.username || userStore.userInfo?.username || '用户'
);
const avatarUrlRaw = computed(() =>
  String(avatarProfile.value?.avatarUrl || userStore.userInfo?.avatarUrl || '').trim()
);
const avatarFullUrl = computed(() => {
  if (!avatarUrlRaw.value) return '';
  const full =
    avatarUrlRaw.value.startsWith('http') || avatarUrlRaw.value.startsWith('/img/')
      ? avatarUrlRaw.value
      : `${apiOrigin}${avatarUrlRaw.value}`;
  const sep = full.includes('?') ? '&' : '?';
  return `${full}${sep}v=${avatarBust.value}`;
});

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

async function loadProfileInfo() {
  profileLoading.value = true;
  try {
    const res = await getProfileInfoApi();
    profileInfo.value = res;
  } catch (e: any) {
    ElMessage.error(e.message || '获取基本信息失败');
  } finally {
    profileLoading.value = false;
  }
}

async function loadAvatarProfile() {
  avatarLoading.value = true;
  try {
    const res = await getProfileAvatarApi();
    avatarProfile.value = res;
    if (res?.avatarUrl && userStore.userInfo) {
      userStore.setUserInfo({ ...userStore.userInfo, avatarUrl: res.avatarUrl });
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取头像信息失败');
  } finally {
    avatarLoading.value = false;
  }
}

async function handleAvatarUpload({ file }: { file: File }) {
  const MAX_AVATAR_SIZE = 10 * 1024 * 1024;
  if (file.size > MAX_AVATAR_SIZE) {
    ElMessage.warning('头像大小不能超过 10MB');
    return;
  }
  const form = new FormData();
  form.append('file', file);
  const userId = avatarProfile.value?.id || profileInfo.value?.id || userStore.userInfo?.id;
  if (!userId) {
    ElMessage.error('未获取到用户ID，无法上传头像');
    return;
  }
  try {
    const res = await uploadAvatarApi(userId, form);
    if (res?.avatarUrl) {
      avatarProfile.value = {
        id: String(userId),
        username: displayUsername.value,
        avatarUrl: res.avatarUrl,
      };
      if (userStore.userInfo) {
        userStore.setUserInfo({ ...userStore.userInfo, avatarUrl: res.avatarUrl });
      }
      ElMessage.success('头像已更新');
    }
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败');
  }
}

const onSendCode = async () => {
  if (!profileInfo.value || sendCodeLoading.value || codeTimer) return;
  if (!profileInfo.value.email) {
    ElMessage.warning('请先绑定邮箱后再获取验证码，可通过找回密码流程绑定邮箱。');
    return;
  }
  sendCodeLoading.value = true;
  try {
    await sendCodeApi({
      scene: 'reset',
      username: profileInfo.value.username,
      email: profileInfo.value.email || undefined,
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
  void loadAvatarProfile();
  void loadProfileInfo();
});

watch(
  () => avatarUrlRaw.value,
  () => {
    avatarBust.value = Date.now();
  },
  { immediate: true }
);
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
.info-loading {
  color: #6b7280;
  font-size: 13px;
  padding: 4px 0;
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

