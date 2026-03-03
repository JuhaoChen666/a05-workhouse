import request from './request';

export interface HotJobItem {
  id: number;
  name: string;
  companyName: string;
  companyLogo: string;
  salaryMin: number;
  salaryMax: number;
  jobContent: string;
}

export function getHotJobsApi(params?: { limit?: number }) {
  return request.get<HotJobItem[]>('/jobs/hot', { params });
}

export function getJobDetailApi(id: number) {
  return request.get<HotJobItem>(`/jobs/${id}`);
}
