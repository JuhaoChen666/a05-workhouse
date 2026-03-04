import request from './request';

// 热门岗位 / 招聘岗位基础结构
export interface HotJobItem {
  id: number;
  name: string;
  companyName: string;
  companyLogo: string;
  salaryMin: number;
  salaryMax: number;
  jobContent: string;
  // 岗位类型（用于搜索筛选），如：backend / frontend / algo / fullstack / other
  type?: string;
}

// 获取首页热门岗位列表
export function getHotJobsApi(params?: { limit?: number }) {
  return request.get<HotJobItem[]>('/jobs/hot', { params });
}

// 获取单个岗位详情
export function getJobDetailApi(id: number) {
  return request.get<HotJobItem>(`/jobs/${id}`);
}

// 招聘岗位搜索（支持关键词与岗位类型筛选）
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

export function searchJobsApi(params: SearchJobsParams) {
  return request.get<SearchJobsResult>('/jobs/search', { params });
}
