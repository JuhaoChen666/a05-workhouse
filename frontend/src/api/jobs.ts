import request from './request';
import { apiOrigin } from './request';

// 热门岗位 / 招聘岗位基础结构（与 api.md 24、25、25.1 一致）
export interface HotJobItem {
  id: number;
  name: string;
  companyName: string;
  companyLogo: string;
  salaryMin: number | string;
  salaryMax: number | string;
  jobContent: string;
  type?: string;
}

export interface SearchJobsParams {
  keyword?: string;
  type?: string;
  page?: number;
  pageSize?: number;
}

export interface SearchJobsResult {
  list: HotJobItem[];
  total: number;
}

/** GET {apiOrigin}/jobs（无 /api 前缀） */
export async function getHotJobsApi(params?: { limit?: number }) {
  const data = await request.get<HotJobItem[]>(`${apiOrigin}/jobs`);
  const list = Array.isArray(data) ? data : [];
  const limit = Math.max(1, Number(params?.limit ?? list.length ?? 6));
  return list.slice(0, limit);
}

/** GET /jobs/:id */
export async function getJobDetailApi(id: number) {
  return request.get<HotJobItem>(`/jobs/${id}`);
}

/** GET /jobs/search */
export async function searchJobsApi(params: SearchJobsParams) {
  return request.get<SearchJobsResult>('/jobs/search', { params });
}

function formatSalaryOne(value: number | string): string {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '--';
    return value >= 1000 ? `${Math.round(value / 1000)}K` : String(value);
  }
  const raw = String(value || '').trim();
  if (!raw) return '--';
  const upper = raw.toUpperCase();
  if (/[KWM万千]/.test(upper)) return raw;
  const n = Number(upper.replace(/,/g, ''));
  if (Number.isFinite(n)) {
    return n >= 1000 ? `${Math.round(n / 1000)}K` : String(n);
  }
  return raw;
}

export function formatSalaryRange(min: number | string, max: number | string): string {
  return `${formatSalaryOne(min)} - ${formatSalaryOne(max)} / 月`;
}
