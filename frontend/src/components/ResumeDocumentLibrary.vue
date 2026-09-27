<template>
  <section class="resume-library theme-page-shell" v-loading="loading">
    <header class="library-heading">
      <div class="library-heading-copy">
        <div class="library-title-row"><h3>简历库</h3><span>Resume Library</span></div>
        <span class="library-heading-accent" aria-hidden="true"></span>
      </div>
      <div class="library-heading-actions">
        <span>共 {{ total }} 份简历</span>
        <el-button type="primary" class="theme-primary-btn" @click="router.push({ name: 'HomeResumeGeneration' })">生成简历</el-button>
      </div>
    </header>

    <ul class="resume-grid" aria-label="简历列表">
      <li v-for="item in documents" :key="item.key" class="resume-card" :class="`is-${item.kind}`">
        <div
          class="resume-card-main"
          role="button"
          tabindex="0"
          :aria-label="`预览简历：${item.name}`"
          @click="openCard(item)"
          @keydown.enter.prevent="openCard(item)"
          @keydown.space.prevent="openCard(item)"
        >
          <div class="resume-card-heading">
            <div class="file-badge" :class="item.kind" aria-hidden="true"><el-icon><Document /></el-icon></div>
            <div class="resume-card-meta">
              <h4 class="resume-card-name" :title="item.name">{{ item.name }}</h4>
              <p class="resume-card-updated">更新于 {{ formatDate(item.updated_at) }}</p>
            </div>
            <span class="source-pill" :class="item.kind">{{ item.kind === 'generated' ? '生成' : '上传' }}</span>
          </div>
          <ResumeThumbnailImage :url="item.thumbnail_url" />
        </div>

        <footer v-if="item.kind === 'generated'" class="resume-card-actions" aria-label="生成简历操作">
          <el-button v-if="item.format === 'latex'" text size="small" class="action-primary" @click.stop="openGenerated(item)">编辑</el-button>
          <el-dropdown trigger="click" placement="bottom-end" @command="handleGeneratedMore($event, item)">
            <el-button text size="small" class="action-button action-more" aria-label="生成简历更多操作" @click.stop><el-icon><MoreFilled /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="item.format === 'latex'" command="download-pdf">PDF 下载</el-dropdown-item>
                <el-dropdown-item v-if="item.format === 'latex'" command="download-latex">LaTeX 下载</el-dropdown-item>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item command="copy">复制</el-dropdown-item>
                <el-dropdown-item command="delete" divided class="menu-danger">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </footer>
        <footer v-else class="resume-card-actions" aria-label="上传简历操作">
          <el-dropdown trigger="click" placement="bottom-end" @command="remove(item)">
            <el-button text size="small" class="action-button action-more" aria-label="上传简历更多操作" @click.stop><el-icon><MoreFilled /></el-icon></el-button>
            <template #dropdown><el-dropdown-menu><el-dropdown-item command="delete" class="menu-danger">删除</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
        </footer>
      </li>

      <li class="resume-card upload-card">
        <el-upload class="resume-upload-control" :show-file-list="false" :auto-upload="false" accept=".pdf,application/pdf" :on-change="handleUploadFileChange">
          <button type="button" class="upload-card-button">
            <el-icon><Plus /></el-icon><strong>上传简历</strong><span>仅支持 PDF</span>
          </button>
        </el-upload>
      </li>
    </ul>
    <p v-if="!documents.length" class="library-empty-hint">还没有简历，上传 PDF 或生成一份简历开始整理。</p>

    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination v-model:current-page="currentPage" :page-size="pageSize" layout="total, prev, pager, next" :total="total" @current-change="onCurrentPageChange" />
    </div>

    <el-collapse v-if="legacy.length" class="legacy-list">
      <el-collapse-item title="历史 Markdown（保留原记录）">
        <article v-for="row in legacy" :key="row.id" class="legacy-row">
          <h4>{{ row.created_at }} · Markdown</h4><pre>{{ row.content }}</pre>
          <el-button type="primary" @click="importHistory(row.id)">核实草稿并重新生成 LaTeX / PDF</el-button>
        </article>
      </el-collapse-item>
    </el-collapse>

    <el-dialog v-model="previewVisible" title="简历在线预览" width="900px" append-to-body @closed="clearPreviewObjectUrl" @update:model-value="onPreviewVisibility">
      <h4 class="dialog-title">{{ currentPreviewName || '--' }}</h4>
      <div v-if="previewLoading" class="dialog-content">预览加载中...</div>
      <div v-else-if="previewError" class="dialog-content">{{ previewError }}</div>
      <ResumePdfPreview v-else-if="previewURL" :src="previewURL" variant="dialog" />
      <div v-else class="dialog-content">暂无可预览内容</div>
    </el-dialog>

    <el-dialog v-model="generatedDetailVisible" title="原始快照与再次编辑" width="800px" append-to-body>
      <template v-if="detail">
        <div class="snapshot-heading"><div><span class="snapshot-kicker">GENERATED RESUME</span><h4>{{ detail.name }}</h4></div><span class="source-pill generated">{{ detail.format }}</span></div>
        <pre v-if="detail.format === 'markdown'" class="snapshot-markdown">{{ detail.markdown_content }}</pre>
        <template v-else>
          <p class="snapshot-note">模板 {{ detail.snapshot.template_snapshot.id }} · {{ detail.snapshot.template_snapshot.version }}；原任务 {{ detail.generation_job_id }}</p>
          <p class="snapshot-note">再次编辑会创建新任务和新文档，原快照及文件保持不变。</p>
          <el-form label-position="top" class="snapshot-form">
            <el-form-item label="JD"><el-input v-model="edit.jd_text" type="textarea" :rows="5" /></el-form-item>
            <el-form-item v-for="field in personFields" :key="field.key" :label="field.label"><el-input v-model="edit.personal_info[field.key]" /></el-form-item>
            <div v-for="(entry, index) in edit.personal_info.education || []" :key="index" class="education-entry">
              <div class="education-heading"><h4>教育经历 {{ Number(index) + 1 }}</h4><el-button link type="danger" @click="edit.personal_info.education.splice(Number(index), 1)">移除</el-button></div>
              <el-form-item v-for="field in educationFields" :key="field.key" :label="field.label"><el-input v-model="entry[field.key]" /></el-form-item>
            </div>
            <el-button @click="(edit.personal_info.education ||= []).push({ school: '', major: '', degree: '', date_range: '', gpa: '' })">添加教育经历</el-button>
            <el-form-item label="使用原快照中的经历" class="experience-picker"><el-checkbox-group v-model="edit.selected_item_ids">
              <div v-for="experience in detail.snapshot.experience_snapshot" :key="experience.id" class="experience-option">
                <el-checkbox :value="experience.id">{{ experience.title }}</el-checkbox>
                <p>{{ experience.start_date }} — {{ experience.end_date }}；{{ experience.attributes.role || experience.attributes.category }}</p>
              </div>
            </el-checkbox-group></el-form-item>
            <div class="snapshot-options">
              <el-form-item label="最多页数"><el-select v-model="edit.target_pages"><el-option :value="1" label="1 页" /><el-option :value="2" label="2 页" /></el-select></el-form-item>
              <el-form-item label="标题语言"><el-select v-model="edit.language"><el-option value="zh" label="中文" /><el-option value="en" label="English" /></el-select></el-form-item>
              <el-form-item label="选择方式"><el-select v-model="edit.ai_recommendation_mode"><el-option value="MANUAL_ONLY" label="仅按手工选择" /><el-option value="JD_AUTO_SELECT_AND_TAILOR" label="AI 选择" /></el-select></el-form-item>
            </div>
          </el-form>
          <div class="snapshot-footer"><el-button @click="generatedDetailVisible = false">取消</el-button><el-button type="primary" :loading="loading" @click="regenerate">创建新版本</el-button></div>
        </template>
      </template>
    </el-dialog>

    <el-dialog v-model="uploadPreviewVisible" title="上传前预览" width="900px" append-to-body @closed="cancelPendingUpload">
      <h4 class="dialog-title">{{ pendingUploadName || '--' }}</h4>
      <ResumePdfPreview v-if="uploadPreviewURL" :src="uploadPreviewURL" variant="dialog" />
      <template #footer><el-button @click="cancelPendingUpload">取消</el-button><el-button type="primary" :loading="uploading" @click="confirmUploadResume">确认上传</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import { Document, MoreFilled, Plus } from '@element-plus/icons-vue';
import { interviewRequest } from '@/api/request';
import { buildInterviewAssetUrl } from '@/api/resumeAssets';
import { buildResumeFilePublicUrl } from '@/config/resumeAssets';
import { getResumeLibraryApi } from '@/api/resumeLibrary';
import { deleteResumeApi, getResumeItemApi, uploadResumeApi } from '@/api/resume';
import { useUserStore } from '@/store/user';
import { markdownImport } from '@/api/experienceImports';
import type { ResumeLibraryItem } from '@/api/resumeLibrary';
import type { ResumeGenerationJob } from '@/types/resumeLatexContracts';
import ResumePdfPreview from '@/components/ResumePdfPreview.vue';
import ResumeThumbnailImage from '@/components/ResumeThumbnailImage.vue';

type LegacyMarkdown = { id: string; content: string; created_at: string };
type GeneratedMoreCommand = 'download-pdf' | 'download-latex' | 'rename' | 'copy' | 'delete';
const router = useRouter();
const user = useUserStore();
const documents = ref<ResumeLibraryItem[]>([]);
const legacy = ref<LegacyMarkdown[]>([]);
const detail = ref<any>();
const loading = ref(false);
const generatedDetailVisible = ref(false);
const previewVisible = ref(false);
const currentPreviewName = ref('');
const previewLoading = ref(false);
const previewError = ref('');
const previewURL = ref('');
const previewDocumentId = ref('');
let previewObjectUrl = '';
let previewRequestId = 0;
let previewController: AbortController | undefined;
const uploadPreviewVisible = ref(false);
const uploading = ref(false);
const pendingUploadFile = ref<File | null>(null);
const pendingUploadName = ref('');
const uploadPreviewURL = ref('');
let uploadPreviewObjectUrl = '';
const currentPage = ref(1);
const pageSize = 12;
const total = ref(0);
let listRequestId = 0;
let listController: AbortController | undefined;
const edit = reactive<any>({ jd_text: '', personal_info: {}, selected_item_ids: [], target_pages: 1, language: 'zh', ai_recommendation_mode: 'MANUAL_ONLY' });
const personFields = [{ key: 'name', label: '姓名' }, { key: 'title', label: '求职方向' }, { key: 'phone', label: '电话' }, { key: 'email', label: '邮箱' }, { key: 'city', label: '城市' }, { key: 'github', label: 'GitHub / 作品链接' }];
const educationFields = [{ key: 'school', label: '学校' }, { key: 'major', label: '专业' }, { key: 'degree', label: '学历' }, { key: 'date_range', label: '就读年月' }, { key: 'gpa', label: 'GPA' }];

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || '--';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function reload() {
  listController?.abort();
  const controller = new AbortController();
  listController = controller;
  const requestId = ++listRequestId;
  loading.value = true;
  try {
    const page = await getResumeLibraryApi(currentPage.value, pageSize, controller.signal);
    if (controller.signal.aborted || requestId !== listRequestId) return;
    documents.value = page.items;
    total.value = page.total;
    try {
      const history = await interviewRequest.get<LegacyMarkdown[]>('/resume-documents/legacy-markdown', { signal: controller.signal });
      if (controller.signal.aborted || requestId !== listRequestId) return;
      legacy.value = history;
    } catch (error) {
      if (!controller.signal.aborted && requestId === listRequestId) { legacy.value = []; ElMessage.warning((error as Error).message || '历史 Markdown 暂时无法读取'); }
    }
  } catch (error) { if (!controller.signal.aborted && requestId === listRequestId) ElMessage.error((error as Error).message || '读取简历列表失败'); }
  finally {
    if (requestId === listRequestId) { loading.value = false; listController = undefined; }
  }
}

function clearPreviewObjectUrl() {
  previewRequestId++;
  previewController?.abort();
  previewController = undefined;
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
  previewObjectUrl = '';
  previewURL.value = '';
  previewDocumentId.value = '';
}

function clearUploadPreviewObjectUrl() {
  if (uploadPreviewObjectUrl) URL.revokeObjectURL(uploadPreviewObjectUrl);
  uploadPreviewObjectUrl = '';
  uploadPreviewURL.value = '';
}

async function viewUploadedResume(item: ResumeLibraryItem) {
  clearPreviewObjectUrl();
  const requestId = previewRequestId;
  const controller = new AbortController();
  previewController = controller;
  currentPreviewName.value = item.name;
  previewDocumentId.value = item.key || String(item.id);
  previewVisible.value = true;
  previewLoading.value = true;
  previewError.value = '';
  try {
    const row = await getResumeItemApi(Number(item.id), controller.signal);
    if (controller.signal.aborted || requestId !== previewRequestId) return;
    const fileKey = String(row?.unique_filename || row?.filename || '').trim();
    previewURL.value = buildResumeFilePublicUrl(fileKey);
    if (!previewURL.value) previewError.value = '简历文件路径无效，无法预览';
  } catch (error) { if (!controller.signal.aborted && requestId === previewRequestId) previewError.value = (error as Error).message || '获取简历详情失败'; }
  finally { if (requestId === previewRequestId) { previewLoading.value = false; previewController = undefined; } }
}

async function getGeneratedAsset(item: ResumeLibraryItem, format: 'pdf' | 'latex', signal?: AbortSignal) {
  const response = await fetch(buildInterviewAssetUrl(`/api/resume-documents/${item.id}/${format}`), {
    headers: { Authorization: `Bearer ${user.token}` },
    signal,
  });
  if (!response.ok) throw new Error(`文件不可用（${response.status}）`);
  return response.blob();
}

async function previewGenerated(item: ResumeLibraryItem) {
  if (item.format === 'markdown') { await openGenerated(item); return; }
  clearPreviewObjectUrl();
  const requestId = previewRequestId;
  const controller = new AbortController();
  previewController = controller;
  currentPreviewName.value = item.name;
  previewVisible.value = true;
  previewLoading.value = true;
  previewError.value = '';
  previewDocumentId.value = item.key || String(item.id);
  try {
    const blob = await getGeneratedAsset(item, 'pdf', controller.signal);
    if (controller.signal.aborted || requestId !== previewRequestId) return;
    previewObjectUrl = URL.createObjectURL(blob);
    previewURL.value = previewObjectUrl;
  } catch (error) { if (!controller.signal.aborted && requestId === previewRequestId) previewError.value = (error as Error).message || '预览文件失败'; }
  finally { if (requestId === previewRequestId) { previewLoading.value = false; previewController = undefined; } }
}

function onPreviewVisibility(value: boolean) {
  previewVisible.value = value;
  if (!value) { clearPreviewObjectUrl(); previewLoading.value = false; }
}

function openCard(item: ResumeLibraryItem) {
  if (item.kind === 'uploaded') void viewUploadedResume(item);
  else void previewGenerated(item);
}

async function openGenerated(item: ResumeLibraryItem) {
  try {
    detail.value = await interviewRequest.get(`/resume-documents/${item.id}`);
    if (item.format === 'latex') {
      const snapshot = detail.value.snapshot;
      Object.assign(edit, {
        jd_text: snapshot.jd_snapshot.text,
        personal_info: JSON.parse(JSON.stringify(snapshot.personal_info_snapshot)),
        selected_item_ids: snapshot.options_snapshot.selected_item_ids || snapshot.experience_snapshot.map((row: any) => row.id),
        target_pages: snapshot.options_snapshot.target_pages,
        language: snapshot.options_snapshot.language,
        ai_recommendation_mode: snapshot.options_snapshot.ai_recommendation_mode,
      });
    }
    generatedDetailVisible.value = true;
  } catch (error) { ElMessage.error((error as Error).message || '读取简历快照失败'); }
}

async function regenerate() {
  if (!detail.value) return;
  loading.value = true;
  try {
    const payload = { ...edit, personal_info: { ...edit.personal_info, education: (edit.personal_info.education || []).filter((entry: Record<string, unknown>) => Object.values(entry).some(value => String(value || '').trim())).map((entry: Record<string, unknown>) => ({ ...entry })) } };
    const result = await interviewRequest.post<ResumeGenerationJob>(`/resume-documents/${detail.value.id}/regenerate`, payload);
    generatedDetailVisible.value = false;
    await router.push({ name: 'HomeResumeGeneration', query: { job: result.job_id } });
  } catch (error) { ElMessage.error((error as Error).message || '创建新版本失败'); }
  finally { loading.value = false; }
}

async function downloadGenerated(item: ResumeLibraryItem, format: 'pdf' | 'latex') {
  try {
    const url = URL.createObjectURL(await getGeneratedAsset(item, format));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${item.name}.${format === 'pdf' ? 'pdf' : 'tex'}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { ElMessage.error((error as Error).message || '下载文件失败'); }
}

async function nameGenerated(item: ResumeLibraryItem, copy: boolean) {
  try {
    const answer = await ElMessageBox.prompt('请输入简历名称', copy ? '复制简历' : '命名简历', { inputValue: copy ? `${item.name} 副本` : item.name, inputValidator: value => !!value?.trim() || '名称不能为空' });
    if (typeof answer !== 'object' || !('value' in answer)) return;
    if (copy) await interviewRequest.post(`/resume-documents/${item.id}/copy`, { name: answer.value });
    else await interviewRequest.patch(`/resume-documents/${item.id}`, { name: answer.value });
    await reload();
    ElMessage.success(copy ? '简历已复制' : '名称已更新');
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
}

async function handleGeneratedMore(command: GeneratedMoreCommand, item: ResumeLibraryItem) {
  if (command === 'delete') { await remove(item); return; }
  if (command === 'download-pdf') { await downloadGenerated(item, 'pdf'); return; }
  if (command === 'download-latex') { await downloadGenerated(item, 'latex'); return; }
  await nameGenerated(item, command === 'copy');
}

async function remove(item: ResumeLibraryItem) {
  try {
    await ElMessageBox.confirm(`确认删除简历「${item.name}」吗？此操作不可撤销。`, '删除简历', { type: 'warning' });
    if (item.kind === 'uploaded') {
      const userId = user.userInfo?.id;
      if (!userId) throw new Error('未获取到用户信息，请重新登录后重试');
      await deleteResumeApi({ id: Number(item.id), user_id: userId, filename: item.name });
    } else {
      await interviewRequest.delete(`/resume-documents/${item.id}`);
    }
    if (detail.value?.id === item.id) { generatedDetailVisible.value = false; detail.value = undefined; }
    if (previewDocumentId.value === item.key || previewDocumentId.value === String(item.id)) { previewVisible.value = false; clearPreviewObjectUrl(); }
    if (documents.value.length === 1 && currentPage.value > 1) currentPage.value--;
    await reload();
    ElMessage.success('简历已删除');
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message || '删除简历失败'); }
}

function handleUploadFileChange(file: { name?: string; raw?: File }) {
  const raw = file.raw;
  const isPdf = String(file.name || '').trim().toLowerCase().endsWith('.pdf') || raw?.type === 'application/pdf';
  if (!isPdf || !raw) { ElMessage.error('仅支持上传有效的 PDF 文件'); return; }
  clearUploadPreviewObjectUrl();
  uploadPreviewObjectUrl = URL.createObjectURL(raw);
  uploadPreviewURL.value = uploadPreviewObjectUrl;
  pendingUploadFile.value = raw;
  pendingUploadName.value = String(file.name || raw.name || '未命名简历');
  uploadPreviewVisible.value = true;
}

function cancelPendingUpload() {
  uploadPreviewVisible.value = false;
  pendingUploadFile.value = null;
  pendingUploadName.value = '';
  uploadPreviewURL.value = '';
  clearUploadPreviewObjectUrl();
}

async function confirmUploadResume() {
  const userId = user.userInfo?.id;
  const file = pendingUploadFile.value;
  if (!userId || !file) { ElMessage.error('上传信息无效，请重新选择 PDF'); return; }
  uploading.value = true;
  try {
    await uploadResumeApi(userId, file);
    currentPage.value = 1;
    uploadPreviewVisible.value = false;
    cancelPendingUpload();
    await reload();
    ElMessage.success('简历上传成功');
  } catch (error) { ElMessage.error((error as Error).message || '简历上传失败'); }
  finally { uploading.value = false; }
}

function onCurrentPageChange(page: number) { currentPage.value = page; void reload(); }

async function importHistory(id: string) {
  loading.value = true;
  try { const batch = await markdownImport(id); await router.push({ name: 'HomeExperienceLibrary', query: { import: batch.id } }); }
  catch (error) {
    const failure = error as Error & { details?: { import_id?: string } };
    ElMessage.error(failure.message);
    if (failure.details?.import_id) await router.push({ name: 'HomeExperienceLibrary', query: { import: failure.details.import_id } });
  } finally { loading.value = false; }
}

onMounted(() => { void reload(); });
onBeforeUnmount(() => { listController?.abort(); clearPreviewObjectUrl(); clearUploadPreviewObjectUrl(); });
</script>

<style scoped>
.resume-library { display: grid; gap: 20px; }
.library-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.library-heading-copy { min-width: 0; }
.library-title-row { display: flex; align-items: baseline; flex-wrap: wrap; column-gap: 14px; row-gap: 2px; }
.library-heading-copy h3 { margin: 0; color: #111827; font-size: clamp(24px, 2vw, 30px); font-weight: 780; letter-spacing: -0.035em; }
.library-title-row > span { color: #9aa0ad; font-size: 15px; font-weight: 500; letter-spacing: .025em; }
.library-heading-accent { width: 48px; height: 4px; display: block; margin-top: 10px; border-radius: 999px; background: linear-gradient(90deg, #7455e8, #a28af8); }
.library-heading-actions { display: flex; align-items: center; gap: 14px; color: #64748b; font-size: 14px; font-weight: 600; }
.resume-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: stretch; gap: 18px; margin: 0; padding: 0; list-style: none; }
.resume-card { min-width: 0; min-height: 328px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #e7e5ee; border-radius: 16px; background: #fff; box-shadow: 0 2px 8px rgba(31, 41, 55, .035); transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease; }
.resume-card:hover { border-color: #c4b5fd; box-shadow: 0 12px 28px rgba(76, 29, 149, .09); transform: translateY(-2px); }
.resume-card-main { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 10px; padding: 12px 14px 10px; cursor: pointer; }
.resume-card-main:focus-visible { outline: 3px solid rgba(124, 58, 237, .38); outline-offset: -4px; border-radius: 15px; }
.resume-card-heading { min-width: 0; display: flex; align-items: center; gap: 11px; }
.file-badge { width: 38px; height: 38px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 11px; background: #f1f5f9; color: #64748b; }
.file-badge.generated { background: #f5f3ff; color: #6d28d9; }
.file-badge .el-icon { font-size: 21px; }
.resume-card-meta { min-width: 0; flex: 1; }
.resume-card-name { width: 100%; margin: 0; overflow: hidden; color: #1f2937; font-size: 14px; font-weight: 700; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.resume-card-updated { margin: 4px 0 0; color: #94a3b8; font-size: 11px; line-height: 1.35; }
.source-pill { flex: 0 0 auto; padding: 4px 8px; border-radius: 999px; background: #f1f5f9; color: #64748b; font-size: 11px; font-weight: 650; line-height: 1.2; }
.source-pill.generated { background: #f5f3ff; color: #6d28d9; }
.resume-card-actions { min-height: 50px; display: flex; align-items: center; justify-content: flex-end; gap: 7px; padding: 8px 12px; border-top: 1px solid #eeedf2; }
:deep(.resume-card-actions .el-button) { min-height: 32px; border: 0; border-radius: 8px; box-shadow: none; font-weight: 600; }
:deep(.action-primary) { background: #f5f3ff; color: #6d28d9; }
:deep(.action-primary:hover), :deep(.action-primary:focus-visible) { background: #ede9fe; color: #5b21b6; }
:deep(.action-button) { background: transparent; color: #475569; }
:deep(.action-button:hover), :deep(.action-button:focus-visible) { background: #f5f3ff; color: #6d28d9; }
:deep(.action-more) { min-width: 34px; padding-inline: 9px; }
:deep(.action-more .el-icon) { font-size: 17px; }
:global(.el-dropdown-menu__item.menu-danger) { color: #dc2626; }
.upload-card { border: 1.5px dashed #c4b5fd; background: #fbfaff; }
.upload-card:hover { border-color: #8b5cf6; background: #f8f5ff; }
:deep(.resume-upload-control), :deep(.resume-upload-control .el-upload) { width: 100%; height: 100%; display: block; }
.upload-card-button { width: 100%; min-height: 328px; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 11px; border: 0; background: transparent; color: #6d28d9; cursor: pointer; font: inherit; }
.upload-card-button:focus-visible { outline: 3px solid #8b5cf6; outline-offset: -5px; border-radius: 14px; }
.upload-card-button .el-icon { font-size: 28px; }
.upload-card-button strong { font-size: 15px; }
.upload-card-button span { color: #8b8795; font-size: 12px; }
.library-empty-hint { margin: -6px 0 0; color: #64748b; font-size: 13px; }
.pagination-wrap { display: flex; justify-content: flex-end; padding: 2px 0; }
:deep(.pagination-wrap .el-pagination) { justify-content: flex-end; }
.legacy-list { margin-top: -4px; }
.legacy-row { padding: 12px 0 18px; border-bottom: 1px solid #ececf2; }
.legacy-row pre, .snapshot-markdown { max-height: 420px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
.dialog-title { margin: 0 0 10px; color: #111827; font-size: 16px; font-weight: 700; }
.dialog-content { max-height: 420px; overflow-y: auto; white-space: pre-wrap; line-height: 1.75; color: #374151; }
.snapshot-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 16px; border-bottom: 1px solid #e5e7eb; }
.snapshot-heading h4 { margin: 4px 0 0; color: #111827; font-size: 19px; }
.snapshot-kicker { color: #7c3aed; font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.snapshot-note { margin: 14px 0 0; color: #64748b; font-size: 13px; line-height: 1.65; }
.snapshot-form { margin-top: 18px; }
.education-entry { margin: 14px 0; padding: 14px; border: 1px solid #e5e7eb; border-radius: 12px; background: #f8fafc; }
.education-heading { display: flex; align-items: center; justify-content: space-between; }
.education-heading h4 { margin: 0; }
.experience-picker { margin-top: 18px; }
.experience-option { margin-bottom: 8px; padding: 10px; border-radius: 10px; background: #f8fafc; }
.experience-option p { margin: 4px 0 0 24px; color: #64748b; font-size: 12px; }
.snapshot-options { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.snapshot-options :deep(.el-select) { width: 100%; }
.snapshot-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
@media (prefers-reduced-motion: reduce) { .resume-card { transition: none; } }
@media (max-width: 1020px) { .resume-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 680px) {
  .resume-grid { grid-template-columns: 1fr; gap: 14px; }
  .library-heading { align-items: flex-start; }
  .library-heading-actions { align-items: flex-end; flex-direction: column; gap: 8px; }
  .resume-card, .upload-card-button { min-height: 328px; }
  .snapshot-options { grid-template-columns: 1fr; }
  :deep(.pagination-wrap .el-pagination) { justify-content: center; }
}
</style>
