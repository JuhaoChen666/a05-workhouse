import { defineStore } from 'pinia';

export interface UserInfo {
  id: string;
  username: string;
  email?: string;
  roleId: number;
  roleName: string;
}

interface UserState {
  token: string | null;
  userInfo: UserInfo | null;
}

function loadUserInfo(): UserInfo | null {
  try {
    const raw = localStorage.getItem('admin_userInfo');
    return raw ? (JSON.parse(raw) as UserInfo) : null;
  } catch {
    return null;
  }
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem('admin_token'),
    userInfo: loadUserInfo(),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.userInfo?.roleId === 2,
  },
  actions: {
    setToken(token: string) {
      this.token = token;
      localStorage.setItem('admin_token', token);
    },
    setUserInfo(info: UserInfo | null) {
      this.userInfo = info;
      if (info) {
        localStorage.setItem('admin_userInfo', JSON.stringify(info));
      } else {
        localStorage.removeItem('admin_userInfo');
      }
    },
    logout() {
      this.token = null;
      this.userInfo = null;
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_userInfo');
    },
  },
});
