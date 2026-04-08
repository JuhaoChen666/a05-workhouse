import { interviewRequest } from './request';

export interface ResumeUploadRes {
  id?: number;
  filename?: string;
  text_preview?: string;
}

export function uploadResumeApi(userId: string | number, file: File) {
  const fd = new FormData();
  fd.append('user_id', String(userId));
  fd.append('file', file, file.name || 'resume.pdf');
  return interviewRequest.post<ResumeUploadRes>('/resumes/upload', fd);
}
