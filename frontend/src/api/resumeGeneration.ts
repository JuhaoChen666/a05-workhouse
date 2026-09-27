import { interviewRequest } from './request';
import { buildInterviewAssetUrl } from './resumeAssets';
import type {
  ResumeGenerationJob,
  ResumeGenerationRequest,
  ResumeTemplateSummary,
} from '@/types/resumeLatexContracts';

export interface SavedResumeDocument {
  id: string;
  name: string;
  format: 'latex' | 'markdown';
  generation_job_id?: string | null;
  created_at: string;
  updated_at: string;
  thumbnail_url?: string | null;
}

export function createResumeGenerationApi(payload: ResumeGenerationRequest) {
  return interviewRequest.post<ResumeGenerationJob>('/resume-generation/jobs', payload);
}

export function getResumeGenerationApi(jobId: string) {
  return interviewRequest.get<ResumeGenerationJob>(
    `/resume-generation/jobs/${encodeURIComponent(jobId)}`,
  );
}

export function retryResumeGenerationApi(jobId: string) {
  return interviewRequest.post<ResumeGenerationJob>(
    `/resume-generation/jobs/${encodeURIComponent(jobId)}/retry`,
  );
}

export function confirmResumeReviewApi(jobId: string, version: string, accepted_indices: number[]) {
  return interviewRequest.post<ResumeGenerationJob>(`/resume-generation/jobs/${encodeURIComponent(jobId)}/review`, { version, accepted_indices });
}

export function listSavedResumeDocumentsApi() {
  return interviewRequest.get<SavedResumeDocument[]>('/resume-generation/documents');
}

export function buildResumeGenerationAssetUrl(jobId: string, format: 'pdf' | 'latex') {
  return buildInterviewAssetUrl(`/api/resume-generation/jobs/${encodeURIComponent(jobId)}/${format}`);
}

export function listGenerationTemplatesApi() {
  return interviewRequest.get<ResumeTemplateSummary[]>('/resume-templates');
}
