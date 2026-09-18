<template>
  <div class="theme-card import-panel" v-loading="busy">
    <h3>导入经历与草稿确认</h3>
    <p>支持文本型 PDF 与主动选择的历史 Markdown，暂不支持图片 OCR。请核对草稿；确认前不会写入经历库。</p>
    <div class="controls">
      <label>上传 PDF <input type="file" accept="application/pdf,.pdf" @change="upload" /></label>
      <el-select v-model="sourceId" placeholder="或选择已有 PDF" clearable>
        <el-option v-for="source in sources" :key="source.id" :value="source.id" :label="source.filename" />
      </el-select>
      <el-button v-if="moreSources" @click="loadMoreSources">更多已有 PDF</el-button>
      <el-button :disabled="!sourceId" @click="run(() => existingImport(sourceId!))">解析已有 PDF</el-button>
      <el-select :model-value="batch?.id" placeholder="恢复导入批次" @change="openBatch">
        <el-option v-for="row in batches" :key="row.id" :value="row.id" :label="`${statusLabel(row.status)} · ${row.id.slice(0, 8)}`" />
      </el-select>
      <el-button v-if="moreBatches" @click="loadMoreBatches">更早批次</el-button>
      <el-button @click="refresh">刷新批次</el-button>
    </div>
    <template v-if="batch">
      <el-alert :title="`${statusLabel(batch.status)} · 草稿保留至 ${batch.expires_at}`" :closable="false" />
      <el-alert v-if="batch.error" type="error" :title="`${batch.error.code}: ${batch.error.message}`" :closable="false" />
      <div class="controls">
        <el-button v-if="batch.status === 'FAILED'" @click="run(() => retryImport(batch!.id))">重试解析</el-button>
        <el-button v-if="['READY', 'FAILED', 'PROCESSING'].includes(batch.status)" @click="run(() => cancelImport(batch!.id))">取消本批次</el-button>
        <el-button v-if="batch.status === 'READY'" type="primary" :disabled="!selected.length || dirtyIds.length > 0" @click="confirm">确认选中的 {{ selected.length }} 条经历</el-button>
        <el-tag v-if="dirtyIds.length" type="warning">有 {{ dirtyIds.length }} 条未保存修正，请先保存</el-tag>
        <el-tag v-if="batch.status === 'CONFIRMED'" type="success">已确认入库；再次确认不会重复创建经历</el-tag>
      </div>
      <el-collapse>
        <el-collapse-item v-for="draft in batch.items" :key="draft.id" :name="draft.id" :title="`${draft.content.title || '待补充标题'}${draft.needs_correction ? ' · 需要修正' : ''}`">
          <el-checkbox v-model="selected" :value="draft.id" :disabled="batch.status !== 'READY'">选择此经历</el-checkbox>
          <p v-if="draft.source_locator.page">来源页码：{{ draft.source_locator.page }}</p>
          <blockquote v-if="draft.source_locator.snippet">{{ draft.source_locator.snippet }}</blockquote>
          <el-alert v-for="(issue, index) in draft.issues" :key="index" type="warning" :title="`${issue.field || ''} ${issue.message || issue.code || '请核实字段'}`" :closable="false" />
          <el-form label-position="top" :disabled="batch.status !== 'READY'">
            <el-form-item label="经历类型"><el-select v-model="draft.content.type" @change="changeType(draft)"><el-option v-for="(label, value) in typeLabels" :key="value" :value="value" :label="label" /></el-select></el-form-item>
            <el-form-item v-for="field in fields(draft)" :key="field.key" :label="field.label">
              <el-input v-if="field.array" :model-value="arrayText(draft.content[field.key])" type="textarea" :rows="3" @update:model-value="draft.content[field.key] = lines($event)" />
              <el-input v-else v-model="draft.content[field.key]" :type="field.key === 'description' ? 'textarea' : 'text'" />
            </el-form-item>
          </el-form>
          <el-button :disabled="batch.status !== 'READY'" @click="save(draft)">保存修正</el-button>
          <el-button type="danger" :disabled="batch.status !== 'READY'" @click="remove(draft)">删除草稿</el-button>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { cancelImport, confirmImport, editDraft, existingImport, getImport, listImports, listPDFSources, removeDraft, retryImport, uploadImport, type ImportBatch, type ImportDraft } from '@/api/experienceImports';
const emit = defineEmits<{ confirmed: [] }>();
const route = useRoute();
const busy = ref(false);
const batch = ref<ImportBatch>();
const batches = ref<Array<{ id: string; status: string }>>([]);
const sources = ref<Array<{ id: number; filename: string }>>([]);
const sourceId = ref<number>();
const sourcePage = ref(1), batchPage = ref(1), moreSources = ref(false), moreBatches = ref(false);
const selected = ref<string[]>([]);
const savedContents = ref<Record<string, string>>({});
const dirtyIds = computed(() => (batch.value?.items || []).filter(row => JSON.stringify(row.content) !== savedContents.value[row.id]).map(row => row.id));
function rememberSaved() { savedContents.value = Object.fromEntries((batch.value?.items || []).map(row => [row.id, JSON.stringify(row.content)])); }
const typeLabels: Record<string, string> = { WORK: '工作/实习', PROJECT: '项目', SKILL: '技能', CERTIFICATE: '证书', COMPETITION_AWARD: '比赛/荣誉' };
const statuses: Record<string, string> = { PROCESSING: '解析中', READY: '待核实确认', FAILED: '解析失败', CONFIRMED: '已确认', CANCELLED: '已取消', EXPIRED: '已过期' };
const statusLabel = (status: string) => statuses[status] || status;
const arrayText = (value: unknown) => Array.isArray(value) ? value.join('\n') : String(value || '');
const lines = (value: string) => value.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
function fields(draft: ImportDraft) {
  const common = [{ key: 'title', label: '标题' }, { key: 'start_date', label: '开始年月（YYYY-MM）' }, { key: 'end_date', label: '结束年月（YYYY-MM / present）' }, { key: 'tags', label: '标签（每行一个）', array: true }];
  const types: Record<string, Array<{ key: string; label: string; array?: boolean }>> = {
    WORK: [{ key: 'role', label: '角色' }, { key: 'department', label: '部门' }, { key: 'city', label: '城市' }, { key: 'bullets', label: '职责与成果（每行一条）', array: true }],
    PROJECT: [{ key: 'role', label: '角色' }, { key: 'project_url', label: '项目链接' }, { key: 'tech_stack', label: '技术栈（每行一个）', array: true }, { key: 'bullets', label: '成果（每行一条）', array: true }, { key: 'description', label: '说明' }],
    SKILL: [{ key: 'category', label: '技能分类' }, { key: 'skills', label: '技能（每行一个）', array: true }, { key: 'proficiency', label: '熟练度' }, { key: 'description', label: '说明' }],
    CERTIFICATE: [{ key: 'authority', label: '颁发机构' }, { key: 'issue_date', label: '颁发年月（YYYY-MM）' }, { key: 'certificate_no', label: '证书编号' }, { key: 'category', label: '类别' }, { key: 'description', label: '说明' }],
    COMPETITION_AWARD: [{ key: 'award_level', label: '奖项级别' }, { key: 'award_date', label: '获奖年月（YYYY-MM）' }, { key: 'organization', label: '主办方' }, { key: 'rank', label: '名次' }, { key: 'description', label: '说明' }],
  };
  return [...common, ...(types[draft.content.type] || [])];
}
function changeType(draft: ImportDraft) {
  const allowed = new Set(['type', ...fields(draft).map(field => field.key)]);
  draft.content = Object.fromEntries(Object.entries(draft.content).filter(([key]) => allowed.has(key)));
}
async function refresh() {
  batches.value = await listImports(); sources.value = await listPDFSources();
  sourcePage.value = batchPage.value = 1;
  moreSources.value = sources.value.length === 100; moreBatches.value = batches.value.length === 50;
  if (batch.value && !dirtyIds.value.length) { batch.value = await getImport(batch.value.id); rememberSaved(); }
}
async function loadMoreSources() {
  try { const rows = await listPDFSources(sourcePage.value + 1); sources.value.push(...rows); sourcePage.value++; moreSources.value = rows.length === 100; }
  catch (error) { ElMessage.error((error as Error).message); }
}
async function loadMoreBatches() {
  try { const rows = await listImports(batchPage.value + 1); batches.value.push(...rows); batchPage.value++; moreBatches.value = rows.length === 50; }
  catch (error) { ElMessage.error((error as Error).message); }
}
async function openBatch(id: string) { batch.value = await getImport(id); rememberSaved(); selected.value = batch.value.items.map(row => row.id); }
async function run(action: () => Promise<ImportBatch>) {
  busy.value = true;
  try { batch.value = await action(); rememberSaved(); selected.value = batch.value.items.map(row => row.id); await refresh(); }
  catch (error) {
    const failure = error as Error & { details?: { import_id?: string } };
    ElMessage.error(failure.message);
    if (failure.details?.import_id) await openBatch(failure.details.import_id);
  } finally { busy.value = false; }
}
async function upload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) await run(() => uploadImport(file));
  input.value = '';
}
async function save(draft: ImportDraft) {
  try {
    await editDraft(batch.value!.id, draft);
    const unsaved = batch.value!.items.filter(row => row.id !== draft.id && dirtyIds.value.includes(row.id)).map(row => ({ id: row.id, content: JSON.parse(JSON.stringify(row.content)) }));
    const checked = [...selected.value];
    batch.value = await getImport(batch.value!.id);
    rememberSaved();
    for (const local of unsaved) { const fresh = batch.value.items.find(row => row.id === local.id); if (fresh) fresh.content = local.content; }
    selected.value = checked;
    ElMessage.success('修正已保存，请再次核对后确认');
  } catch (error) { ElMessage.error(`${(error as Error).message}；请刷新批次核对最新版本，未保存的修正仍显示在当前表单。`); }
}
async function remove(draft: ImportDraft) {
  try { await ElMessageBox.confirm('删除这条草稿？正式经历库不受影响。', '删除草稿'); await removeDraft(batch.value!.id, draft); await openBatch(batch.value!.id); }
  catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
}
async function confirm() {
  try {
    await ElMessageBox.confirm('确认已核实所选经历的事实，并写入经历库？未保存的修改不会提交。', '确认经历');
    await confirmImport(batch.value!.id, batch.value!.items.filter(row => selected.value.includes(row.id)));
    await openBatch(batch.value!.id); emit('confirmed'); ElMessage.success('经历已确认入库');
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message); }
}
onMounted(() => { void refresh().then(() => typeof route.query.import === 'string' ? openBatch(route.query.import) : undefined).catch(error => ElMessage.error(error.message)); });
</script>
<style scoped>
.import-panel { padding: 18px; } .controls { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
blockquote { white-space: pre-wrap; padding: 12px; background: #f4f5f7; } .el-form { max-width: 700px; }
</style>
