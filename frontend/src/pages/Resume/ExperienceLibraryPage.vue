<template>
  <section class="experience-page theme-page-shell">
    <div class="toolbar theme-card">
      <div>
        <h3>经历库</h3>
        <p>集中管理项目、工作、技能、证书和获奖经历，生成简历时可直接复用。</p>
      </div>
      <el-button type="primary" class="theme-primary-btn" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新增经历
      </el-button>
    </div>

    <PdfExperienceImportPanel @confirmed="reload" />
    <div class="filters theme-card">
      <el-input v-model="keyword" clearable placeholder="搜索标题、标签或内容" @keyup.enter="reload">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="typeFilter" clearable placeholder="全部类型" @change="reload">
        <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input v-model="tagFilter" clearable placeholder="标签筛选" @keyup.enter="reload" />
      <el-select v-model="archiveFilter" @change="reload">
        <el-option label="当前经历" value="active" />
        <el-option label="已归档" value="archived" />
        <el-option label="全部" value="all" />
      </el-select>
      <el-button :icon="Refresh" circle title="刷新" @click="reload" />
    </div>

    <div class="table-wrap theme-card">
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column label="保存顺序（小值在前）" width="200">
          <template #default="{ row }"><el-input-number :model-value="row.sort_order" :min="0" :max="2147483647" @change="saveOrder(row, $event)" /></template>
        </el-table-column>
        <el-table-column label="经历" min-width="240">
          <template #default="{ row }">
            <div class="title-cell">
              <strong>{{ row.title }}</strong>
              <span>{{ typeLabel(row.type) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="300">
          <template #default="{ row }">{{ summary(row) }}</template>
        </el-table-column>
        <el-table-column label="标签" min-width="170">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            <span v-if="!row.tags?.length" class="muted">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="150">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'PDF_IMPORT' ? 'warning' : 'info'" size="small">
              {{ row.source_type === 'PDF_IMPORT' ? 'PDF 导入' : row.source_type === 'MARKDOWN_IMPORT' ? '历史 Markdown 确认' : '手动录入' }}
            </el-tag>
            <p v-if="row.source_locator.page">第 {{ row.source_locator.page }} 页</p>
            <el-tooltip v-if="row.source_locator.snippet" :content="String(row.source_locator.snippet)"><span>查看来源片段</span></el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="175" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link @click="toggleArchive(row)">
              {{ row.is_archived ? '恢复' : '归档' }}
            </el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !items.length" description="还没有匹配的经历" :image-size="72" />
      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, prev, pager, next"
          :total="total"
          @current-change="fetchItems"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑经历' : '新增经历'" width="680px">
      <el-form :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="经历类型" required>
            <el-select v-model="form.type" :disabled="Boolean(editingId)">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题" required>
            <el-input v-model="form.title" placeholder="例如：智能招聘平台" />
          </el-form-item>
          <el-form-item label="开始年月">
            <el-input v-model="form.start_date" placeholder="YYYY-MM" />
          </el-form-item>
          <el-form-item label="结束年月">
            <el-input v-model="form.end_date" placeholder="YYYY-MM 或 present" />
          </el-form-item>
        </div>

        <template v-if="form.type === 'WORK' || form.type === 'PROJECT'">
          <div class="form-grid">
            <el-form-item label="角色" required><el-input v-model="form.role" /></el-form-item>
            <el-form-item v-if="form.type === 'WORK'" label="部门"><el-input v-model="form.department" /></el-form-item>
            <el-form-item v-if="form.type === 'WORK'" label="城市"><el-input v-model="form.city" /></el-form-item>
            <el-form-item v-if="form.type === 'PROJECT'" label="项目链接"><el-input v-model="form.project_url" /></el-form-item>
          </div>
          <el-form-item v-if="form.type === 'PROJECT'" label="技术栈">
            <el-input v-model="form.tech_stack_text" placeholder="每行一个技术栈" />
          </el-form-item>
          <el-form-item label="核心亮点" required>
            <el-input v-model="form.bullets_text" type="textarea" :rows="5" placeholder="每行一个亮点，尽量包含动作和结果" />
          </el-form-item>
        </template>

        <template v-else-if="form.type === 'SKILL'">
          <div class="form-grid">
            <el-form-item label="技能分类" required><el-input v-model="form.category" /></el-form-item>
            <el-form-item label="熟练度"><el-input v-model="form.proficiency" /></el-form-item>
          </div>
          <el-form-item label="技术栈" required>
            <el-input v-model="form.skills_text" type="textarea" :rows="4" placeholder="每行一个技能" />
          </el-form-item>
          <el-form-item label="补充说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="form.type === 'CERTIFICATE'">
          <div class="form-grid">
            <el-form-item label="颁发机构"><el-input v-model="form.authority" /></el-form-item>
            <el-form-item label="获得年月" required><el-input v-model="form.issue_date" placeholder="YYYY-MM" /></el-form-item>
            <el-form-item label="证书编号"><el-input v-model="form.certificate_no" /></el-form-item>
            <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
          </div>
          <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else>
          <div class="form-grid">
            <el-form-item label="奖项等级" required><el-input v-model="form.award_level" /></el-form-item>
            <el-form-item label="获奖年月" required><el-input v-model="form.award_date" placeholder="YYYY-MM" /></el-form-item>
            <el-form-item label="主办单位"><el-input v-model="form.organization" /></el-form-item>
            <el-form-item label="名次/角色"><el-input v-model="form.rank" /></el-form-item>
          </div>
          <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        </template>

        <el-form-item label="标签">
          <el-input v-model="form.tags_text" placeholder="多个标签用逗号分隔，例如：Python, FastAPI, AI" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import PdfExperienceImportPanel from '@/components/PdfExperienceImportPanel.vue';
import { interviewRequest } from '@/api/request';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Refresh, Search } from '@element-plus/icons-vue';
import {
  archiveExperienceApi,
  createExperienceApi,
  deleteExperienceApi,
  listExperiencesApi,
  updateExperienceApi,
} from '@/api/experiences';
import type { ExperienceItemResponse, ExperienceType } from '@/types/resumeLatexContracts';

const typeOptions: Array<{ label: string; value: ExperienceType }> = [
  { label: '工作/实习', value: 'WORK' },
  { label: '项目经历', value: 'PROJECT' },
  { label: '专业技能', value: 'SKILL' },
  { label: '证书/知识产权', value: 'CERTIFICATE' },
  { label: '比赛/荣誉', value: 'COMPETITION_AWARD' },
];
const items = ref<ExperienceItemResponse[]>([]);
const loading = ref(false);
const saving = ref(false);
const page = ref(1);
const pageSize = ref(12);
const total = ref(0);
const keyword = ref('');
const tagFilter = ref('');
const typeFilter = ref<ExperienceType>();
const archiveFilter = ref<'active' | 'archived' | 'all'>('active');
const dialogVisible = ref(false);
const editingId = ref<string>();

const emptyForm = () => reactive<Record<string, any>>({
  type: 'WORK',
  title: '',
  start_date: '',
  end_date: '',
  tags_text: '',
  role: '',
  department: '',
  city: '',
  project_url: '',
  tech_stack_text: '',
  bullets_text: '',
  category: '',
  skills_text: '',
  proficiency: '',
  authority: '',
  issue_date: '',
  certificate_no: '',
  award_level: '',
  award_date: '',
  organization: '',
  rank: '',
  description: '',
});
let form = emptyForm();

async function saveOrder(row: ExperienceItemResponse, value: number | undefined) {
  if (value == null || value === row.sort_order) return;
  try {
    await interviewRequest.patch(`/experiences/${row.id}/order`, { sort_order: value, expected_revision: row.revision });
    await fetchItems();
  } catch (error) { ElMessage.error((error as Error).message); await fetchItems(); }
}

function typeLabel(type: ExperienceType) {
  return typeOptions.find((item) => item.value === type)?.label || type;
}

function summary(row: ExperienceItemResponse) {
  const attrs = row.attributes || {};
  const values = [
    attrs.role,
    attrs.category,
    attrs.skills && Array.isArray(attrs.skills) ? attrs.skills.join('、') : attrs.skills,
    attrs.bullets && Array.isArray(attrs.bullets) ? attrs.bullets[0] : attrs.bullets,
    attrs.description,
  ].filter(Boolean);
  return String(values[0] || '暂无摘要');
}

async function fetchItems() {
  loading.value = true;
  try {
    const response = await listExperiencesApi({
      page: page.value,
      page_size: pageSize.value,
      type: typeFilter.value,
      keyword: keyword.value.trim() || undefined,
      tag: tagFilter.value.split(',').map((item) => item.trim()).filter(Boolean),
      archive: archiveFilter.value,
    });
    items.value = response.items || [];
    total.value = response.total || 0;
  } catch (error) {
    ElMessage.error((error as Error).message || '经历加载失败');
  } finally {
    loading.value = false;
  }
}

function reload() {
  page.value = 1;
  void fetchItems();
}

function openCreate() {
  editingId.value = undefined;
  form = emptyForm();
  dialogVisible.value = true;
}

function openEdit(row: ExperienceItemResponse) {
  const attrs = row.attributes || {};
  editingId.value = row.id;
  form = emptyForm();
  Object.assign(form, {
    type: row.type,
    title: row.title,
    start_date: row.start_date || '',
    end_date: row.end_date || '',
    tags_text: row.tags.join(', '),
    ...attrs,
    skills_text: Array.isArray(attrs.skills) ? attrs.skills.join('\n') : '',
    tech_stack_text: Array.isArray(attrs.tech_stack) ? attrs.tech_stack.join('\n') : '',
    bullets_text: Array.isArray(attrs.bullets) ? attrs.bullets.join('\n') : '',
  });
  dialogVisible.value = true;
}

function splitLines(value: string) {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
}

function payload() {
  const current = items.value.find(item => item.id === editingId.value);
  const common = {
    type: form.type,
    title: String(form.title).trim(),
    start_date: String(form.start_date || '').trim() || null,
    end_date: String(form.end_date || '').trim() || null,
    tags: String(form.tags_text || '').split(',').map((item: string) => item.trim()).filter(Boolean),
    source_type: 'MANUAL',
    source_resume_id: null,
    source_locator: {},
    sort_order: current?.sort_order ?? 0,
    is_archived: current?.is_archived ?? false,
  };
  if (form.type === 'WORK') {
    return { ...common, role: String(form.role).trim(), department: form.department || null, city: form.city || null, bullets: splitLines(form.bullets_text) };
  }
  if (form.type === 'PROJECT') {
    return { ...common, role: String(form.role).trim(), project_url: form.project_url || null, tech_stack: splitLines(form.tech_stack_text), description: form.description || null, bullets: splitLines(form.bullets_text) };
  }
  if (form.type === 'SKILL') {
    return { ...common, category: String(form.category).trim(), skills: splitLines(form.skills_text), proficiency: form.proficiency || null, description: form.description || null };
  }
  if (form.type === 'CERTIFICATE') {
    return { ...common, authority: form.authority || null, issue_date: String(form.issue_date).trim(), certificate_no: form.certificate_no || null, category: form.category || null, description: form.description || null };
  }
  return { ...common, award_level: String(form.award_level).trim(), award_date: String(form.award_date).trim(), organization: form.organization || null, rank: form.rank || null, description: form.description || null };
}

async function save() {
  saving.value = true;
  try {
    if (editingId.value) {
      const current = items.value.find((item) => item.id === editingId.value);
      if (!current) return;
      await updateExperienceApi(editingId.value, current.revision, payload() as any);
    } else {
      await createExperienceApi(payload() as any);
    }
    dialogVisible.value = false;
    ElMessage.success('经历已保存');
    await fetchItems();
  } catch (error) {
    ElMessage.error((error as Error).message || '保存失败');
  } finally {
    saving.value = false;
  }
}

async function toggleArchive(row: ExperienceItemResponse) {
  try {
    await archiveExperienceApi(row.id, row.revision, !row.is_archived);
    ElMessage.success(row.is_archived ? '经历已恢复' : '经历已归档');
    await fetchItems();
  } catch (error) {
    ElMessage.error((error as Error).message || '操作失败');
  }
}

async function remove(row: ExperienceItemResponse) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title}」吗？此操作不可恢复。`, '删除经历', { type: 'warning' });
    await deleteExperienceApi(row.id, row.revision);
    ElMessage.success('经历已删除');
    await fetchItems();
  } catch (error) {
    if (error === 'cancel' || error === 'close') return;
    ElMessage.error((error as Error).message || '删除失败');
  }
}

onMounted(() => void fetchItems());
</script>

<style scoped>
.experience-page { display: grid; gap: 16px; }
.toolbar, .filters { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 16px 18px; flex-wrap: wrap; }
.toolbar h3 { margin: 0 0 6px; color: #111827; }
.toolbar p { margin: 0; color: #6b7280; font-size: 13px; }
.filters :deep(.el-input) { width: 240px; }
.filters :deep(.el-select) { width: 150px; }
.table-wrap { padding: 8px; }
.title-cell { display: grid; gap: 4px; }
.title-cell span, .muted { color: #94a3b8; font-size: 12px; }
.pagination { display: flex; justify-content: flex-end; padding: 14px 8px 6px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.form-grid :deep(.el-select), .form-grid :deep(.el-input) { width: 100%; }
.table-wrap :deep(.el-tag) { margin: 2px 4px 2px 0; }
@media (max-width: 768px) {
  .filters :deep(.el-input), .filters :deep(.el-select) { width: 100%; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
