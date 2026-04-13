import request, { adminRequest } from './request';

/**
 * 后台管理 - 岗位、题库、学习资源、用户等接口封装。
 * - 用户、角色、**岗位**：真实后端挂在 **`/admin`** 下（`adminRequest` / `VITE_ADMIN_API_PREFIX`）
 * - 题库、学习资源：仍走默认 **`/api`**
 */

// 岗位列表项 / 详情项（列表分页 + 详情接口字段兼容 snake_case / camelCase）
export interface AdminPositionItem {
  id: number;
  name: string;
  sortOrder: number;
  city?: string;
  workExperience?: string;
  education?: string;
  salaryMin?: number;
  salaryMax?: number;
  responsibilities?: string;
  requirements?: string;
  tags?: string[] | string;
  publishDate?: string;
  /** 详情：岗位职责（接口多为 responsibility） */
  responsibility?: string;
  salary_junior?: string;
  salary_mid?: string;
  salary_senior?: string;
  salary_expert?: string;
  skill_requirements?: string;
}

/** 分页列表行（表格用） */
export interface AdminPositionRow {
  id: number;
  name: string;
  sortOrder: number;
}

export interface PositionPageResult {
  list: AdminPositionRow[];
  total: number;
}

/** 写入岗位详情 — `POST|PUT {origin}/admin/positions/info` */
export interface AdminPositionInfoPayload {
  id: number;
  name: string;
  responsibility: string;
  salary_junior: string;
  salary_mid: string;
  salary_senior: string;
  salary_expert: string;
  skill_requirements: string;
}

function pickSortOrder(row: Record<string, unknown>): number {
  const v = row.sort_order ?? row.sortOrder;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function normalizePositionPage(raw: unknown): PositionPageResult {
  if (Array.isArray(raw)) {
    const list: AdminPositionRow[] = raw.map((item) => {
      const r = item as Record<string, unknown>;
      return {
        id: Number(r.id),
        name: String(r.name ?? ''),
        sortOrder: pickSortOrder(r),
      };
    });
    return { list, total: list.length };
  }
  const o = (raw ?? {}) as Record<string, unknown>;
  const arr = Array.isArray(o.list)
    ? o.list
    : Array.isArray(o.items)
      ? o.items
      : Array.isArray(o.records)
        ? o.records
        : Array.isArray(o.data) && o.data.length > 0 && typeof o.data[0] === 'object'
          ? (o.data as unknown[])
          : [];
  const list: AdminPositionRow[] = arr.map((item) => {
    const r = item as Record<string, unknown>;
    return {
      id: Number(r.id),
      name: String(r.name ?? ''),
      sortOrder: pickSortOrder(r),
    };
  });
  const total = Number(o.total ?? o.count ?? list.length) || list.length;
  return { list, total };
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

export interface AdminResumeItem {
  id: number;
  userId: number | null;
  filename: string;
  localPath: string | null;
  contentText: string | null;
  uploadedAt: string | null;
}

export interface AdminResumePageResult {
  list: AdminResumeItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AdminSessionItem {
  sessionId: string;
  userId: number | null;
  resume: string | null;
  position: string | null;
  status: string | null;
  difficulty: string | null;
  currentTopic: string | null;
  currentQuestion: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface AdminSessionPageResult {
  list: AdminSessionItem[];
  total: number;
  page: number;
  pageSize: number;
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

/** 管理员分页查询简历（可按 userId 过滤） */
export function getAdminResumePageApi(params: { page?: number; pageSize?: number; userId?: number }) {
  return adminRequest.get<AdminResumePageResult>('/resumes/page', {
    params: {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 10,
      userId: params.userId,
    },
  });
}

/** 管理员删除简历 */
export function deleteAdminResumeApi(id: number) {
  return adminRequest.delete<string>(`/resumes/${id}`);
}

/** 管理员分页查询面试会话（可按 userId 过滤） */
export function getAdminSessionPageApi(params: {
  page?: number;
  pageSize?: number;
  userId?: number;
  order?: 'asc' | 'desc';
  sortBy?: string;
}) {
  const specialHeaderKey =
    (import.meta.env.VITE_ADMIN_SESSIONS_SPECIAL_HEADER_KEY as string | undefined)?.trim() || '';
  const specialHeaderValue =
    (import.meta.env.VITE_ADMIN_SESSIONS_SPECIAL_HEADER_VALUE as string | undefined)?.trim() || '';
  const headers: Record<string, string> = {};
  if (specialHeaderKey && specialHeaderValue) {
    headers[specialHeaderKey] = specialHeaderValue;
  }
  return adminRequest.get<AdminSessionPageResult>('/sessions/page', {
    params: {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 10,
      userId: params.userId,
      order: params.order,
      sortBy: params.sortBy,
    },
    headers,
  });
}

/** 管理员删除面试会话 */
export function deleteAdminSessionApi(sessionId: string) {
  return adminRequest.delete<string>(`/sessions/${encodeURIComponent(sessionId)}`);
}

/**
 * 分页模糊查询岗位 — `GET {apiOrigin}/positions/page`
 * Query: name, page, pageSize
 */
export async function getPositionPageApi(params: {
  name?: string;
  page?: number;
  pageSize?: number;
}): Promise<PositionPageResult> {
  const raw = await request.get<unknown>('/positions/page', {
    params: {
      name: params.name?.trim() || undefined,
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 10,
    },
  });
  return normalizePositionPage(raw);
}

/** 题库等下拉的岗位列表（一次拉较大 pageSize） */
export async function getPositionListApi(): Promise<AdminPositionItem[]> {
  const { list } = await getPositionPageApi({ page: 1, pageSize: 500 });
  return list.map((r) => ({
    id: r.id,
    name: r.name,
    sortOrder: r.sortOrder,
  }));
}

/** 获取单个岗位详情 — `GET {origin}/admin/positions/:id` */
export function getPositionDetailApi(id: number) {
  return adminRequest.get<AdminPositionItem | Record<string, unknown>>(`/positions/${id}`);
}

/**
 * 新建岗位（仅名称与排序）— `POST {apiOrigin}/positions`
 * Body: { name, sort_order }
 */
export function createPositionBasicApi(body: { name: string; sort_order: number }) {
  return request.post<Record<string, unknown>>('/positions', body);
}

/** 新建岗位详情 — `POST {origin}/admin/positions/info` */
export function createPositionInfoApi(body: AdminPositionInfoPayload) {
  return adminRequest.post<unknown>('/positions/info', body);
}

/** 更新岗位详情 — `PUT {origin}/admin/positions/info` */
export function updatePositionInfoApi(body: AdminPositionInfoPayload) {
  return adminRequest.put<unknown>('/positions/info', body);
}

/** 删除岗位 — `DELETE {origin}/admin/positions/:id` */
export function deletePositionApi(id: number) {
  return adminRequest.delete(`/positions/${id}`);
}

/** 从 POST /positions 响应中解析 id */
export function parseCreatedPositionId(raw: unknown): number {
  const o = (raw ?? {}) as Record<string, unknown>;
  const inner = o.data !== undefined && typeof o.data === 'object' ? (o.data as Record<string, unknown>) : o;
  const id = inner.id ?? o.id;
  const n = typeof id === 'number' ? id : Number(id);
  return Number.isFinite(n) ? n : NaN;
}

/**
 * @deprecated 旧版直连 admin POST /positions；请改用 createPositionBasicApi + createPositionInfoApi
 */
export async function createPositionApi(data: { name: string; sortOrder?: number }) {
  const raw = await createPositionBasicApi({
    name: data.name,
    sort_order: data.sortOrder ?? 0,
  });
  const id = parseCreatedPositionId(raw);
  return { id, name: data.name, sortOrder: data.sortOrder ?? 0 } as AdminPositionItem;
}

/**
 * @deprecated 旧版 PUT /positions/:id；请改用 updatePositionInfoApi
 */
export function updatePositionApi(id: number, data: Record<string, unknown>) {
  return adminRequest.put(`/positions/${id}`, data);
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

