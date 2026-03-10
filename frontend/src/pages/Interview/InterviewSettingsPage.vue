<template>
  <div class="interview-settings-page">
    <el-card class="settings-card" shadow="hover" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>面试设置</span>
          <el-button type="primary" link @click="backToJobDetail">
            返回岗位详情
          </el-button>
        </div>
      </template>

      <template v-if="job">
        <div class="job-brief">
          <div class="job-title-row">
            <span class="job-name">{{ job.name }}</span>
            <span class="company-name">{{ job.companyName }}</span>
          </div>
          <div class="salary">
            {{ (job.salaryMin / 1000).toFixed(0) }}k -
            {{ (job.salaryMax / 1000).toFixed(0) }}k / 月
          </div>
        </div>

        <el-divider />

        <el-row :gutter="20">
          <!-- 左侧：简历上传/直接面试 -->
          <el-col :span="14">
            <h3>简历设置</h3>
            <p class="desc">
              可上传一份 PDF / Word 简历，用于后续简历分析与问答；也可以选择直接开始面试。
            </p>

            <el-radio-group v-model="mode" class="mode-radio-group">
              <el-radio label="withResume">上传简历后开始面试</el-radio>
              <el-radio label="noResume">不提交简历，直接面试</el-radio>
            </el-radio-group>

            <div
              v-if="mode === 'withResume'"
              class="upload-wrap"
            >
              <el-upload
                class="upload-block"
                drag
                :show-file-list="true"
                :limit="1"
                :auto-upload="false"
                :file-list="fileList"
                :on-change="handleFileChange"
                :before-remove="handleBeforeRemove"
                accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              >
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  将文件拖到此处或 <em>点击上传</em>
                </div>
                <div class="el-upload__tip">
                  仅支持 PDF / Word，大小建议不超过 5MB（后端上传接口可后续接入）
                </div>
              </el-upload>
            </div>
          </el-col>

          <!-- 右侧：简历优化入口 -->
          <el-col :span="10">
            <h3>简历优化（预留）</h3>
            <p class="desc">
              进入简历优化工具，对现有简历进行结构化调整和用词润色，再返回本页开始模拟面试。
            </p>
            <el-button type="primary" plain @click="goResumeOptimize">
              打开简历优化页面（占位）
            </el-button>
          </el-col>
        </el-row>

        <el-divider />

        <div class="actions">
          <el-button @click="backToJobDetail">返回岗位详情</el-button>
          <el-button type="primary" @click="startInterview">
            开始面试
          </el-button>
        </div>
      </template>

      <el-empty
        v-else-if="!loading"
        description="岗位不存在或已下线"
        :image-size="80"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { UploadFile, UploadFiles } from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { useRoute, useRouter } from 'vue-router';
import { getJobDetailApi, type HotJobItem } from '@/api/jobs';

// 路由对象
const route = useRoute();
const router = useRouter();

// 状态：岗位与加载
const loading = ref<boolean>(true);
const job = ref<HotJobItem | null>(null);

// 状态：简历模式和文件
const mode = ref<'withResume' | 'noResume'>('withResume');
const fileList = ref<UploadFiles>([]);

// 返回岗位详情页
function backToJobDetail() {
  const id = route.params.id;
  if (id) {
    router.push({ name: 'JobDetail', params: { id: String(id) } });
  } else {
    router.push({ name: 'Home' });
  }
}

// 进入简历优化页面（占位路由，后续可替换为真实地址）
function goResumeOptimize() {
  ElMessage.info('简历优化页面暂未实现，可在后续迭代中接入。');
}

// 处理文件选择
function handleFileChange(_file: UploadFile, fileListInner: UploadFiles) {
  fileList.value = fileListInner;
}

// 删除文件前确认
function handleBeforeRemove(file: UploadFile) {
  return ElMessageBox.confirm(`确定移除文件「${file.name}」吗？`, '提示', {
    type: 'warning',
  });
}

// 开始面试：这里仅进行前端流程跳转，面试页面逻辑后续扩展
function startInterview() {
  if (mode.value === 'withResume' && fileList.value.length === 0) {
    ElMessage.warning('请先上传简历，或选择“不提交简历，直接面试”。');
    return;
  }
  const id = route.params.id;
  if (!id) {
    ElMessage.error('缺少岗位 ID');
    return;
  }

  // 此处暂不真正上传简历和创建面试记录，后续可在此处接入后端接口
  router.push({
    name: 'InterviewSession',
    params: { id: String(id) },
    query: {
      withResume: mode.value === 'withResume' ? '1' : '0',
    },
  });
}

onMounted(async () => {
  const id = Number(route.params.id);
  if (!id) {
    loading.value = false;
    ElMessage.error('缺少岗位 ID');
    return;
  }
  try {
    const res = await getJobDetailApi(id);
    job.value = res;
  } catch {
    job.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.interview-settings-page {
  max-width: 960px;
  margin: 0 auto;
}
.settings-card {
  width: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.job-brief {
  margin-bottom: 8px;
}
.job-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.job-name {
  font-weight: 600;
}
.company-name {
  font-size: 13px;
  color: #909399;
}
.salary {
  color: #e6a23c;
  font-weight: 500;
}
.desc {
  font-size: 13px;
  color: #606266;
  margin: 4px 0 12px;
}
.mode-radio-group {
  margin-bottom: 12px;
}
.upload-wrap {
  max-width: 420px;
}
.upload-block {
  width: 100%;
}
.upload-icon {
  font-size: 32px;
  color: #409eff;
  margin-bottom: 8px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

