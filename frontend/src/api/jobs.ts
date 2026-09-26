import request from './request';

// 热门岗位 / 招聘岗位基础结构（与 api.md 24、25、25.1 一致）
export interface HotJobItem {
  id: number;
  name: string;
  englishName?: string | null;
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

export interface SimplePositionItem {
  id: number;
  name: string;
  englishName?: string | null;
  responsibility?: string;
}

export interface SimplePositionPageRes {
  total: number;
  pageSize: number;
  page: number;
  list: SimplePositionItem[];
}

export interface PositionDetailRes {
  id: number;
  name?: string;
  type?: string;
  content?: string;
  jobContent?: string;
  description?: string;
  responsibility?: string;
  skill_requirements?: string;
  companyName?: string;
  responsibilities?: string;
  requirements?: string;
}

/** GET {apiOrigin}/jobs/hot（本机 Mock 与线上热门岗位契约一致） */
export async function getHotJobsApi(params?: { limit?: number }) {
  const data = await request.get<HotJobItem[]>('/jobs/hot', {
    params: { limit: params?.limit },
  });
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

/** GET /positions/simple/page */
export async function getSimplePositionPageApi(params: {
  page: number;
  pageSize: number;
  name?: string;
}) {
  const keyword = params.name?.trim().toLowerCase() || '';
  try {
    const result = await request.get<unknown>('/positions/simple/page', {
      params: { page: params.page, pageSize: params.pageSize, name: params.name },
    });
    return normalizePositionPage(result, params);
  } catch {
    // The local mock server exposes /positions rather than the remote paging API.
    // Keep the UI usable locally while preserving the preferred remote contract.
    const result = await request.get<unknown>('/positions');
    return normalizePositionPage(result, {
      ...params,
      name: keyword,
    });
  }
}

/** GET /positions/:id */
export async function getPositionDetailApi(id: number | string) {
  const raw = await request.get<unknown>(`/positions/${id}`);
  const detail = unwrapPositionPayload(raw);
  if (!detail || typeof detail !== 'object') {
    throw new Error('岗位详情服务返回格式异常');
  }
  const value = detail as PositionDetailRes;
  return {
    ...value,
    responsibility: value.responsibility || value.responsibilities || '',
    skill_requirements: value.skill_requirements || value.requirements || '',
  };
}

function unwrapPositionPayload(value: unknown): unknown {
  if (!value || typeof value !== 'object') return value;
  const record = value as Record<string, unknown>;
  return record.data ?? record.result ?? value;
}

function normalizePositionPage(value: unknown, params: { page: number; pageSize: number; name?: string }): SimplePositionPageRes {
  const payload = unwrapPositionPayload(value);
  const record = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {};
  const rawList = Array.isArray(payload)
    ? payload
    : Array.isArray(record.list)
      ? record.list
      : Array.isArray(record.items)
        ? record.items
        : [];
  const keyword = params.name?.trim().toLowerCase() || '';
  const list = rawList
    .map((item) => {
      const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
      return {
        id: Number(row.id),
        name: String(row.name || row.positionName || ''),
        englishName: row.englishName == null ? undefined : String(row.englishName),
        responsibility: row.responsibility == null ? undefined : String(row.responsibility),
      };
    })
    .filter((item) => item.id > 0 && (!keyword || item.name.toLowerCase().includes(keyword)));
  const page = Math.max(1, params.page);
  const pageSize = Math.max(1, params.pageSize);
  const start = (page - 1) * pageSize;
  const paged = list.slice(start, start + pageSize);
  return {
    total: list.length,
    pageSize,
    page,
    list: paged,
  };
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
