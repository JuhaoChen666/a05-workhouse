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