import request from './request';
import type { UserInfo } from '@/store/user';

export interface LoginPayload {
  username: string;
  password: string;
}

export interface LoginResult {
  token: string;
  user: UserInfo;
}

export function loginApi(payload: LoginPayload) {
  return request.post<LoginResult>('/auth/login', payload);
}

export function getProfileApi() {
  return request.get<UserInfo>('/auth/profile');
}
