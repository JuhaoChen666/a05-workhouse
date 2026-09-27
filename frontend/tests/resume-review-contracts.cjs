// Runs actual TypeScript/component functions; API and Vue refs are controlled substitutes.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('../node_modules/typescript');
const axios = require('../node_modules/axios/dist/node/axios.cjs');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
function evaluate(source, requireMock = () => { throw Error('unexpected import'); }, extras = {}) {
  const context = { exports: {}, require: requireMock, ...extras };
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, context);
  return context.exports;
}
async function main() {
  const request = read('src/api/request.ts');
  const { unwrapResponse } = evaluate(request.slice(request.indexOf('function pickErrorMessage'), request.indexOf('function formatAxiosError')));
  assert.equal(await unwrapResponse({ status: 204, data: '' }), undefined);
  assert.equal(await unwrapResponse({ status: 200, data: { code: '0', data: 7 } }), 7);
  await assert.rejects(Promise.resolve().then(() => unwrapResponse({ status: 200, data: '' })));
  let config;
  const experiences = evaluate(read('src/api/experiences.ts'), () => ({ interviewRequest: { get: (_url, options) => { config = options; } } }));
  experiences.listExperiencesApi({ tag: ['Python', '后端'], type: 'PROJECT', keyword: 'api' });
  const uri = axios.getUri({ url: '/experiences', ...config });
  assert.deepEqual(new URL('http://test' + uri).searchParams.getAll('tag'), ['Python', '后端']);
  const merge = evaluate(read('src/utils/draftMerge.ts'));
  let response = { id: 'one', status: 'READY', items: [{ id: 'draft', revision: 2, content: { type: 'SKILL', title: 'Server' }, source_locator: { snippet: 'server provenance' } }] };
  let getCalls = 0, prompt = 'close', mutations = 0;
  const api = { listImports: async () => [], listPDFSources: async () => [],
    getImport: async id => { getCalls++; return { ...JSON.parse(JSON.stringify(response)), id }; },
    editDraft: async (_id, draft) => { assert.equal(draft.revision, 2); response.items[0].content = JSON.parse(JSON.stringify(draft.content)); response.items[0].revision++; } };
  const script = read('src/components/PdfExperienceImportPanel.vue').split('<script setup lang="ts">')[1].split('</script>')[0];
  const refs = evaluate(script + '\nexports.probe = { batch, savedContents, conflicts, dirtyIds, visible, busy, refresh, openBatch, run, resolveConflict, save, requestClose };', name => {
    if (name === 'vue') return { ref: value => ({ value }), computed: fn => ({ get value() { return fn(); } }), onMounted() {}, onBeforeUnmount() {} };
    if (name === 'vue-router') return { useRoute: () => ({ query: {} }), onBeforeRouteLeave() {} };
    if (name === '@/utils/draftMerge') return merge;
    if (name === '@/api/experienceImports') return api;
    if (name === 'element-plus') return { ElMessage: { error() {}, success() {}, warning() {}, info() {} }, ElMessageBox: { confirm: async () => { if (prompt !== 'save') throw prompt; } } };
    throw Error('unexpected import ' + name);
  }, { defineEmits: () => () => {}, defineExpose() {} }).probe;
  refs.batch.value = { id: 'one', status: 'READY', items: [{ id: 'draft', revision: 1, content: { type: 'SKILL', title: 'Local' } }] };
  refs.savedContents.value = { draft: JSON.stringify({ type: 'SKILL', title: 'Original' }) };
  await refs.refresh();
  assert.equal(getCalls, 1); assert.equal(refs.batch.value.items[0].revision, 2);
  assert.equal(refs.batch.value.items[0].content.title, 'Local');
  assert.equal(refs.batch.value.items[0].source_locator.snippet, 'server provenance');
  assert.equal(refs.conflicts.value.length, 1);
  await refs.openBatch('two');
  assert.equal(refs.batch.value.id, 'one'); // closing guard cancels switching
  await refs.run(async () => { mutations++; return response; });
  assert.equal(mutations, 0); // no new import is created before guard resolution
  refs.resolveConflict(refs.conflicts.value[0], false);
  assert.equal(await refs.save(refs.batch.value.items[0]), true);
  assert.equal(refs.dirtyIds.value.length, 0); assert.equal(refs.batch.value.items[0].revision, 3);
  let finishSave;
  api.editDraft = async (_id, draft) => {
    await new Promise(resolve => { finishSave = resolve; });
    response.items[0].content = JSON.parse(JSON.stringify(draft.content)); response.items[0].revision++;
  };
  refs.batch.value.items[0].content.title = 'Submitted';
  const pendingSave = refs.save(refs.batch.value.items[0]);
  refs.batch.value.items[0].content.title = 'Typed while saving';
  finishSave(); await pendingSave;
  assert.equal(refs.batch.value.items[0].content.title, 'Typed while saving');
  assert.equal(refs.dirtyIds.value.length, 1); // in-flight edits are never falsely marked saved
  refs.batch.value.items[0].content.title = 'Unsaved'; prompt = 'cancel';
  await refs.openBatch('two');
  assert.equal(refs.batch.value.id, 'two'); // explicit discard permits switching

  response.items[0].content = { title: 'Server after discard' };
  refs.batch.value = { id: 'one', status: 'READY', items: [{ id: 'draft', revision: 4, content: { title: 'Unsaved close' } }] };
  refs.savedContents.value = { draft: JSON.stringify({ title: 'Server before discard' }) };
  refs.visible.value = true; prompt = 'close';
  await refs.requestClose();
  assert.equal(refs.visible.value, true); assert.equal(refs.dirtyIds.value.length, 1); // close cancels
  prompt = 'cancel';
  await refs.requestClose();
  assert.equal(refs.visible.value, false); assert.equal(refs.batch.value.items[0].content.title, 'Server after discard');
  assert.equal(refs.dirtyIds.value.length, 0); // explicit discard reloads the server snapshot

  refs.batch.value.items[0].content.title = 'Busy change'; refs.visible.value = true; refs.busy.value = true;
  await refs.requestClose();
  assert.equal(refs.visible.value, true); refs.busy.value = false;
  prompt = 'save';
  finishSave = undefined;
  api.editDraft = async (_id, draft) => {
    await new Promise(resolve => { finishSave = resolve; });
    response.items[0].content = JSON.parse(JSON.stringify(draft.content)); response.items[0].revision++;
  };
  const guardedClose = refs.requestClose();
  for (let attempt = 0; attempt < 20 && !finishSave; attempt++) await new Promise(resolve => setImmediate(resolve));
  assert.equal(typeof finishSave, 'function');
  refs.batch.value.items[0].content.title = 'Typed during close save';
  finishSave(); await guardedClose;
  assert.equal(refs.visible.value, true); assert.equal(refs.dirtyIds.value.length, 1); // post-submit edits keep the dialog open
  const libraryScript = read('src/components/ResumeDocumentLibrary.vue').split('<script setup lang="ts">')[1].split('</script>')[0];
  let deleted = '', revoked = '', resolveResumeA, resolveGeneratedPdf, createObjectCalls = 0;
  let pageRequester = async () => ({ items: [], total: 0, page: 1, page_size: 12, uploaded_total: 0, generated_total: 0 });
  const library = evaluate(libraryScript + '\nexports.probe = { documents, detail, generatedDetailVisible, previewVisible, previewURL, previewLoading, previewError, previewDocumentId, setPreviewObjectUrl: url => { previewObjectUrl = url; }, currentPage, loading, remove, viewUploadedResume, previewGenerated, onPreviewVisibility, reload };', name => {
    if (name === 'vue') return { ref: value => ({ value }), reactive: value => value, onMounted() {}, onBeforeUnmount() {} };
    if (name === 'vue-router') return { useRouter: () => ({ push() {} }) };
    if (name === '@element-plus/icons-vue') return { Document: {}, MoreFilled: {}, Plus: {} };
    if (name === '@/api/request') return { interviewRequest: { delete: async url => { deleted = url; }, get: async () => [] }, INTERVIEW_API_ORIGIN: '' };
    if (name === '@/api/resumeAssets') return { buildInterviewAssetUrl: value => value };
    if (name === '@/config/resumeAssets') return { buildResumeFilePublicUrl: key => key ? `/data/resumes/${key}` : '' };
    if (name === '@/api/resumeLibrary') return { getResumeLibraryApi: (...args) => pageRequester(...args) };
    if (name === '@/api/resume') return { deleteResumeApi: async () => {}, getResumeItemApi: async id => id === 1 ? new Promise(resolve => { resolveResumeA = resolve; }) : { unique_filename: 'B.pdf' }, uploadResumeApi: async () => {} };
    if (name === '@/store/user') return { useUserStore: () => ({ token: 'test' }) };
    if (name === '@/api/experienceImports') return {};
    if (name === '@/components/ResumePdfPreview.vue' || name === '@/components/ResumeThumbnailImage.vue') return {};
    if (name === 'element-plus') return { ElMessage: { error() {} }, ElMessageBox: { confirm: async () => {} } };
    throw Error('unexpected library import ' + name);
  }, { URL: { revokeObjectURL: value => { revoked = value; }, createObjectURL: () => { createObjectCalls++; return 'blob:new'; } }, fetch: async () => new Promise(resolve => { resolveGeneratedPdf = () => resolve({ ok: true, blob: async () => new Blob(['pdf']) }); }), AbortController, Blob }).probe;
  const lateA = library.viewUploadedResume({ id: 1, key: 'uploaded-1', name: 'A.pdf', kind: 'uploaded' });
  await Promise.resolve();
  await library.viewUploadedResume({ id: 2, key: 'uploaded-2', name: 'B.pdf', kind: 'uploaded' });
  resolveResumeA({ unique_filename: 'A.pdf' }); await lateA;
  assert.equal(library.previewURL.value, '/data/resumes/B.pdf'); // stale A cannot replace later B
  const closedA = library.viewUploadedResume({ id: 1, key: 'uploaded-1', name: 'A.pdf', kind: 'uploaded' });
  await Promise.resolve(); library.onPreviewVisibility(false); resolveResumeA({ unique_filename: 'A-late.pdf' }); await closedA;
  assert.equal(library.previewURL.value, ''); assert.equal(library.previewLoading.value, false); // close aborts stale response
  const latePdf = library.previewGenerated({ id: 'g1', key: 'generated-g1', name: 'Generated', kind: 'generated', format: 'latex' });
  await Promise.resolve(); library.onPreviewVisibility(false); resolveGeneratedPdf(); await latePdf;
  assert.equal(createObjectCalls, 0); assert.equal(library.previewURL.value, ''); // closed response never creates a Blob URL
  let resolveListA, resolveListB;
  pageRequester = page => new Promise(resolve => { if (page === 1) resolveListA = resolve; else resolveListB = resolve; });
  library.currentPage.value = 1; const oldPage = library.reload(); await Promise.resolve();
  library.currentPage.value = 2; const newPage = library.reload(); await Promise.resolve();
  resolveListB({ items: [{ key: 'generated-new', name: 'Page B' }], total: 30, page: 2, page_size: 12, uploaded_total: 15, generated_total: 15 }); await newPage;
  resolveListA({ items: [{ key: 'generated-old', name: 'Page A' }], total: 30, page: 1, page_size: 12, uploaded_total: 15, generated_total: 15 }); await oldPage;
  assert.equal(library.documents.value[0].name, 'Page B'); assert.equal(library.loading.value, false); // stale page and loading state cannot overwrite B
  pageRequester = async page => ({ items: [], total: 0, page, page_size: 12, uploaded_total: 0, generated_total: 0 });
  library.detail.value = { id: 'owned' }; library.generatedDetailVisible.value = true;
  library.previewDocumentId.value = 'owned'; library.previewURL.value = 'blob:owned'; library.setPreviewObjectUrl('blob:owned'); library.previewVisible.value = true;
  await library.remove({ id: 'owned', name: 'Mine' });
  assert.equal(deleted, '/resume-documents/owned'); assert.equal(library.generatedDetailVisible.value, false);
  assert.equal(library.detail.value, undefined); assert.equal(library.previewVisible.value, false);
  assert.equal(revoked, 'blob:owned'); assert.equal(library.documents.value.length, 0);
}
const watchdog = setTimeout(() => {
  console.error('FAIL: contract run exceeded 15 seconds (possible unresolved async request)');
  process.exitCode = 1;
}, 15000);
main().then(() => {
  clearTimeout(watchdog);
  console.log('PASS: response parsing, repeated tags, protected import close/discard, save-during-edit, stale preview and page cancellation, delete cleanup');
}).catch(error => {
  clearTimeout(watchdog);
  console.error(error);
  process.exitCode = 1;
});
