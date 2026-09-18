import { interviewRequest } from './request';
import type { ExperienceItem, ExperienceType, ExperienceItemResponse } from '@/types/resumeLatexContracts';

export interface ExperiencePage {
  items: ExperienceItemResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface ExperienceListParams {
  page?: number;
  page_size?: number;
  type?: ExperienceType;
  tag?: string[];
  keyword?: string;
  archive?: 'active' | 'archived' | 'all';
}

export function listExperiencesApi(params: ExperienceListParams = {}) {
  return interviewRequest.get<ExperiencePage>('/experiences', {
    params: { ...params, tag: params.tag?.filter(Boolean) },
  });
}

export function createExperienceApi(item: ExperienceItem) {
  return interviewRequest.post<ExperienceItemResponse>('/experiences', item);
}

export function updateExperienceApi(id: string, expectedRevision: number, item: ExperienceItem) {
  return interviewRequest.put<ExperienceItemResponse>(`/experiences/${encodeURIComponent(id)}`, {
    expected_revision: expectedRevision,
    item,
  });
}

export function archiveExperienceApi(id: string, expectedRevision: number, isArchived: boolean) {
  return interviewRequest.patch<ExperienceItemResponse>(
    `/experiences/${encodeURIComponent(id)}/archive`,
    { expected_revision: expectedRevision, is_archived: isArchived },
  );
}

export function reorderExperienceApi(id: string, expectedRevision: number, sortOrder: number) {
  return interviewRequest.patch<ExperienceItemResponse>(
    `/experiences/${encodeURIComponent(id)}/order`,
    { expected_revision: expectedRevision, sort_order: sortOrder },
  );
}

export function deleteExperienceApi(id: string, expectedRevision: number) {
  return interviewRequest.delete(`/experiences/${encodeURIComponent(id)}`, {
    params: { expected_revision: expectedRevision },
  });
}
