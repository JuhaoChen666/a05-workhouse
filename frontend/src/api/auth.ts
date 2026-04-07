import { authRequest } from './request';
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
  return authRequest.post<null>('/auth/verify-code', payload);
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

// 上传头像（FormData 或 { avatar: base64 }）
export function uploadAvatarApi(form: FormData | { avatar: string }) {
  if (form instanceof FormData) {
    return authRequest.post<{ avatarUrl: string }>('/auth/avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }
  return authRequest.post<{ avatarUrl: string }>('/auth/avatar', form);
}