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
  const refs = evaluate(script + '\nexports.probe = { batch, savedContents, conflicts, dirtyIds, refresh, openBatch, run, resolveConflict, save };', name => {
    if (name === 'vue') return { ref: value => ({ value }), computed: fn => ({ get value() { return fn(); } }), onMounted() {}, onBeforeUnmount() {} };
    if (name === 'vue-router') return { useRoute: () => ({ query: {} }), onBeforeRouteLeave() {} };
    if (name === '@/utils/draftMerge') return merge;
    if (name === '@/api/experienceImports') return api;
    if (name === 'element-plus') return { ElMessage: { error() {}, success() {}, warning() {} }, ElMessageBox: { confirm: async () => { if (prompt !== 'save') throw prompt; } } };
    throw Error('unexpected import ' + name);
  }, { defineEmits: () => () => {} }).probe;
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
  const libraryScript = read('src/components/ResumeDocumentLibrary.vue').split('<script setup lang="ts">')[1].split('</script>')[0];
  let deleted = '', revoked = '';
  const library = evaluate(libraryScript + '\nexports.probe = { documents, detail, visible, previewVisible, previewURL, previewDocumentId, remove };', name => {
    if (name === 'vue') return { ref: value => ({ value }), reactive: value => value, onMounted() {}, onBeforeUnmount() {} };
    if (name === 'vue-router') return { useRouter: () => ({ push() {} }) };
    if (name === '@/api/request') return { interviewRequest: { delete: async url => { deleted = url; }, get: async () => [] }, INTERVIEW_API_ORIGIN: '' };
    if (name === '@/store/user') return { useUserStore: () => ({ token: 'test' }) };
    if (name === '@/api/experienceImports') return {};
    if (name === 'element-plus') return { ElMessage: { error() {} }, ElMessageBox: { confirm: async () => {} } };
    throw Error('unexpected library import ' + name);
  }, { URL: { revokeObjectURL: value => { revoked = value; } } }).probe;
  library.detail.value = { id: 'owned' }; library.visible.value = true;
  library.previewDocumentId.value = 'owned'; library.previewURL.value = 'blob:owned'; library.previewVisible.value = true;
  await library.remove({ id: 'owned', name: 'Mine' });
  assert.equal(deleted, '/resume-documents/owned'); assert.equal(library.visible.value, false);
  assert.equal(library.detail.value, undefined); assert.equal(library.previewVisible.value, false);
  assert.equal(revoked, 'blob:owned'); assert.equal(library.documents.value.length, 0);
  console.log('PASS: 204 response, repeated tags, revision merge, provenance, cancel/discard guards and save');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
