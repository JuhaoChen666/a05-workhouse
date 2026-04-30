import { interviewRequest } from './request';

export interface ResumeUploadRes {
  id?: number;
  filename?: string;
  text_preview?: string;
}

export interface ResumeListItem {
  id: number;
  filename: string;
  uploaded_at: string;
}

export interface ResumeListRes {
  total: number;
  items: ResumeListItem[];
  page: number;
  page_size: number;
}

export interface ResumeDeleteBody {
  id: number;
  user_id: string | number;
  filename: string;
}

export interface ResumeItemRes {
  id: number;
  filename: string;
  unique_filename?: string;
  uploaded_at?: string;
}

export function uploadResumeApi(userId: string | number, file: File) {
  const fd = new FormData();
  fd.append('user_id', String(userId));
  fd.append('file', file, file.name || 'resume.pdf');
  return interviewRequest.post<ResumeUploadRes>('/resumes/upload', fd);
}

export function getResumeListApi(userId: string | number, page = 1, pageSize = 5) {
  return interviewRequest.get<ResumeListRes>('/resumes/list', {
    params: {
      user_id: String(userId),
      page: String(page),
      page_size: String(pageSize),
    },
  });
}

export function deleteResumeApi(body: ResumeDeleteBody) {
  return interviewRequest.delete<unknown>('/resumes/delete', { data: body });
}

export function getResumeItemApi(id: number | string) {
  return interviewRequest.get<ResumeItemRes>(`/resumes/item/${id}`);
}
