import { defineStore } from 'pinia';
import type { UserInfo } from '@/types/auth';

interface UserState {
  token: string | null;
  userInfo: UserInfo | null;
}

// 从 localStorage 恢复 userInfo
function loadUserInfo(): UserInfo | null {
  try {
    const raw = localStorage.getItem('userInfo');
    return raw ? (JSON.parse(raw) as UserInfo) : null;
  } catch {
    return null;
  }
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem('token'),
    userInfo: loadUserInfo(),
  }),
  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setToken(token: string) {
      this.token = token;
      localStorage.setItem('token', token);
    },
    setUserInfo(info: UserInfo) {
      this.userInfo = info;
      if (info) {
        localStorage.setItem('userInfo', JSON.stringify(info));
      } else {
        localStorage.removeItem('userInfo');
      }
    },
    logout() {
      this.token = null;
      this.userInfo = null;
      localStorage.removeItem('token');
      localStorage.removeItem('userInfo');
    },
  },
});
