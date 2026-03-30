import request from './request';

export interface ReportContent {
  totalScore?: number;
  dimensions?: { name: string; score: number; comment?: string }[];
  summary?: string;
  suggestions?: string[];
}

export interface ReportItem {
  id: number;
  interviewRecordId: number;
  content: ReportContent;
}

export function getReportByRecordIdApi(interviewRecordId: number) {
  return request.get<ReportItem>('/report', { params: { interviewRecordId } });
}
