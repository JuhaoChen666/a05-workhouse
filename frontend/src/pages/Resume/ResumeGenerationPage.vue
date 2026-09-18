<template>
  <section class="generation-page theme-page-shell">
    <div class="intro theme-card">
      <div>
        <span class="eyebrow">JD RESUME STUDIO</span>
        <h3>生成一份更贴近岗位的简历</h3>
        <p>经历只作为事实来源，AI 负责选择与组织，最终 LaTeX 和 PDF 由后端确定性生成。</p>
      </div>
      <el-button link @click="router.push({ name: 'HomeExperienceLibrary' })">管理经历库</el-button>
    </div>

    <el-steps :active="activeStep" finish-status="success" simple>
      <el-step title="岗位 / JD" />
      <el-step title="模板与经历" />
      <el-step title="生成与下载" />
    </el-steps>

    <div v-if="activeStep === 0" class="panel theme-card">
      <div class="panel-heading">
        <div><h4>选择目标岗位</h4><p>可以选择系统岗位，也可以粘贴一段 JD。</p></div>
      </div>
      <el-radio-group v-model="jdMode" class="mode-switch">
        <el-radio-button label="JOB_ID">系统岗位</el-radio-button>
        <el-radio-button label="TEXT">粘贴 JD</el-radio-button>
      </el-radio-group>
      <div v-if="jdMode === 'JOB_ID'" class="job-picker">
        <el-select v-model="selectedJobId" filterable remote :remote-method="searchJobs" :loading="jobLoading" placeholder="搜索岗位" @change="loadSelectedJob">
          <el-option v-for="job in jobs" :key="job.id" :label="job.name" :value="String(job.id)" />
        </el-select>
        <div v-if="selectedJobText" class="job-preview">{{ selectedJobText }}</div>
      </div>
      <el-input v-else v-model="jdText" type="textarea" :rows="12" maxlength="12000" show-word-limit placeholder="粘贴职位描述、职责和任职要求" />
      <div class="actions"><el-button type="primary" class="theme-primary-btn" :disabled="!hasJd" @click="activeStep = 1">下一步</el-button></div>
    </div>

    <div v-else-if="activeStep === 1" class="workspace">
      <div class="panel theme-card">
        <div class="panel-heading"><div><h4>选择模板</h4><p>模板版本由后端冻结，生成后可下载完整源码。</p></div></div>
        <div class="template-grid">
          <button v-for="template in templates" :key="`${template.id}-${template.version}`" class="template-card" :class="{ selected: selectedTemplate?.id === template.id && selectedTemplate?.version === template.version }" @click="selectedTemplate = template">
            <strong>{{ template.name }}</strong>
            <span>{{ template.id }} · v{{ template.version }}</span>
            <small>{{ template.supported_languages.join(' / ') }} · {{ template.supported_pages.join(' / ') }} 页</small>
          </button>
        </div>
      </div>
      <div class="panel theme-card">
        <div class="panel-heading"><div><h4>选择经历</h4><p>不选具体经历时，系统会根据 JD 自动推荐。</p></div></div>
        <div class="experience-toolbar">
          <el-input v-model="experienceKeyword" clearable placeholder="筛选经历" />
          <el-switch v-model="aiAutoSelect" active-text="AI 自动推荐" />
        </div>
        <el-checkbox-group v-model="selectedExperienceIds" class="experience-list">
          <label v-for="item in filteredExperiences" :key="item.id" class="experience-option">
            <el-checkbox :label="item.id" :disabled="aiAutoSelect" />
            <span><strong>{{ item.title }}</strong><small>{{ typeLabel(item.type) }} · {{ experienceSummary(item) }}</small></span>
          </label>
        </el-checkbox-group>
        <el-empty v-if="!filteredExperiences.length" description="暂无可用经历" :image-size="60" />
      </div>
      <div class="panel-options theme-card">
        <el-select v-model="targetPages" style="width: 130px"><el-option :value="1" label="最多 1 页" /><el-option :value="2" label="最多 2 页" /></el-select>
        <el-select v-model="language" style="width: 130px"><el-option value="zh" label="中文" /><el-option value="en" label="English" /></el-select>
        <el-checkbox v-model="showAvatar" :disabled="!selectedTemplate?.supports_avatar">保留头像</el-checkbox>
        <p>页数为 PDF 实际页数上限。语言控制标题，来源事实保留原文；AI 改写须逐条核对来源并明确确认后采用。</p>
        <el-form label-position="top" class="personal-info">
          <el-form-item v-for="field in personalFields" :key="field.key" :label="field.label"><el-input v-model="personal[field.key]" /></el-form-item>
          <div v-for="(entry, index) in personal.education" :key="index">
            <h4>教育经历 {{ Number(index) + 1 }}</h4>
            <el-form-item v-for="field in educationFields" :key="field.key" :label="field.label"><el-input v-model="entry[field.key]" /></el-form-item>
            <el-button @click="personal.education.splice(Number(index), 1)">移除教育经历</el-button>
          </div>
          <el-button @click="personal.education.push({ school: '', major: '', degree: '', date_range: '', gpa: '' })">添加教育经历</el-button>
        </el-form>
        <div class="actions"><el-button @click="activeStep = 0">上一步</el-button><el-button type="primary" class="theme-primary-btn" :loading="starting" @click="startGeneration">开始生成</el-button></div>
      </div>
    </div>

    <div v-else class="result-layout">
      <div class="panel theme-card">
        <div class="progress-head">
          <div><span class="eyebrow">GENERATION STATUS</span><h4>{{ statusLabel }}</h4></div>
          <strong>{{ job?.progress_percentage || 0 }}%</strong>
        </div>
        <el-progress :percentage="job?.progress_percentage || 0" :status="job?.status === 'FAILED' ? 'exception' : undefined" />
        <p class="stage">{{ stageLabel }}</p>
        <div v-if="job?.status === 'WAITING_REVIEW' && job.review_plan" class="review-panel">
          <el-alert title="请对照来源核实事实。仅采用勾选的建议，其余保留原文；用户确认不等于系统自动验证事实。" type="warning" :closable="false" />
          <div v-for="(bullet, index) in job.review_plan.tailored_bullets" :key="index">
            <p>来源经历：{{ bullet.source_item_id }}</p>
            <blockquote>原文：{{ bullet.original_bullet }}</blockquote>
            <p>建议：{{ bullet.tailored_bullet }}</p>
            <el-checkbox v-model="acceptedRewrites" :value="index">确认事实无新增，采用这条建议</el-checkbox>
          </div>
          <p>关键词匹配：{{ JSON.stringify(job.review_plan.keyword_matches) }}</p>
          <p v-for="(suggestion, index) in job.review_plan.trim_suggestions" :key="index">删减建议：{{ suggestion }}</p>
          <el-button type="primary" :loading="reviewing" @click="submitReview">确认选择并继续生成（未选建议保留原文）</el-button>
        </div>
        <div v-if="job?.status === 'FAILED'" class="error-box">
          <div>
            <strong>{{ job.compile_error_message || '生成失败' }}</strong>
            <small v-if="job.compile_error_location">{{ job.compile_error_location }}</small>
          </div>
          <el-button v-if="job.retryable" type="primary" link @click="retry">重试</el-button>
        </div>
        <div v-if="job?.result_metadata" class="recommendation">
          <el-alert v-if="job.result_metadata.ai_status === 'DEGRADED'" type="warning" :title="`AI 未成功，已按关键词降级选择：${job.result_metadata.ai_error_code}`" :closable="false" />
          <span>已选经历 {{ job.result_metadata.selected_item_ids?.length || 0 }} 条</span>
          <span v-if="job.result_metadata.actual_pages">实际 {{ job.result_metadata.actual_pages }} 页 / 上限 {{ job.result_metadata.maximum_pages }} 页</span>
          <span v-if="job.result_metadata.unverified_rewrites_preserved">{{ job.result_metadata.unverified_rewrites_preserved }} 条无法验证的改写已保留原文</span>
          <p v-if="job.result_metadata.keyword_matches">关键词匹配：{{ JSON.stringify(job.result_metadata.keyword_matches) }}</p>
          <p v-for="(suggestion, index) in job.result_metadata.trim_suggestions || []" :key="index">删减建议：{{ suggestion }}</p>
        </div>
        <div v-if="job?.status === 'COMPILED'" class="download-actions">
          <el-button type="primary" class="theme-primary-btn" :loading="previewLoading" @click="previewPdf">预览 PDF</el-button>
          <el-button @click="download('pdf')">下载 PDF</el-button>
          <el-button @click="download('latex')">下载 LaTeX</el-button>
        </div>
      </div>
      <div v-if="previewUrl" class="preview-frame theme-card"><iframe :src="previewUrl" title="PDF 预览" /></div>
      <ResumeDocumentLibrary :key="job?.document_id || job?.job_id" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import ResumeDocumentLibrary from '@/components/ResumeDocumentLibrary.vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRoute, useRouter } from 'vue-router';
import { getPositionDetailApi, getSimplePositionPageApi, type SimplePositionItem } from '@/api/jobs';
import { listExperiencesApi } from '@/api/experiences';
import {
  createResumeGenerationApi,
  confirmResumeReviewApi,
  getResumeGenerationApi,
  listGenerationTemplatesApi,
  listSavedResumeDocumentsApi,
  retryResumeGenerationApi,
  type SavedResumeDocument,
} from '@/api/resumeGeneration';
import type { ExperienceItemResponse, ExperienceType, ResumeGenerationJob, ResumeTemplateSummary } from '@/types/resumeLatexContracts';
import { useUserStore } from '@/store/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const personal = reactive<Record<string, any>>({ name: userStore.userInfo?.username || '', email: userStore.userInfo?.email || '', title: '', phone: '', city: '', github: '', education: [] });
const personalFields = [{ key: 'name', label: '姓名' }, { key: 'title', label: '求职方向' }, { key: 'phone', label: '电话' }, { key: 'email', label: '邮箱' }, { key: 'city', label: '城市' }, { key: 'github', label: 'GitHub / 作品链接' }];
const educationFields = [{ key: 'school', label: '学校' }, { key: 'major', label: '专业' }, { key: 'degree', label: '学历' }, { key: 'date_range', label: '就读起止年月' }, { key: 'gpa', label: 'GPA（选填）' }];
const activeStep = ref(0);
const jdMode = ref<'JOB_ID' | 'TEXT'>('JOB_ID');
const selectedJobId = ref<string>();
const selectedJobText = ref('');
const jdText = ref('');
const jobs = ref<SimplePositionItem[]>([]);
const jobLoading = ref(false);
const templates = ref<ResumeTemplateSummary[]>([]);
const selectedTemplate = ref<ResumeTemplateSummary>();
const experiences = ref<ExperienceItemResponse[]>([]);
const selectedExperienceIds = ref<string[]>([]);
const experienceKeyword = ref('');
const aiAutoSelect = ref(true);
const targetPages = ref<1 | 2>(1);
const language = ref<'zh' | 'en'>('zh');
const showAvatar = ref(false);
const starting = ref(false);
const job = ref<ResumeGenerationJob>();
const acceptedRewrites = ref<number[]>([]), reviewing = ref(false);
watch(() => job.value?.review_plan?.version, () => { acceptedRewrites.value = []; });
const documents = ref<SavedResumeDocument[]>([]);
const previewUrl = ref('');
const previewLoading = ref(false);
let timer: number | undefined;
let previewObjectUrl = '';

const hasJd = computed(() => jdMode.value === 'JOB_ID' ? Boolean(selectedJobId.value && selectedJobText.value) : jdText.value.trim().length >= 20);
const filteredExperiences = computed(() => {
  const query = experienceKeyword.value.trim().toLowerCase();
  if (!query) return experiences.value;
  return experiences.value.filter((item) => `${item.title} ${item.tags.join(' ')} ${JSON.stringify(item.attributes)}`.toLowerCase().includes(query));
});
const statusLabel = computed(() => ({ PENDING: '排队中', PROCESSING: '处理中', WAITING_REVIEW: '等待核实 AI 改写', COMPILED: '生成完成', FAILED: '生成失败' }[job.value?.status || 'PENDING'] || '处理中'));
const stageLabel = computed(() => ({ PENDING: '等待处理', CLAIMED: '已开始处理', CONTENT_SELECTION: '选择和核对内容', LATEX_RENDER: '生成排版源码', ISOLATED_COMPILE: '编译 PDF', PERSIST_OUTPUTS: '保存简历', COMPLETED: '已完成', FAILED: '生成失败', INTERRUPTED: '服务中断，请重试' } as Record<string, string>)[job.value?.stage || 'PENDING'] || '处理中');

function typeLabel(type: ExperienceType) {
  return ({ WORK: '工作', PROJECT: '项目', SKILL: '技能', CERTIFICATE: '证书', COMPETITION_AWARD: '获奖' } as Record<string, string>)[type] || type;
}
function experienceSummary(item: ExperienceItemResponse) {
  const attrs = item.attributes || {};
  return String(attrs.role || attrs.category || (Array.isArray(attrs.bullets) ? attrs.bullets[0] : '') || '暂无摘要');
}

async function searchJobs(query: string) {
  jobLoading.value = true;
  try {
    const result = await getSimplePositionPageApi({ page: 1, pageSize: 30, name: query.trim() || undefined });
    jobs.value = result.list || [];
  } catch (error) {
    ElMessage.error((error as Error).message || '岗位加载失败');
  } finally {
    jobLoading.value = false;
  }
}
async function loadSelectedJob() {
  if (!selectedJobId.value) return;
  try {
    const detail = await getPositionDetailApi(selectedJobId.value);
    selectedJobText.value = [detail.responsibility, detail.skill_requirements].filter(value => typeof value === 'string' && value.trim()).join('\n\n') || String(detail.jobContent || detail.content || detail.description || '');
  } catch (error) {
    ElMessage.error((error as Error).message || '岗位详情加载失败');
  }
}
async function loadCatalog() {
  try {
    const [templateResult, experienceResult] = await Promise.all([
      listGenerationTemplatesApi(),
      listExperiencesApi({ page: 1, page_size: 100, archive: 'active' }),
    ]);
    templates.value = (templateResult || []).filter(template => template.protocol_version === '1.1');
    selectedTemplate.value = templates.value[0];
    experiences.value = experienceResult.items || [];
    for (let next = 2; experiences.value.length < experienceResult.total; next++) {
      const result = await listExperiencesApi({ page: next, page_size: 100, archive: 'active' });
      if (!result.items.length) break;
      experiences.value.push(...result.items);
    }
  } catch (error) {
    ElMessage.error((error as Error).message || '生成素材加载失败');
  }
}
async function startGeneration() {
  if (!selectedTemplate.value || !hasJd.value) return;
  starting.value = true;
  try {
    job.value = await createResumeGenerationApi({
      jd_source_type: jdMode.value,
      jd_text: jdMode.value === 'TEXT' ? jdText.value.trim() : undefined,
      job_id: jdMode.value === 'JOB_ID' ? selectedJobId.value : undefined,
      template_id: selectedTemplate.value.id,
      template_version: selectedTemplate.value.version,
      target_pages: targetPages.value,
      language: language.value,
      show_avatar: showAvatar.value,
      selected_item_ids: aiAutoSelect.value ? null : selectedExperienceIds.value,
      ai_recommendation_mode: aiAutoSelect.value ? 'JD_AUTO_SELECT_AND_TAILOR' : 'MANUAL_ONLY',
      personal_info: personal,
    });
    activeStep.value = 2;
    await router.replace({ query: { job: job.value.job_id } });
    beginPolling();
  } catch (error) {
    ElMessage.error((error as Error).message || '生成任务创建失败');
  } finally {
    starting.value = false;
  }
}
let disposed = false;
function beginPolling() {
  stopPolling();
  async function poll() {
    const id = job.value?.job_id;
    if (!id || disposed) return;
    try {
      const latest = await getResumeGenerationApi(id);
      if (job.value?.job_id !== id || disposed) return;
      job.value = latest;
      if (latest.status === 'COMPILED' || latest.status === 'FAILED') return;
      timer = window.setTimeout(poll, 1800);
    } catch (error) { ElMessage.error((error as Error).message || '生成状态获取失败'); }
  }
  timer = window.setTimeout(poll, 1800);
}
function stopPolling() {
  if (timer) window.clearTimeout(timer);
  timer = undefined;
}
watch(() => route.query.job, async id => {
  if (typeof id !== 'string') return;
  stopPolling();
  try {
    const loaded = await getResumeGenerationApi(id);
    if (route.query.job !== id || disposed) return;
    job.value = loaded;
    activeStep.value = 2;
    if (!['COMPILED', 'FAILED'].includes(loaded.status)) beginPolling();
  } catch (error) { ElMessage.error((error as Error).message); }
}, { immediate: true });
async function retry() {
  if (!job.value) return;
  try {
    job.value = await retryResumeGenerationApi(job.value.job_id);
    beginPolling();
  } catch (error) {
    ElMessage.error((error as Error).message || '重试失败');
  }
}
async function submitReview() {
  if (!job.value?.review_plan) return;
  try {
    await ElMessageBox.confirm('已对照原文核实勾选建议，确认继续生成？未选建议保留原文。', '确认改写');
    reviewing.value = true;
    job.value = await confirmResumeReviewApi(job.value.job_id, job.value.review_plan.version, acceptedRewrites.value);
    beginPolling();
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
  finally { reviewing.value = false; }
}
async function fetchAsset(format: 'pdf' | 'latex') {
  if (!job.value) return null;
  const path = format === 'pdf' ? job.value.pdf_download_url : job.value.latex_source_url;
  if (!path || !job.value.document_id) throw new Error('文档不存在或已删除，请刷新简历库');
  const base = String(import.meta.env.VITE_INTERVIEW_API_ORIGIN || '').replace(/\/$/, '');
  const response = await fetch(`${base}${path}`, {
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : undefined,
  });
  if (!response.ok) throw new Error(`下载失败（${response.status}）`);
  return response.blob();
}
async function previewPdf() {
  previewLoading.value = true;
  try {
    const blob = await fetchAsset('pdf');
    if (!blob) return;
    if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = URL.createObjectURL(blob);
    previewUrl.value = previewObjectUrl;
  } catch (error) {
    ElMessage.error((error as Error).message || 'PDF 预览失败');
  } finally {
    previewLoading.value = false;
  }
}
async function download(format: 'pdf' | 'latex') {
  try {
    const blob = await fetchAsset(format);
    if (!blob || !job.value) return;
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `resume-${job.value.job_id.slice(0, 8)}.${format === 'pdf' ? 'pdf' : 'tex'}`;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error) {
    ElMessage.error((error as Error).message || '下载失败');
  }
}
async function loadDocuments() {
  try { documents.value = await listSavedResumeDocumentsApi(); } catch (error) { ElMessage.error((error as Error).message || '简历库加载失败'); }
}

onMounted(() => {
  void searchJobs('');
  void loadCatalog();
  void loadDocuments();
});
onBeforeUnmount(() => {
  disposed = true;
  stopPolling();
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
});
</script>

<style scoped>
.generation-page { display: grid; gap: 16px; }
.intro, .panel, .panel-options { padding: 18px; }
.intro { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.intro h3, .panel-heading h4, .progress-head h4 { margin: 4px 0 6px; color: #111827; }
.intro p, .panel-heading p { margin: 0; color: #6b7280; font-size: 13px; }
.eyebrow { color: #64748b; font-size: 11px; letter-spacing: 1px; font-weight: 700; }
.panel-heading { display: flex; justify-content: space-between; margin-bottom: 16px; }
.mode-switch { margin-bottom: 16px; }
.job-picker { display: grid; gap: 14px; }
.job-preview { max-height: 220px; overflow: auto; white-space: pre-wrap; line-height: 1.7; padding: 14px; color: #475569; background: #f8fafc; border-radius: 8px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.workspace { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
.template-grid { display: grid; gap: 10px; }
.template-card { display: grid; gap: 5px; text-align: left; padding: 14px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; cursor: pointer; }
.template-card.selected { border-color: #2563eb; background: #eff6ff; }
.template-card span, .template-card small { color: #64748b; }
.experience-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.experience-list { display: grid; gap: 8px; max-height: 360px; overflow: auto; }
.experience-option { display: flex; gap: 8px; padding: 10px; border-bottom: 1px solid #f1f5f9; }
.experience-option span { display: grid; gap: 4px; }
.experience-option small { color: #64748b; }
.panel-options { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.panel-options .actions { margin: 0 0 0 auto; }
.result-layout { display: grid; gap: 16px; }
.progress-head { display: flex; justify-content: space-between; align-items: center; }
.stage { color: #64748b; font-size: 13px; }
.error-box { display: flex; gap: 12px; align-items: center; padding: 12px; color: #b91c1c; background: #fef2f2; border-radius: 8px; }
.error-box > div { display: grid; gap: 4px; }
.error-box small { color: #991b1b; }
.recommendation, .download-actions { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; margin-top: 16px; }
.recommendation span { color: #475569; font-size: 13px; }
.preview-frame { height: min(76vh, 900px); padding: 0; overflow: hidden; }
.preview-frame iframe { width: 100%; height: 100%; border: 0; }
.saved-panel { margin-top: 0; }
@media (max-width: 900px) { .workspace { grid-template-columns: 1fr; } .panel-options { grid-column: auto; } .panel-options .actions { width: 100%; margin-left: 0; justify-content: flex-end; } }
</style>
