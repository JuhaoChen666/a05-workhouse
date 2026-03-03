import request from './request';

export interface PositionItem {
  id: number;
  name: string;
  sortOrder: number;
}

export interface UserItem {
  id: string;
  username: string;
  email?: string;
  roleId: number;
  roleName: string;
}

export interface QuestionBankItem {
  id: number;
  positionId: number;
  positionName: string;
  question: string;
  answer: string | null;
  knowledgeTags: string | null;
}

export interface LearningResourceItem {
  id: number;
  title: string;
  link: string;
  tags: string | null;
}

export interface InterviewRecordItem {
  id: number;
  positionId: number;
  positionName: string;
  startedAt: string;
  endedAt: string | null;
  totalScore: number | null;
}

// 角色
export function getRolesApi() {
  return request.get<{ id: number; name: string }[]>('/roles');
}

// 用户列表（管理员）
export function getUserListApi(params: { page?: number; pageSize?: number }) {
  return request.get<{ list: UserItem[]; total: number }>('/users', { params });
}

// 岗位
export function getPositionListApi() {
  return request.get<PositionItem[]>('/positions');
}

export function getPositionDetailApi(id: number) {
  return request.get<PositionItem>(`/positions/${id}`);
}

export function createPositionApi(data: { name: string; sortOrder?: number }) {
  return request.post<PositionItem>('/positions', data);
}

export function updatePositionApi(id: number, data: { name?: string; sortOrder?: number }) {
  return request.put(`/positions/${id}`, data);
}

export function deletePositionApi(id: number) {
  return request.delete(`/positions/${id}`);
}

// 题库
export function getQuestionBankListApi(params: {
  page?: number;
  pageSize?: number;
  positionId?: number;
}) {
  return request.get<{ list: QuestionBankItem[]; total: number }>('/question-bank', { params });
}

export function getQuestionBankDetailApi(id: number) {
  return request.get<QuestionBankItem>(`/question-bank/${id}`);
}

export function createQuestionBankApi(data: {
  positionId: number;
  question: string;
  answer?: string;
  knowledgeTags?: string;
}) {
  return request.post<QuestionBankItem>('/question-bank', data);
}

export function updateQuestionBankApi(
  id: number,
  data: { positionId?: number; question?: string; answer?: string; knowledgeTags?: string }
) {
  return request.put(`/question-bank/${id}`, data);
}

export function deleteQuestionBankApi(id: number) {
  return request.delete(`/question-bank/${id}`);
}

// 学习资源
export function getLearningResourceListApi(params: {
  page?: number;
  pageSize?: number;
  tags?: string;
}) {
  return request.get<{ list: LearningResourceItem[]; total: number }>('/learning-resource', {
    params,
  });
}

export function createLearningResourceApi(data: { title: string; link: string; tags?: string }) {
  return request.post<LearningResourceItem>('/learning-resource', data);
}

export function updateLearningResourceApi(
  id: number,
  data: { title?: string; link?: string; tags?: string }
) {
  return request.put(`/learning-resource/${id}`, data);
}

export function deleteLearningResourceApi(id: number) {
  return request.delete(`/learning-resource/${id}`);
}
