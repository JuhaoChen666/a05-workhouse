import request from './request';
import type { LoginRequest, RegisterRequest, LoginResponse, UserInfo } from '../types/auth';

// 用户登录
export function loginApi(payload: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', payload);
}

// 用户注册
export function registerApi(payload: RegisterRequest) {
  return request.post<null>('/auth/register', payload);
}

// 获取当前登录用户信息
export function getProfileApi() {
  return request.get<UserInfo>('/auth/profile');
}

// 修改密码
export interface ChangePasswordRequest {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export function changePasswordApi(payload: ChangePasswordRequest) {
  return request.put<null>('/auth/password', payload);
}

// 上传头像（FormData 或 { avatar: base64 }）
export function uploadAvatarApi(form: FormData | { avatar: string }) {
  if (form instanceof FormData) {
    return request.post<{ avatarUrl: string }>('/auth/avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }
  return request.post<{ avatarUrl: string }>('/auth/avatar', form);
}