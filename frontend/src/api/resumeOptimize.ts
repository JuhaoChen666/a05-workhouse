import axios from 'axios';
import { interviewApiJsonBase, interviewRequest } from './request';
import { useUserStore } from '@/store/user';

export interface ResumeOptimizeImportRes {
  session_id: string;
  text_preview?: string;
}

export interface ResumeOptimizeStartRes {
  session_id?: string;
}

export interface ResumeOptimizeStatusRes {
  session_id: string;
  progress: number;
  status: string;
  result_markdown?: string;
}

/** POST /resume/optimize/import — form-data: user_id, file */
export function importResumeOptimizeApi(userId: string | number, file: File) {
  const fd = new FormData();
  fd.append('user_id', String(userId));
  fd.append('file', file, file.name || 'resume.pdf');
  return interviewRequest.post<ResumeOptimizeImportRes>('/resume/optimize/import', fd);
}

/** POST /resume/optimize/{sessionId} — 启动 AI 优化 */
export function startResumeOptimizeApi(sessionId: string) {
  return interviewRequest.post<ResumeOptimizeStartRes>(`/resume/optimize/${sessionId}`);
}

/** GET /resume/optimize/status/{sessionId} */
export function getResumeOptimizeStatusApi(sessionId: string) {
  return interviewRequest.get<ResumeOptimizeStatusRes>(`/resume/optimize/status/${sessionId}`);
}

/** GET 导出（可能为 PDF/HTML，不走 JSON unwrap） */
export async function exportResumeOptimizeBlob(sessionId: string): Promise<{ blob: Blob; filename: string }> {
  const token = useUserStore().token;
  const res = await axios.get(`${interviewApiJsonBase}/resume/optimize/export/${encodeURIComponent(sessionId)}`, {
    responseType: 'blob',
    timeout: 120000,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const cd = res.headers['content-disposition'] as string | undefined;
  let filename = `resume-optimize-${sessionId.slice(0, 8)}.pdf`;
  if (cd) {
    const m = /filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i.exec(cd) || /filename=["']?([^"';]+)["']?/i.exec(cd);
    if (m?.[1]) filename = decodeURIComponent(m[1].trim());
  }
  return { blob: res.data as Blob, filename };
}
