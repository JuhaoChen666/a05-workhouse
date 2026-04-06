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

/**
 * 远程未提供 /jobs 接口（如 404）时的本地示例数据，保证首页卡片与搜索/详情可演示。
 */
export const FALLBACK_HOT_JOBS: HotJobItem[] = [
  {
    id: 1,
    name: '移动端开发工程师(Android)',
    companyName: '示例公司',
    companyLogo: 'ByteDance',
    salaryMin: 18000,
    salaryMax: 30000,
    jobContent:
      '负责 Android 客户端开发与性能优化，熟悉 Kotlin/Java、组件化、网络请求、数据存储与稳定性治理。',
    type: 'frontend',
  },
  {
    id: 2,
    name: '后端开发工程师',
    companyName: '示例公司',
    companyLogo: 'Alibaba',
    salaryMin: 20000,
    salaryMax: 35000,
    jobContent:
      '负责后端接口设计与实现，熟悉 Java/Spring、MySQL、缓存与消息队列，关注高并发与可用性。',
    type: 'backend',
  },
];

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

function searchFallbackLocal(params: SearchJobsParams): SearchJobsResult {
  const keyword = String(params.keyword || '')
    .trim()
    .toLowerCase();
  const type = String(params.type || '').trim();
  const page = Math.max(1, Number(params.page || 1));
  const pageSize = Math.max(1, Number(params.pageSize || 10));
  let list = [...FALLBACK_HOT_JOBS];
  if (type) list = list.filter((j) => j.type === type);
  if (keyword) {
    list = list.filter((j) =>
      [j.name, j.companyName, j.jobContent].some((v) => String(v || '').toLowerCase().includes(keyword))
    );
  }
  const total = list.length;
  const start = (page - 1) * pageSize;
  return { list: list.slice(start, start + pageSize), total };
}

/** GET {apiOrigin}/jobs（无 /api 前缀）；失败时使用 FALLBACK_HOT_JOBS */
export async function getHotJobsApi(params?: { limit?: number }) {
  try {
    const data = await request.get<HotJobItem[]>(`${apiOrigin}/jobs`);
    const list = Array.isArray(data) ? data : [];
    const limit = Math.max(1, Number(params?.limit ?? list.length ?? 6));
    return list.slice(0, limit);
  } catch {
    const limit = Math.max(1, Number(params?.limit ?? FALLBACK_HOT_JOBS.length));
    return FALLBACK_HOT_JOBS.slice(0, limit);
  }
}

/** GET /jobs/:id；失败时在 FALLBACK_HOT_JOBS 中按 id 查找 */
export async function getJobDetailApi(id: number) {
  try {
    return await request.get<HotJobItem>(`/jobs/${id}`);
  } catch {
    const item = FALLBACK_HOT_JOBS.find((j) => j.id === Number(id));
    if (item) return item;
    throw new Error('岗位不存在');
  }
}

/** GET /jobs/search；失败时在本地示例数据中筛选分页 */
export async function searchJobsApi(params: SearchJobsParams) {
  try {
    return await request.get<SearchJobsResult>('/jobs/search', { params });
  } catch {
    return searchFallbackLocal(params);
  }
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
