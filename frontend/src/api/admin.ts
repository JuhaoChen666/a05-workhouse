import request, { adminRequest } from './request';

/**
 * 后台管理 - 岗位、题库、学习资源、用户等接口封装。
 * - 用户、角色、**岗位**：真实后端挂在 **`/admin`** 下（`adminRequest` / `VITE_ADMIN_API_PREFIX`）
 * - 题库、学习资源：仍走默认 **`/api`**
 */

// 岗位列表项 / 详情项
export interface AdminPositionItem {
  id: number;
  name: string;
  sortOrder: number;
  // 以下字段来自 admin `/positions/:id` 详情结构，用于后台管理编辑
  city?: string;
  workExperience?: string;
  education?: string;
  salaryMin?: number;
  salaryMax?: number;
  responsibilities?: string;
  requirements?: string;
  tags?: string[] | string;
  publishDate?: string;
}

// 用户列表项
export interface AdminUserItem {
  id: number;
  username: string;
  email?: string;
  avatar?: string;
  roleId: number;
  roleName: string;
}

export interface AdminUserDetail {
  id: number;
  username: string;
  email?: string;
  roleId: number;
  avatar?: string;
}

// 题库列表项
export interface AdminQuestionBankItem {
  id: number;
  positionId: number;
  positionName: string;
  question: string;
  answer: string | null;
  knowledgeTags: string | null;
}

// 学习资源列表项
export interface AdminLearningResourceItem {
  id: number;
  title: string;
  link: string;
  tags: string | null;
}

// 后台查看的面试记录项（如后续需要可扩展使用）
export interface AdminInterviewRecordItem {
  id: number;
  userId: number;
  userName: string;
  positionId: number;
  positionName: string;
  startedAt: string;
  endedAt: string | null;
  totalScore: number | null;
}

/** 管理员获取用户列表（分页） — `GET {origin}/admin/users` */
export function getUserListApi(params: { page?: number; pageSize?: number }) {
  return adminRequest.get<{ list: AdminUserItem[]; total: number }>('/users', { params });
}

/** 管理员获取用户详情 */
export function getUserDetailApi(id: number) {
  return adminRequest.get<AdminUserDetail>(`/users/${id}`);
}

/** 管理员创建用户 */
export function createUserApi(data: {
  username: string;
  password: string;
  email?: string;
  roleId?: number;
}) {
  return adminRequest.post('/users', data);
}

/** 管理员更新用户 */
export function updateUserApi(
  id: number,
  data: {
    username?: string;
    email?: string;
    roleId?: number;
    password?: string;
  }
) {
  return adminRequest.put(`/users/${id}`, data);
}

/** 管理员删除用户 */
export function deleteUserApi(id: number) {
  return adminRequest.delete(`/users/${id}`);
}

/** 获取全部岗位列表 — `GET {origin}/admin/positions` */
export function getPositionListApi() {
  return adminRequest.get<AdminPositionItem[]>('/positions');
}

/** 获取单个岗位详情（包含扩展字段） */
export function getPositionDetailApi(id: number) {
  return adminRequest.get<AdminPositionItem>(`/positions/${id}`);
}

/** 新增岗位（管理员） */
export function createPositionApi(
  data: {
    name: string;
    sortOrder?: number;
    city?: string;
    workExperience?: string;
    education?: string;
    salaryMin?: number;
    salaryMax?: number;
    responsibilities?: string;
    requirements?: string;
    tags?: string[] | string;
    publishDate?: string;
  }
) {
  return adminRequest.post<AdminPositionItem>('/positions', data);
}

/** 更新岗位（管理员） */
export function updatePositionApi(
  id: number,
  data: {
    name?: string;
    sortOrder?: number;
    city?: string;
    workExperience?: string;
    education?: string;
    salaryMin?: number;
    salaryMax?: number;
    responsibilities?: string;
    requirements?: string;
    tags?: string[] | string;
    publishDate?: string;
  }
) {
  return adminRequest.put(`/positions/${id}`, data);
}

/** 删除岗位（管理员） */
export function deletePositionApi(id: number) {
  return adminRequest.delete(`/positions/${id}`);
}

/** 获取题库列表（分页 + 岗位筛选） */
export function getQuestionBankListApi(params: {
  page?: number;
  pageSize?: number;
  positionId?: number;
}) {
  return request.get<{ list: AdminQuestionBankItem[]; total: number }>('/question-bank', { params });
}

/** 获取单个题库题目详情 */
export function getQuestionBankDetailApi(id: number) {
  return request.get<AdminQuestionBankItem>(`/question-bank/${id}`);
}

/** 新增题目（管理员） */
export function createQuestionBankApi(data: {
  positionId: number;
  question: string;
  answer?: string;
  knowledgeTags?: string;
}) {
  return request.post<AdminQuestionBankItem>('/question-bank', data);
}

/** 更新题目（管理员） */
export function updateQuestionBankApi(
  id: number,
  data: { positionId?: number; question?: string; answer?: string; knowledgeTags?: string }
) {
  return request.put(`/question-bank/${id}`, data);
}

/** 删除题目（管理员） */
export function deleteQuestionBankApi(id: number) {
  return request.delete(`/question-bank/${id}`);
}

/** 获取学习资源列表（分页） */
export function getLearningResourceListApi(params: {
  page?: number;
  pageSize?: number;
  tags?: string;
}) {
  return request.get<{ list: AdminLearningResourceItem[]; total: number }>('/learning-resource', {
    params,
  });
}

/** 新增学习资源（管理员） */
export function createLearningResourceApi(data: { title: string; link: string; tags?: string }) {
  return request.post<AdminLearningResourceItem>('/learning-resource', data);
}

/** 更新学习资源（管理员） */
export function updateLearningResourceApi(
  id: number,
  data: { title?: string; link?: string; tags?: string }
) {
  return request.put(`/learning-resource/${id}`, data);
}

/** 删除学习资源（管理员） */
export function deleteLearningResourceApi(id: number) {
  return request.delete(`/learning-resource/${id}`);
}

