import { interviewRequest } from './request';

export interface ImportDraft {
  id: string;
  revision: number;
  content: Record<string, any>;
  issues: Array<{ message?: string; field?: string; code?: string }>;
  source_locator: Record<string, any>;
  needs_correction: boolean;
}
export interface ImportBatch {
  id: string;
  status: 'PROCESSING' | 'READY' | 'FAILED' | 'CONFIRMED' | 'CANCELLED' | 'EXPIRED';
  error?: { code: string; message: string };
  items: ImportDraft[];
  expires_at: string;
  source_format?: 'pdf' | 'markdown';
  confirmation_result?: { experience_ids: string[] };
}
export const listImports = (page = 1) => interviewRequest.get<Array<{ id: string; status: string }>>('/experience-imports', { params: { page } });
export const listPDFSources = (page = 1) => interviewRequest.get<Array<{ id: number; filename: string }>>('/experience-imports/sources', { params: { page } });
export const getImport = (id: string) => interviewRequest.get<ImportBatch>(`/experience-imports/${id}`);
export function uploadImport(file: File) {
  const body = new FormData();
  body.append('file', file);
  return interviewRequest.post<ImportBatch>('/experience-imports/upload', body, { timeout: 120000 });
}
export const existingImport = (source_resume_id: number) => interviewRequest.post<ImportBatch>('/experience-imports/existing', { source_resume_id }, { timeout: 120000 });
export const retryImport = (id: string) => interviewRequest.post<ImportBatch>(`/experience-imports/${id}/retry`, {}, { timeout: 120000 });
export const cancelImport = (id: string) => interviewRequest.post<ImportBatch>(`/experience-imports/${id}/cancel`);
export const editDraft = (batch: string, draft: ImportDraft) => interviewRequest.put(`/experience-imports/${batch}/items/${draft.id}`, { content: draft.content, expected_revision: draft.revision });
export const removeDraft = (batch: string, draft: ImportDraft) => interviewRequest.delete(`/experience-imports/${batch}/items/${draft.id}`, { params: { expected_revision: draft.revision } });
export const confirmImport = (batch: string, drafts: ImportDraft[]) => interviewRequest.post(`/experience-imports/${batch}/confirm`, { items: drafts.map(({ id, revision }) => ({ id, expected_revision: revision })) });
export const markdownImport = (legacy_optimization_id: string) => interviewRequest.post<ImportBatch>('/experience-imports/markdown', { legacy_optimization_id }, { timeout: 120000 });
