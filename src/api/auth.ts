import { authRequest } from './request';
import type { LoginRequest, RegisterRequest, LoginResponse, UserInfo } from '../types/auth';

// 用户登录
export function loginApi(payload: LoginRequest) {
  return authRequest.post<LoginResponse>('/auth/login', payload);
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