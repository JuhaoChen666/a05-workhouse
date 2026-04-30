import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { useUserStore } from '@/store/user';

/**
 * 认证：`{apiOrigin}/auth/login`（**无** `/api` 段），与多数远程网关一致。
 * 业务：`{apiOrigin}/...`（不再追加 `/api` 前缀；岗位管理走 `adminJsonBase`）。
 */
const PUBLIC_AUTH_PATHS = new Set([
  '/auth/login',
  '/auth/register',
  '/auth/send-code',
  '/auth/verify-code',
]);

function normalizedRequestPath(config: InternalAxiosRequestConfig): string {
  const raw = (config.url || '').split('?')[0] || '';
  if (!raw) return '';
  return raw.startsWith('/') ? raw : `/${raw}`;
}

export const apiOrigin =
  (import.meta.env.VITE_API_ORIGIN as string | undefined)?.replace(/\/$/, '').trim() ||
  '';

/** 业务接口根路径（无 `/api` 前缀）；模拟面试 AI 见 `interviewApiJsonBase`（8000） */
export const apiJsonBase = `${apiOrigin}`;

/**
 * 管理后台接口根路径（带 `/admin`），与真实后端用户/角色等文档一致。
 * 覆盖：`.env` 中 `VITE_ADMIN_API_PREFIX=/admin` 或 `admin`（默认 `/admin`）
 */
const rawAdminPrefix = (import.meta.env.VITE_ADMIN_API_PREFIX as string | undefined)?.trim() || '/admin';
const adminPathNoTrail = rawAdminPrefix.replace(/\/$/, '') || '/admin';
const adminPathPrefix = adminPathNoTrail.startsWith('/')
  ? adminPathNoTrail
  : `/${adminPathNoTrail}`;
export const adminJsonBase = `${apiOrigin}${adminPathPrefix}`;

/**
 * 模拟面试 AI（8000）。务必与后端实际监听地址一致，否则请求打到别的机器，对方会显示「没收到」。
 * 覆盖：`.env` 中 `VITE_INTERVIEW_API_ORIGIN=http://ip:端口`
 */
export const INTERVIEW_API_ORIGIN =
  (import.meta.env.VITE_INTERVIEW_API_ORIGIN as string | undefined)?.replace(/\/$/, '').trim() ||
  '';
  /*
  ''
  */
export const interviewApiJsonBase = `${INTERVIEW_API_ORIGIN}/api`;

/**
 * 认证接口根路径：`apiOrigin` 或 `apiOrigin + /api`（与仓库 server.js 的 `/api/auth/*` 对齐时设为 `/api`）。
 * 例：`.env` 中 `VITE_AUTH_API_PREFIX=/api`
 */
const rawAuthPrefix = (import.meta.env.VITE_AUTH_API_PREFIX as string | undefined)?.trim() || '';
const authPathPrefix = rawAuthPrefix.replace(/\/$/, '');
export const authBaseUrl =
  authPathPrefix === ''
    ? apiOrigin
    : `${apiOrigin}${authPathPrefix.startsWith('/') ? authPathPrefix : `/${authPathPrefix}`}`;

/** 从各类后端错误体里抽出可读说明（不含错误码前缀） */
function pickErrorMessage(payload: unknown): string | undefined {
  if (payload == null || typeof payload !== 'object') return undefined;
  const o = payload as Record<string, unknown>;
  const m = o.message ?? o.msg ?? (typeof o.error === 'string' ? o.error : undefined);
  if (typeof m === 'string' && m.trim()) return m.trim();
  const d = o.detail;
  if (typeof d === 'string' && d.trim()) return d.trim();
  if (Array.isArray(d) && d.length > 0) {
    const first = d[0] as Record<string, unknown> | undefined;
    if (first && typeof first === 'object') {
      const loc = Array.isArray(first.loc) ? String(first.loc.join('.')) : '';
      const msg = typeof first.msg === 'string' ? first.msg : '';
      const s = [loc, msg].filter(Boolean).join(' ');
      if (s.trim()) return s.trim();
    }
  }
  return undefined;
}

/** 后端可能返回数字或字符串 `0` / `200`，避免成功被误判为失败 */
function isSuccessCode(code: unknown): boolean {
  if (code === 0 || code === 200) return true;
  if (code === '0' || code === '200') return true;
  const n = Number(code);
  return !Number.isNaN(n) && (n === 0 || n === 200);
}

/**
 * 业务失败或 HTTP 错误体：提示中带错误码，便于对接文档里的 code 表。
 * 例：`[1009] 验证码错误或已过期`、`[HTTP 404] 请求失败`
 */
export function formatApiErrorText(payload: unknown, httpStatus?: number): string {
  if (payload != null && typeof payload === 'object') {
    const o = payload as { code?: unknown; message?: string };
    const msg =
      (typeof o.message === 'string' && o.message.trim() ? o.message.trim() : null) ||
      pickErrorMessage(payload) ||
      '请求错误';
    const code = o.code;
    const hasCode = code !== undefined && code !== null && code !== '';
    if (hasCode && !isSuccessCode(code)) {
      return `[${code}] ${msg}`;
    }
    if (httpStatus != null) return `[HTTP ${httpStatus}] ${msg}`;
    return msg;
  }
  const fromBody = pickErrorMessage(payload);
  if (fromBody) {
    return httpStatus != null ? `[HTTP ${httpStatus}] ${fromBody}` : fromBody;
  }
  if (httpStatus != null) return `[HTTP ${httpStatus}] 请求失败`;
  return '响应格式异常';
}

function unwrapResponse<T = unknown>(response: { data: unknown }) {
  const raw = response.data;
  if (raw == null || typeof raw !== 'object') {
    return Promise.reject(new Error(formatApiErrorText(null)));
  }
  const data = raw as { code?: unknown; message?: string; data?: T; result?: T };
  // 仅当显式携带 code 且非成功码时失败；无 code 时视为成功（兼容仅靠 HTTP 200 的网关）
  const hasCode = Object.prototype.hasOwnProperty.call(data, 'code');
  if (hasCode && !isSuccessCode(data.code)) {
    return Promise.reject(new Error(formatApiErrorText(data)));
  }
  // 兼容 data 或 result 作为业务载荷（如部分后端登录/业务接口用 result）
  const inner = data.data !== undefined ? data.data : data.result;
  // 若后端直接返回业务对象（如 { total, items, page, page_size }），则直接返回 raw
  if (inner === undefined) return raw as T;
  return inner as T;
}

function formatAxiosError(error: unknown): Error {
  const ax = error as {
    response?: { data?: unknown; status?: number };
    message?: string;
    code?: string;
  };
  const status = ax.response?.status;
  const body = ax.response?.data;
  if (body != null && typeof body === 'object' && ('code' in body || pickErrorMessage(body))) {
    return new Error(formatApiErrorText(body, status));
  }
  if (status == null) {
    const code =
      (typeof ax.code === 'string' && ax.code.trim()) ||
      (typeof ax.message === 'string' && /network error/i.test(ax.message) ? 'NETWORK_ERROR' : '') ||
      'NETWORK_ERROR';
    const detail = pickErrorMessage(body) || ax.message || '无法连接后端服务';
    return new Error(`[${code}] ${detail}`);
  }
  const msg =
    pickErrorMessage(body) ||
    (typeof ax.message === 'string' && ax.message ? ax.message : undefined) ||
    (status != null ? `[HTTP ${status}] 请求失败` : undefined) ||
    '网络或服务器错误';
  return new Error(msg);
}

const authAxios = axios.create({
  baseURL: authBaseUrl,
  timeout: 10000,
});
authAxios.interceptors.request.use((config) => {
  const path = normalizedRequestPath(config);
  const publicAuth = PUBLIC_AUTH_PATHS.has(path);
  const userStore = useUserStore();
  if (!config.headers) return config;
  if (publicAuth) {
    delete config.headers.Authorization;
    return config;
  }
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});
authAxios.interceptors.response.use(unwrapResponse, (err) => Promise.reject(formatAxiosError(err)));

const apiAxios = axios.create({
  baseURL: apiJsonBase,
  timeout: 10000,
});
apiAxios.interceptors.request.use((config) => {
  const userStore = useUserStore();
  if (!config.headers) return config;
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});
apiAxios.interceptors.response.use(unwrapResponse, (err) => Promise.reject(formatAxiosError(err)));

const adminAxios = axios.create({
  baseURL: adminJsonBase,
  timeout: 10000,
});
adminAxios.interceptors.request.use((config) => {
  const userStore = useUserStore();
  if (!config.headers) return config;
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});
adminAxios.interceptors.response.use(unwrapResponse, (err) => Promise.reject(formatAxiosError(err)));

const interviewAxios = axios.create({
  baseURL: interviewApiJsonBase,
  timeout: 120000,
});
interviewAxios.interceptors.request.use((config) => {
  const userStore = useUserStore();
  if (!config.headers) return config;
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});
interviewAxios.interceptors.response.use(unwrapResponse, (err) => Promise.reject(formatAxiosError(err)));

function wrapClient(inst: AxiosInstance) {
  return {
    get: <T = unknown>(url: string, config?: Parameters<typeof inst.get>[1]) =>
      inst.get(url, config) as Promise<T>,
    post: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof inst.post>[2]) =>
      inst.post(url, data, config) as Promise<T>,
    put: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof inst.put>[2]) =>
      inst.put(url, data, config) as Promise<T>,
    patch: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof inst.patch>[2]) =>
      inst.patch(url, data, config) as Promise<T>,
    delete: <T = unknown>(url: string, config?: Parameters<typeof inst.delete>[1]) =>
      inst.delete(url, config) as Promise<T>,
  };
}

/** `/auth/*`，实际根地址为 `authBaseUrl`（见 `VITE_AUTH_API_PREFIX`） */
export const authRequest = wrapClient(authAxios);

/** 默认业务：`{apiOrigin}/...` */
export default wrapClient(apiAxios);

/** 管理后台：`{apiOrigin}/admin/...`（见 `VITE_ADMIN_API_PREFIX`） */
export const adminRequest = wrapClient(adminAxios);

/** 仅模拟面试 AI：`{INTERVIEW_API_ORIGIN}/api/...` */
export const interviewRequest = wrapClient(interviewAxios);
