<template>
  <section class="resume-page fade-in-up delay-1">
    <div class="resume-toolbar theme-card">
      <p>支持上传、在线编辑与管理。</p>
      <div class="resume-upload-area">
        <el-upload
          :show-file-list="false"
          :auto-upload="false"
          accept=".pdf,application/pdf"
          :on-change="handleResumeFileChange"
        >
          <el-button type="primary" class="theme-primary-btn">上传简历</el-button>
        </el-upload>
        <span class="resume-upload-tip">*仅支持pdf格式文件</span>
      </div>
    </div>

    <el-table :data="resumeList" stripe>
      <el-table-column prop="name" label="文件名" min-width="280" show-overflow-tooltip />
      <el-table-column prop="updatedAt" label="更新时间" width="180" />
      <el-table-column prop="content" label="摘要">
        <template #default="{ row }">
          {{ row.content.slice(0, 60) || '暂无内容' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="removeResume(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="resumeList.length === 0" description="暂无简历，请先上传" :image-size="72" />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { uploadResumeApi } from '@/api/resume';
import { useUserStore } from '@/store/user';

type ResumeItem = { id: number; name: string; content: string; updatedAt: string };
const resumeList = ref<ResumeItem[]>([]);
const userStore = useUserStore();
const LOCAL_KEY = 'user_resume_list_v1';

function nowText() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function handleResumeFileChange(file: { name?: string; raw?: File }) {
  const raw = file.raw;
  const filename = String(file?.name || '').trim().toLowerCase();
  const isPdf = filename.endsWith('.pdf') || raw?.type === 'application/pdf';
  if (!isPdf) {
    ElMessage.error('仅支持上传 PDF 格式简历');
    return;
  }
  if (!raw) {
    ElMessage.error('上传文件无效');
    return;
  }
  const userId = userStore.userInfo?.id;
  if (!userId) {
    ElMessage.error('未获取到用户信息，请重新登录后重试');
    return;
  }
  uploadResumeApi(userId, raw)
    .then((res) => {
      const item: ResumeItem = {
        id: Number(res?.id ?? Date.now()),
        name: String(res?.filename || file?.name || '未命名简历'),
        content: String(res?.text_preview || '简历已上传，暂无预览内容'),
        updatedAt: nowText(),
      };
      resumeList.value.unshift(item);
      ElMessage.success('简历上传成功');
    })
    .catch((e: unknown) => {
      ElMessage.error((e as Error).message || '简历上传失败');
    });
}

function removeResume(id: number) {
  resumeList.value = resumeList.value.filter((r) => r.id !== id);
  ElMessage.success('简历已删除');
}

onMounted(() => {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    if (!raw) return;
    const list = JSON.parse(raw) as ResumeItem[];
    if (Array.isArray(list)) resumeList.value = list;
  } catch {
    // ignore parse error
  }
});

watch(
  resumeList,
  (list) => {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(list));
  },
  { deep: true }
);
</script>

<style scoped>
.resume-page { display: grid; gap: clamp(10px, 1vw, 16px); }
.resume-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: clamp(14px, 1.2vw, 20px);
  gap: 12px;
  flex-wrap: wrap;
}
.resume-toolbar p {
  margin: 0;
  color: #6b7280;
  font-size: clamp(12px, 0.9vw, 14px);
}
.resume-upload-area {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-direction: column;
  gap: 0;
}
.resume-upload-tip {
  width: max-content;
  position: absolute;
  font-size: clamp(10px, 0.8vw, 12px);
  color: #909399;
  top: 110%;
}
</style>
