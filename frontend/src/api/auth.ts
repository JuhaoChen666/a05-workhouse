import { authRequest, adminRequest } from './request';
import type { LoginRequest, RegisterRequest, UserInfo } from '../types/auth';

/** 登录接口解析结果（兼容多种后端字段命名与嵌套） */
export interface LoginApiResult {
  token: string;
  user: UserInfo | null;
}

/**
 * 将 unwrap 后的登录载荷规范为 token + user。
 * 兼容：accessToken / access_token、userInfo / user_info、以及 user 字段与根级扁平共存。
 */
function normalizeLoginResult(raw: unknown): LoginApiResult {
  if (raw == null || typeof raw !== 'object') {
    throw new Error('登录响应格式异常');
  }
  const o = raw as Record<string, unknown>;
  const token =
    (typeof o.token === 'string' && o.token) ||
    (typeof o.accessToken === 'string' && o.accessToken) ||
    (typeof o.access_token === 'string' && o.access_token) ||
    '';
  if (!token) {
    throw new Error('登录响应缺少 token');
  }

  const nested = o.user ?? o.userInfo ?? o.user_info;
  if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
    return { token, user: nested as UserInfo };
  }

  if (o.id != null || o.username != null) {
    return {
      token,
      user: {
        id: o.id,
        username: o.username,
        email: o.email,
        roleId: o.roleId,
        role_id: o.role_id,
        roleID: o.roleID,
        roleName: o.roleName,
        role_name: o.role_name,
        avatarUrl: o.avatarUrl ?? o.avatar_url,
      } as UserInfo,
    };
  }

  return { token, user: null };
}

// 用户登录
export async function loginApi(payload: LoginRequest): Promise<LoginApiResult> {
  const raw = await authRequest.post<unknown>('/auth/login', payload);
  return normalizeLoginResult(raw);
}

// 用户注册
export function registerApi(payload: RegisterRequest) {
  return authRequest.post<null>('/auth/register', payload);
}

// 获取当前登录用户信息
export function getProfileApi() {
  return authRequest.get<UserInfo>('/auth/profile');
}

// 分离请求：仅用于头像区域（独立加载）
export function getProfileAvatarApi() {
  return authRequest.get<Pick<UserInfo, 'id' | 'username' | 'avatarUrl'>>('/auth/profile');
}

// 分离请求：仅用于基本信息区域（独立加载）
export function getProfileInfoApi() {
  return authRequest.get<Pick<UserInfo, 'id' | 'username' | 'email'>>('/auth/profile');
}

// 发送验证码（注册绑定邮箱 / 找回密码）；注册场景远程常要求同时带 username + email
export function sendCodeApi(payload: {
  scene: 'register' | 'reset';
  username?: string;
  email?: string;
}) {
  return authRequest.post<null>('/auth/send-code', payload);
}

// 找回密码 - 验证验证码并重置密码
export interface VerifyCodeResetRequest {
  username: string;
  code: string;
  newPassword: string;
  confirmPassword: string;
}

export function verifyCodeResetApi(payload: VerifyCodeResetRequest) {
  // 后端字段大小写约定：newpassword（小写 p）+ confirmPassword（大写 P）
  return authRequest.post<null>('/auth/verify-code', {
    username: payload.username,
    code: payload.code,
    newpassword: payload.newPassword,
    confirmPassword: payload.confirmPassword,
  });
}

// 修改密码（已登录场景）
export interface ChangePasswordRequest {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
  code: string;
}

export function changePasswordApi(payload: ChangePasswordRequest) {
  return authRequest.post<null>('/auth/password', payload);
}

// 上传头像：POST /admin/users/{id}/avatar（form-data: file）
export function uploadAvatarApi(userId: string | number, form: FormData) {
  return adminRequest.post<{ avatarUrl: string }>(`/users/${userId}/avatar`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

// 根据用户 ID 获取头像地址：GET /admin/users/{id}/avatar（与文档一致，code/msg/data.avatarUrl）
export async function getUserAvatarByIdApi(userId: string | number): Promise<{ avatarUrl: string }> {
  const raw = await adminRequest.get<unknown>(`/users/${encodeURIComponent(String(userId))}/avatar`);
  if (raw == null || typeof raw !== 'object') {
    return { avatarUrl: '' };
  }
  const obj = raw as Record<string, unknown>;
  const inner =
    obj.data != null && typeof obj.data === 'object' && !Array.isArray(obj.data)
      ? (obj.data as Record<string, unknown>)
      : obj;
  const avatarUrl = String(inner.avatarUrl ?? inner.avatar_url ?? inner.url ?? '').trim();
  return { avatarUrl };
}