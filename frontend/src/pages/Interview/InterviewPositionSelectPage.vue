<template>
  <div class="setup-page">
    <InterviewSetupProgress :active="1" />
    <div class="layout">
      <el-card class="theme-card left-card" shadow="hover">
        <el-form label-width="120px">
          <el-form-item label="是否使用简历">
            <el-switch v-model="useResume" />
          </el-form-item>

          <el-form-item v-if="useResume" label="个人简历：">
            <el-select v-model="selectedResumeId" placeholder="请选择个人简历" clearable style="width: 100%">
              <el-option
                v-for="item in resumeOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="岗位：" required>
            <el-autocomplete
              v-model="positionName"
              :fetch-suggestions="queryPositionSuggestions"
              clearable
              placeholder="请选择岗位"
              @select="onPositionSelect"
              :disabled="positionLockedByResume"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="工作：">
            <el-input
              v-model="jobKeyword"
              :placeholder="positionLockedByResume && !positionName ? '请先选择岗位' : '输入关键词搜索工作'"
              :disabled="positionLockedByResume && !positionName"
              clearable
            />
          </el-form-item>

          <div class="job-result-wrap">
            <el-empty
              v-if="positionLockedByResume && !positionName"
              description="请先选择岗位"
              :image-size="54"
            />
            <div v-else class="job-cards">
              <article
                v-for="job in filteredJobs"
                :key="job.id"
                class="job-card"
                :class="{ active: selectedJobId === job.id }"
                @click="selectJob(job)"
              >
                <h4>{{ job.name }}</h4>
                <p class="meta">{{ job.companyName }}</p>
                <p class="desc">{{ shorten(job.jobContent) }}</p>
              </article>
            </div>
            <el-empty
              v-if="!(positionLockedByResume && !positionName) && filteredJobs.length === 0"
              description="暂无匹配工作"
              :image-size="54"
            />
          </div>
        </el-form>
      </el-card>

      <el-card class="theme-card right-card" shadow="hover">
        <h3 class="detail-title">岗位详情</h3>
        <el-input
          v-model="positionDetail"
          type="textarea"
          :rows="16"
          placeholder="请输入岗位详情"
        />
      </el-card>
    </div>

    <div class="actions">
      <el-button @click="goPrev">上一步</el-button>
      <el-button type="primary" class="theme-primary-btn" @click="goNext">下一步</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { getHotJobsApi, searchJobsApi, type HotJobItem } from '@/api/jobs';
import { loadInterviewSetupDraft, saveInterviewSetupDraft } from './setupState';
import InterviewSetupProgress from './InterviewSetupProgress.vue';

const router = useRouter();
const draft = loadInterviewSetupDraft();
const LOCAL_KEY = 'user_resume_list_v1';

const useResume = ref(Boolean(draft.useResume));
const resumeName = ref(draft.resumeName || '');
const resumeType = ref(draft.resumeType || '');
const positionName = ref(draft.positionName || '');
const positionDetail = ref(draft.positionDetail || '');
const selectedResumeId = ref<number | undefined>(draft.resumeId);
const resumeOptions = ref<Array<{ id: number; name: string; content: string }>>([]);
const selectedJobId = ref<number | undefined>(undefined);
const jobKeyword = ref('');
const allJobs = ref<HotJobItem[]>([]);

const positionLockedByResume = computed(() => useResume.value);

async function fetchJobsByPosition(position: string) {
  const kw = String(position || '').trim();
  if (!kw) {
    allJobs.value = [];
    return;
  }
  try {
    const res = await searchJobsApi({ keyword: kw, page: 1, pageSize: 50 });
    allJobs.value = res.list || [];
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '岗位搜索失败');
  }
}

type SuggestItem = { value: string };
function queryPositionSuggestions(queryString: string, cb: (arg: SuggestItem[]) => void) {
  const q = queryString.trim();
  const base = ['后端工程师', '前端开发', 'Android开发', 'iOS开发', '测试开发', '算法工程师'];
  const fromJobs = allJobs.value.map((j) => j.name).filter(Boolean);
  const all = Array.from(new Set([...base, ...fromJobs]));
  const list = (q ? all.filter((n) => n.toLowerCase().includes(q.toLowerCase())) : all)
    .slice(0, 10)
    .map((value) => ({ value }));
  cb(list);
}

async function onPositionSelect(item: SuggestItem) {
  positionName.value = item.value;
  await fetchJobsByPosition(item.value);
}

watch(positionName, (v) => {
  if (positionLockedByResume.value) return;
  const txt = String(v || '').trim();
  if (!txt) return;
  void fetchJobsByPosition(txt);
});

watch(selectedResumeId, async (id) => {
  const item = resumeOptions.value.find((r) => r.id === id);
  if (!item) return;
  resumeName.value = item.name;
  const text = String(item.content || '').toLowerCase();
  if (text.includes('android')) resumeType.value = 'Android';
  else if (text.includes('前端') || text.includes('frontend')) resumeType.value = '前端';
  else if (text.includes('后端') || text.includes('backend')) resumeType.value = '后端';
  else resumeType.value = '';
  positionName.value = resumeType.value ? `${resumeType.value}工程师` : positionName.value;
  if (positionName.value) await fetchJobsByPosition(positionName.value);
});

watch(useResume, async (v) => {
  if (!v) {
    resumeName.value = '';
    resumeType.value = '';
    return;
  }
  if (selectedResumeId.value) {
    const item = resumeOptions.value.find((r) => r.id === selectedResumeId.value);
    if (item) {
      const text = String(item.content || '').toLowerCase();
      if (text.includes('android')) resumeType.value = 'Android';
      else if (text.includes('前端') || text.includes('frontend')) resumeType.value = '前端';
      else if (text.includes('后端') || text.includes('backend')) resumeType.value = '后端';
      else resumeType.value = '';
      positionName.value = resumeType.value ? `${resumeType.value}工程师` : positionName.value;
      if (positionName.value) await fetchJobsByPosition(positionName.value);
    }
  }
});

const filteredJobs = computed(() => {
  const p = String(positionName.value || '').trim().toLowerCase();
  const q = String(jobKeyword.value || '').trim().toLowerCase();
  let list = allJobs.value;
  if (!useResume.value && p) {
    list = list.filter((j) => String(j.name || '').toLowerCase().includes(p));
  }
  if (q) {
    list = list.filter((j) => `${j.companyName} ${j.name} ${j.jobContent}`.toLowerCase().includes(q));
  }
  return list.slice(0, 30);
});

function selectJob(job: HotJobItem) {
  selectedJobId.value = job.id;
  positionName.value = job.name || positionName.value;
  positionDetail.value = job.jobContent || positionDetail.value;
}

function shorten(text: string) {
  const t = String(text || '');
  return t.length > 60 ? `${t.slice(0, 60)}...` : t;
}

onMounted(async () => {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    if (raw) {
      const list = JSON.parse(raw) as Array<{ id: number; name: string; content: string }>;
      if (Array.isArray(list)) resumeOptions.value = list;
    }
  } catch {
    // ignore
  }
  if (!positionName.value) {
    try {
      allJobs.value = await getHotJobsApi({ limit: 50 });
    } catch {
      // ignore
    }
  } else {
    await fetchJobsByPosition(positionName.value);
  }
});

function goPrev() {
  router.push({ name: 'HomeInterviewType' });
}

function goNext() {
  if (!positionName.value.trim() || !positionDetail.value.trim()) {
    ElMessage.warning('请完善岗位名称与岗位详情');
    return;
  }
  saveInterviewSetupDraft({
    useResume: useResume.value,
    resumeId: selectedResumeId.value,
    resumeName: resumeName.value,
    resumeType: resumeType.value,
    positionName: positionName.value.trim(),
    positionDetail: positionDetail.value.trim(),
  });
  router.push({ name: 'HomeInterviewConfig' });
}
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.left-card,
.right-card {
  min-height: 420px;
}
.job-result-wrap { margin-top: 6px; }
.job-cards { display: grid; gap: 10px; max-height: 280px; overflow: auto; padding-right: 4px; }
.job-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all .2s ease;
  background: #fff;
}
.job-card:hover { border-color: #c4b5fd; background: #faf5ff; }
.job-card.active { border-color: #8b5cf6; background: #f5f3ff; }
.job-card h4 { margin: 0 0 4px; font-size: 14px; }
.job-card .meta { margin: 0 0 6px; color: #6b7280; font-size: 12px; }
.job-card .desc { margin: 0; color: #4b5563; font-size: 12px; line-height: 1.5; }
.detail-title { margin: 0 0 8px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 12px; }
@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
