import { interviewRequest } from './request';
import type { SavedResumeDocument } from './resumeGeneration';

export type ResumeLibraryKind = 'uploaded' | 'generated';

export interface ResumeLibraryItem {
  key: string;
  kind: ResumeLibraryKind;
  id: number | string;
  name: string;
  format: 'pdf' | 'latex' | 'markdown';
  updated_at: string;
  thumbnail_url: string | null;
  generation_job_id?: string | null;
  copied_from_id?: string | null;
  document?: SavedResumeDocument;
}

export interface ResumeLibraryPage {
  total: number;
  page: number;
  page_size: number;
  uploaded_total: number;
  generated_total: number;
  items: ResumeLibraryItem[];
}

export function getResumeLibraryApi(page = 1, pageSize = 12, signal?: AbortSignal) {
  return interviewRequest.get<ResumeLibraryPage>('/resume-library', {
    params: { page: String(page), page_size: String(pageSize) },
    signal,
  });
}
