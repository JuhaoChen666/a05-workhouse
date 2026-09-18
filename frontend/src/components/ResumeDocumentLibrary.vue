<template>
  <div class="theme-card library" v-loading="loading">
    <div class="heading"><h3>简历库</h3><el-button @click="reload">刷新</el-button></div>
    <el-table :data="documents">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="format" label="格式" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" min-width="330"><template #default="{ row }">
        <el-button link @click="open(row)">快照 / 再次编辑</el-button>
        <el-button v-if="row.format === 'latex'" link @click="asset(row, 'pdf', true)">预览</el-button>
        <el-button v-if="row.format === 'latex'" link @click="asset(row, 'pdf')">PDF</el-button>
        <el-button v-if="row.format === 'latex'" link @click="asset(row, 'latex')">LaTeX</el-button>
        <el-button link @click="nameAction(row, false)">命名</el-button>
        <el-button link @click="nameAction(row, true)">复制</el-button>
        <el-button link type="danger" @click="remove(row)">删除</el-button>
      </template></el-table-column>
    </el-table>
    <el-empty v-if="!documents.length" description="尚无已生成简历" :image-size="60" />
    <el-collapse v-if="legacy.length"><el-collapse-item title="历史 Markdown（保留原记录）">
      <article v-for="row in legacy" :key="row.id">
        <h4>{{ row.created_at }} · Markdown</h4><pre>{{ row.content }}</pre>
        <el-button type="primary" @click="importHistory(row.id)">核实草稿并重新生成 LaTeX / PDF</el-button>
      </article>
    </el-collapse-item></el-collapse>
    <el-dialog v-model="visible" title="原始快照与再次编辑" width="800px">
      <template v-if="detail">
        <p>{{ detail.name }} · {{ detail.format }}</p>
        <pre v-if="detail.format === 'markdown'">{{ detail.markdown_content }}</pre>
        <template v-else>
          <p>模板 {{ detail.snapshot.template_snapshot.id }} · {{ detail.snapshot.template_snapshot.version }}；原任务 {{ detail.generation_job_id }}</p>
          <p>再次编辑会创建新任务和新文档，原快照及文件保持不变。</p>
          <el-form label-position="top">
            <el-form-item label="JD"><el-input v-model="edit.jd_text" type="textarea" :rows="5" /></el-form-item>
            <el-form-item v-for="field in personFields" :key="field.key" :label="field.label"><el-input v-model="edit.personal_info[field.key]" /></el-form-item>
            <div v-for="(entry, index) in edit.personal_info.education || []" :key="index">
              <h4>教育经历 {{ Number(index) + 1 }}</h4>
              <el-form-item v-for="field in educationFields" :key="field.key" :label="field.label"><el-input v-model="entry[field.key]" /></el-form-item>
              <el-button @click="edit.personal_info.education.splice(Number(index), 1)">移除</el-button>
            </div>
            <el-button @click="(edit.personal_info.education ||= []).push({ school: '', major: '', degree: '', date_range: '', gpa: '' })">添加教育经历</el-button>
            <el-form-item label="使用原快照中的经历"><el-checkbox-group v-model="edit.selected_item_ids">
              <div v-for="experience in detail.snapshot.experience_snapshot" :key="experience.id">
                <el-checkbox :value="experience.id">{{ experience.title }}</el-checkbox>
                <p>{{ experience.start_date }} — {{ experience.end_date }}；{{ experience.attributes.role || experience.attributes.category }}</p>
                <p v-for="bullet in experience.attributes.bullets || []" :key="bullet">{{ bullet }}</p>
              </div>
            </el-checkbox-group></el-form-item>
            <el-form-item label="最多页数"><el-select v-model="edit.target_pages"><el-option :value="1" label="1 页" /><el-option :value="2" label="2 页" /></el-select></el-form-item>
            <el-form-item label="标题语言"><el-select v-model="edit.language"><el-option value="zh" label="中文" /><el-option value="en" label="English" /></el-select></el-form-item>
            <el-form-item label="选择方式"><el-select v-model="edit.ai_recommendation_mode"><el-option value="MANUAL_ONLY" label="仅按手工选择" /><el-option value="JD_AUTO_SELECT_AND_TAILOR" label="AI 选择（未经验证的改写保留原文）" /></el-select></el-form-item>
          </el-form>
          <el-button type="primary" :loading="loading" @click="regenerate">创建新版本</el-button>
        </template>
      </template>
    </el-dialog>
    <el-dialog v-model="previewVisible" title="PDF 预览" width="900px"><iframe v-if="previewURL" :src="previewURL" title="简历 PDF" /></el-dialog>
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import { interviewRequest, INTERVIEW_API_ORIGIN } from '@/api/request';
import { useUserStore } from '@/store/user';
import { markdownImport } from '@/api/experienceImports';
import type { SavedResumeDocument } from '@/api/resumeGeneration';
import type { ResumeGenerationJob } from '@/types/resumeLatexContracts';
const router = useRouter();
const user = useUserStore();
const documents = ref<SavedResumeDocument[]>([]);
const legacy = ref<Array<{ id: string; content: string; created_at: string }>>([]);
const detail = ref<any>();
const loading = ref(false);
const visible = ref(false);
const previewVisible = ref(false);
const previewURL = ref('');
const previewDocumentId = ref('');
const edit = reactive<any>({ jd_text: '', personal_info: {}, selected_item_ids: [], target_pages: 1, language: 'zh', ai_recommendation_mode: 'MANUAL_ONLY' });
const personFields = [{ key: 'name', label: '姓名' }, { key: 'title', label: '求职方向' }, { key: 'phone', label: '电话' }, { key: 'email', label: '邮箱' }, { key: 'city', label: '城市' }, { key: 'github', label: 'GitHub / 作品链接' }];
const educationFields = [{ key: 'school', label: '学校' }, { key: 'major', label: '专业' }, { key: 'degree', label: '学历' }, { key: 'date_range', label: '就读年月' }, { key: 'gpa', label: 'GPA' }];
async function reload() {
  loading.value = true;
  try { [documents.value, legacy.value] = await Promise.all([interviewRequest.get<SavedResumeDocument[]>('/resume-documents'), interviewRequest.get<typeof legacy.value>('/resume-documents/legacy-markdown')]); }
  catch (error) { ElMessage.error((error as Error).message); }
  finally { loading.value = false; }
}
async function open(row: SavedResumeDocument) {
  try {
    detail.value = await interviewRequest.get(`/resume-documents/${row.id}`);
    if (row.format === 'latex') {
      const snapshot = detail.value.snapshot;
      Object.assign(edit, { jd_text: snapshot.jd_snapshot.text, personal_info: JSON.parse(JSON.stringify(snapshot.personal_info_snapshot)),
        selected_item_ids: snapshot.options_snapshot.selected_item_ids || snapshot.experience_snapshot.map((item: any) => item.id),
        target_pages: snapshot.options_snapshot.target_pages, language: snapshot.options_snapshot.language,
        ai_recommendation_mode: snapshot.options_snapshot.ai_recommendation_mode });
    }
    visible.value = true;
  } catch (error) { ElMessage.error((error as Error).message); }
}
async function regenerate() {
  loading.value = true;
  try {
    const result = await interviewRequest.post<ResumeGenerationJob>(`/resume-documents/${detail.value.id}/regenerate`, edit);
    visible.value = false;
    await router.push({ name: 'HomeResumeGeneration', query: { job: result.job_id } });
  } catch (error) { ElMessage.error((error as Error).message); }
  finally { loading.value = false; }
}
async function nameAction(row: SavedResumeDocument, copy: boolean) {
  try {
    const answer = await ElMessageBox.prompt('请输入简历名称', copy ? '复制简历' : '命名简历', { inputValue: copy ? `${row.name} 副本` : row.name, inputValidator: value => !!value?.trim() || '名称不能为空' });
    if (typeof answer !== 'object' || !('value' in answer)) return;
    const value = answer.value;
    if (copy) await interviewRequest.post(`/resume-documents/${row.id}/copy`, { name: value });
    else await interviewRequest.patch(`/resume-documents/${row.id}`, { name: value });
    await reload();
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
}
async function remove(row: SavedResumeDocument) {
  try {
    await ElMessageBox.confirm(`删除“${row.name}”？文件按保留期清理，共享副本仍可访问。`, '删除简历');
    await interviewRequest.delete(`/resume-documents/${row.id}`);
    if (detail.value?.id === row.id) { visible.value = false; detail.value = undefined; }
    if (previewDocumentId.value === row.id) {
      previewVisible.value = false;
      if (previewURL.value) URL.revokeObjectURL(previewURL.value);
      previewURL.value = ''; previewDocumentId.value = '';
    }
    await reload();
  }
  catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
}
async function asset(row: SavedResumeDocument, format: 'pdf' | 'latex', preview = false) {
  try {
    const response = await fetch(`${INTERVIEW_API_ORIGIN}/api/resume-documents/${row.id}/${format}`, { headers: { Authorization: `Bearer ${user.token}` } });
    if (!response.ok) throw new Error(`文件不可用（${response.status}）`);
    const url = URL.createObjectURL(await response.blob());
    if (preview) { if (previewURL.value) URL.revokeObjectURL(previewURL.value); previewURL.value = url; previewDocumentId.value = row.id; previewVisible.value = true; }
    else { const link = document.createElement('a'); link.href = url; link.download = `${row.name}.${format === 'pdf' ? 'pdf' : 'tex'}`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }
  } catch (error) { ElMessage.error((error as Error).message); }
}
async function importHistory(id: string) {
  loading.value = true;
  try { const batch = await markdownImport(id); await router.push({ name: 'HomeExperienceLibrary', query: { import: batch.id } }); }
  catch (error) {
    const failure = error as Error & { details?: { import_id?: string } };
    ElMessage.error(failure.message);
    if (failure.details?.import_id) await router.push({ name: 'HomeExperienceLibrary', query: { import: failure.details.import_id } });
  } finally { loading.value = false; }
}
onMounted(() => void reload());
onBeforeUnmount(() => { if (previewURL.value) URL.revokeObjectURL(previewURL.value); });
</script>
<style scoped>
.library { padding: 18px; } .heading { display: flex; justify-content: space-between; align-items: center; } pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 400px; overflow: auto; } iframe { width: 100%; height: 75vh; border: none; } article { padding-bottom: 20px; }
</style>
