import request from './request';

export interface InterviewRecordItem {
  id: number;
  positionId: number;
  positionName: string;
  startedAt: string;
  endedAt: string | null;
  totalScore: number | null;
}

export interface InterviewRecordListRes {
  list: InterviewRecordItem[];
  total: number;
}

export function getInterviewRecordListApi(params: {
  page?: number;
  pageSize?: number;
}) {
  return request.get<InterviewRecordListRes>('/interview-record', { params });
}

export interface InterviewStats {
  totalCount: number;
  finishedCount: number;
  avgScore: number | null;
  lastAt: string | null;
}

export function getInterviewStatsApi() {
  return request.get<InterviewStats>('/interview-record/stats');
}

export interface RecentScoreItem {
  interviewRecordId: number;
  positionName: string;
  startedAt: string;
  totalScore: number;
}

export function getRecentScoresApi(params?: { limit?: number }) {
  return request.get<RecentScoreItem[]>('/interview-record/recent-scores', { params });
}
