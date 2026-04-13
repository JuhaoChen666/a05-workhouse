import { interviewRequest, interviewApiJsonBase } from './request';
import { useUserStore } from '@/store/user';

const MIN_STREAM_EVENT_DELAY_MS = 20;

/**
 * 模拟面试 AI：创建会话、上传简历（走统一 request 解包 data）
 * 流式对话使用原生 fetch，因响应体非 JSON 包装格式
 */

export interface StartInterviewBody {
  resume_id: number;
  position: string;
  collection_name: string;
  user_id?: string | number;
  difficulty?: 'easy' | 'medium' | 'hard' | string;
}

export interface StartInterviewRes {
  session_id: string;
  status: 'questioning' | 'ended';
  total_rounds: number;
  current_topic: string;
  current_question: string;
  history: InterviewSessionHistoryItem[];
}

export interface InterviewSessionHistoryItem {
  round: number;
  question: string;
  answer: string;
  topic: string;
  timestamp: string;
}

export interface InterviewSessionInfo {
  session_id: string;
  status: 'questioning' | 'ended';
  total_rounds: number;
  current_topic: string;
  current_question: string;
  history: InterviewSessionHistoryItem[];
  interview_mode?: 'text' | 'voice' | 'avatar';
  /** 部分后端会返回，用于前端计算面试已进行时长 */
  created_at?: string;
  started_at?: string;
}

/** GET /interview/session/:sessionId/evaluation（8000 等服务端） */
export interface InterviewEvaluationData {
  session_id: string;
  strengths?: string[];
  weaknesses?: string[];
  overall_score?: number;
  recommendation?: string;
  overall_comment?: string;
  technical_evaluation?: string;
  communication_evaluation?: string;
}

export interface UserInterviewSessionItem {
  session_id: string;
  position?: string;
  position_name?: string;
  status: 'questioning' | 'completed' | 'ended' | string;
  created_at: string;
  updated_at: string;
}

export interface UserInterviewSessionPageRes {
  list: UserInterviewSessionItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UserEvaluationTrendData {
  xAxis?: { type?: string; data?: string[] };
  yAxis?: { type?: string };
  series?: Array<{ data?: number[]; type?: string; smooth?: boolean }>;
}

export interface SessionEvaluationRadarData {
  indicator?: Array<{ name?: string; max?: number }>;
  value?: number[];
  // 兼容旧结构 radar: [{name,max,value}] 与新结构 radar: { indicator: [...] }
  radar?: Array<{ name?: string; max?: number; value?: number }> | { indicator?: Array<{ name?: string; max?: number }> };
  series?: Array<{ value?: number[]; data?: Array<{ value?: number[]; name?: string }> }>;
}

export interface AvatarSessionStartRes {
  session_id: string;
  avatar_session_id: string;
  vendor: string;
  avatar_id: string;
  sdk_config: {
    app_id: string;
    server_url: string;
    signed_url: string;
    scene_id: string;
    vcn: string;
    protocol: 'xrtc' | 'webrtc';
    alpha: 0 | 1;
    token: string;
    expire_at: number;
  };
}

export interface AvatarSessionRefreshRes {
  session_id: string;
  avatar_session_id: string;
  sdk_config: {
    token: string;
    expire_at: number;
  };
}

/**
 * 面试回答流式 NDJSON（与后端一致）。
 * - voice_processing / analyzing：进度文案在 data.message
 * - analysis_result：评价与引导在 data.feedback，另有 depth_score、is_vague、need_followup 等
 * - checking_completeness / completeness_result：主题完整性检查阶段
 * - topic_completed：本话题结束（data.topic / reason）
 * - error：业务失败，data.message 为人类可读说明；收到后前端应停止继续解析后续 NDJSON
 */
export interface InterviewAnswerStreamEvent {
  type:
    | 'voice_processing'
    | 'analyzing'
    | 'analysis_result'
    | 'checking_completeness'
    | 'completeness_result'
    | 'topic_completed'
    | 'followup'
    | 'question_chunk'
    | 'question'
    | 'interview_complete'
    | 'error';
  data: Record<string, unknown>;
  timestamp: string;
}

export function startInterviewApi(body: StartInterviewBody) {
  return interviewRequest.post<StartInterviewRes>('/interview/start', body);
}

export function getInterviewSessionApi(sessionId: string) {
  return interviewRequest.get<InterviewSessionInfo>(`/interview/session/${sessionId}`);
}

/** 面试评估报告（与联调服务一致：`code` 常为 200） */
export function getInterviewEvaluationApi(sessionId: string) {
  return interviewRequest.get<InterviewEvaluationData>(`/interview/session/${sessionId}/evaluation`);
}

/** 获取某个用户的历史面试会话（按时间倒序） */
export function getUserInterviewSessionsApi(userId: string | number) {
  return interviewRequest.get<UserInterviewSessionItem[]>(`/interview/user/${userId}/sessions`);
}

/** 分页获取用户会话列表：`/interview/user/:userId/sessions/page` */
export async function getUserInterviewSessionsPageApi(
  userId: string | number,
  params?: { page?: number; pageSize?: number }
) {
  const page = Number(params?.page ?? 1) || 1;
  const pageSize = Number(params?.pageSize ?? 10) || 10;
  const raw = await interviewRequest.get<unknown>(`/interview/user/${userId}/sessions/page`, {
    params: {
      page,
      pageSize,
      page_size: pageSize,
    },
  });
  // 兼容后端不同分页结构：data 可能是数组，或 { list, total, ... }
  if (Array.isArray(raw)) {
    return {
      list: raw as UserInterviewSessionItem[],
      total: raw.length,
      page,
      pageSize,
    } satisfies UserInterviewSessionPageRes;
  }
  const obj = (raw ?? {}) as Record<string, unknown>;
  const list = Array.isArray(obj.list)
    ? (obj.list as UserInterviewSessionItem[])
    : Array.isArray(obj.items)
      ? (obj.items as UserInterviewSessionItem[])
      : [];
  return {
    list,
    total: Number(obj.total ?? obj.count ?? list.length) || list.length,
    page: Number(obj.page ?? obj.page_num ?? page) || page,
    pageSize: Number(obj.pageSize ?? obj.page_size ?? pageSize) || pageSize,
  } satisfies UserInterviewSessionPageRes;
}

/** 用户评分趋势：`/interview/user/:userId/evaluation/trend` */
export function getUserEvaluationTrendApi(userId: string | number) {
  return interviewRequest.get<UserEvaluationTrendData>(`/interview/user/${userId}/evaluation/trend`);
}

/** 会话雷达图：`/interview/session/:sessionId/evaluation/radar` */
export function getSessionEvaluationRadarApi(sessionId: string) {
  return interviewRequest.get<SessionEvaluationRadarData>(`/interview/session/${sessionId}/evaluation/radar`);
}

export function endInterviewSessionApi(sessionId: string) {
  return interviewRequest.delete<{ session_id: string; status: 'ended' }>(
    `/interview/session/${sessionId}`
  );
}

export function startAvatarInterviewSessionApi(
  sessionId: string,
  avatarId = '110592024'
) {
  return interviewRequest.post<AvatarSessionStartRes>('/interview/avatar/session/start', {
    session_id: sessionId,
    avatar_id: avatarId,
  });
}

export function refreshAvatarInterviewSessionApi(sessionId: string, avatarSessionId: string) {
  return interviewRequest.post<AvatarSessionRefreshRes>('/interview/avatar/session/refresh', {
    session_id: sessionId,
    avatar_session_id: avatarSessionId,
  });
}

export function speakAvatarApi(sessionId: string, text: string, interrupt = true) {
  return interviewRequest.post<{ accepted: boolean; task_id: string }>('/interview/avatar/speak', {
    session_id: sessionId,
    text,
    interrupt,
  });
}

export function endAvatarInterviewSessionApi(sessionId: string) {
  return interviewRequest.delete<{ session_id: string; status: 'ended' }>(
    `/interview/avatar/session/${sessionId}`
  );
}

async function readNdjsonStream(
  res: Response,
  onEvent: (evt: InterviewAnswerStreamEvent) => void,
  meta?: { url: string }
) {
  const urlHint = meta?.url ? ` 请求: ${meta.url}` : '';
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const body = (text || '').trim().slice(0, 800);
    throw new Error(
      `HTTP ${res.status}${urlHint}${body ? ` — ${body}` : ` — ${res.statusText || '无响应体'}`}`
    );
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error(`无法读取响应流${urlHint}`);
  const decoder = new TextDecoder();
  let buffer = '';
  let lastEmitAt = 0;
  readLoop: while (true) {
    const { done, value } = await reader.read();
    if (done) break readLoop;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      const raw = line.trim();
      if (!raw) continue;
      let evt: InterviewAnswerStreamEvent;
      try {
        evt = JSON.parse(raw) as InterviewAnswerStreamEvent;
      } catch {
        throw new Error(`NDJSON 解析失败${urlHint}，行片段: ${raw.slice(0, 200)}`);
      }
      const now = Date.now();
      const waitMs = Math.max(0, MIN_STREAM_EVENT_DELAY_MS - (now - lastEmitAt));
      if (waitMs > 0) {
        // 控制极小显示间隔，避免渲染抖动但保持高速输出
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, waitMs));
      }
      onEvent(evt);
      lastEmitAt = Date.now();
      if (evt.type === 'error') {
        void reader.cancel().catch(() => {});
        break readLoop;
      }
      if (evt.type === 'interview_complete') {
        void reader.cancel().catch(() => {});
        break readLoop;
      }
    }
  }
}

export async function streamInterviewAnswer(
  sessionId: string,
  answer: string,
  onEvent: (evt: InterviewAnswerStreamEvent) => void
): Promise<void> {
  const store = useUserStore();
  const token = store.token;
  if (!token) {
    throw new Error('未登录');
  }

  const url = `${interviewApiJsonBase}/interview/answer`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      Accept: 'application/x-ndjson',
    },
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
  await readNdjsonStream(res, onEvent, { url });
}

/**
 * 语音回答：multipart/form-data，与 Apifox 一致
 * - session_id：字符串
 * - file：二进制文件（文件名应与真实 MIME 对应，如 .webm/.wav）
 */
export async function streamInterviewVoiceAnswer(
  sessionId: string,
  audioFile: File,
  onEvent: (evt: InterviewAnswerStreamEvent) => void
): Promise<void> {
  const store = useUserStore();
  const token = store.token;
  if (!token) throw new Error('未登录');

  const fd = new FormData();
  fd.append('session_id', sessionId);
  const uploadName = audioFile.name?.trim() || 'frontend-record.webm';
  fd.append('file', audioFile, uploadName);

  const voiceUrl = `${interviewApiJsonBase}/interview/answer-voice`;
  const res = await fetch(voiceUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/x-ndjson',
    },
    body: fd,
  });
  await readNdjsonStream(res, onEvent, { url: voiceUrl });
}

/** 押题流式事件（与 8000 `/api/interview/predict-questions/stream` 对齐） */
export interface PredictQuestionStreamEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface PredictQuestionsBody {
  resume_id: number;
  position: string;
}

/**
 * POST `/interview/predict-questions/stream`，NDJSON：
 * - prediction_item：{ id, question, key_points, answer, difficulty }
 * - prediction_complete / predict_complete：结束
 * - error
 */
export async function streamPredictQuestions(
  body: PredictQuestionsBody,
  onEvent: (evt: PredictQuestionStreamEvent) => void
): Promise<void> {
  const store = useUserStore();
  const token = store.token;
  if (!token) {
    throw new Error('未登录');
  }

  const url = `${interviewApiJsonBase}/interview/predict-questions/stream`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      Accept: 'application/x-ndjson',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const bodyPreview = (text || '').trim().slice(0, 800);
    throw new Error(
      `HTTP ${res.status} — ${bodyPreview || res.statusText || '无响应体'}`
    );
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';

  readLoop: while (true) {
    const { done, value } = await reader.read();
    if (done) break readLoop;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      const raw = line.trim();
      if (!raw) continue;
      let evt: PredictQuestionStreamEvent;
      try {
        evt = JSON.parse(raw) as PredictQuestionStreamEvent;
      } catch {
        throw new Error(`NDJSON 解析失败，行片段: ${raw.slice(0, 200)}`);
      }
      onEvent(evt);
      if (
        evt.type === 'error' ||
        evt.type === 'predict_complete' ||
        evt.type === 'prediction_complete'
      ) {
        void reader.cancel().catch(() => {});
        break readLoop;
      }
    }
  }
}

export async function streamInterviewOpening(
  sessionId: string,
  onEvent: (evt: InterviewAnswerStreamEvent) => void
): Promise<void> {
  const store = useUserStore();
  const token = store.token;
  if (!token) throw new Error('未登录');

  const url = `${interviewApiJsonBase}/interview/opening-stream`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      Accept: 'application/x-ndjson',
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  await readNdjsonStream(res, onEvent, { url });
}
