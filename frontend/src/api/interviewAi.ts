import { interviewRequest, interviewApiJsonBase } from './request';
import { useUserStore } from '@/store/user';

const MIN_STREAM_EVENT_DELAY_MS = 20;

/**
 * 模拟面试 AI：创建会话、上传简历（走统一 request 解包 data）
 * 流式对话使用原生 fetch，因响应体非 JSON 包装格式
 */

export interface StartInterviewBody {
  resume: string;
  position: string;
  collection_name: string;
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
}

/**
 * 面试回答流式 NDJSON（与后端一致）。
 * - voice_processing / analyzing：进度文案在 data.message
 * - analysis_result：评价与引导在 data.feedback，另有 depth_score、is_vague、need_followup 等
 * - error：业务失败，data.message 为人类可读说明；收到后前端应停止继续解析后续 NDJSON
 */
export interface InterviewAnswerStreamEvent {
  type:
    | 'voice_processing'
    | 'analyzing'
    | 'analysis_result'
    | 'followup'
    | 'question_chunk'
    | 'question'
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

export function endInterviewSessionApi(sessionId: string) {
  return interviewRequest.delete<{ session_id: string; status: 'ended' }>(
    `/interview/session/${sessionId}`
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
 * - file：二进制文件（示例文件名 fronten.wav）
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
  const uploadName = audioFile.name?.trim() || 'fronten.wav';
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
