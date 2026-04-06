import { defineStore } from 'pinia';
import type { UserInfo } from '@/types/auth';

interface UserState {
  token: string | null;
  userInfo: UserInfo | null;
}

/**
 * 登录/资料接口可能返回 number、字符串 "2"，或蛇形字段 role_id；
 * 部分后端返回驼峰但为 **roleID**（末尾大写 ID），与前端类型里的 roleId 不一致，需一并兼容。
 */
export function normalizeUserInfo(raw: unknown): UserInfo | null {
  if (raw == null || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  const roleRaw = o.roleId ?? o.role_id ?? o.roleID;
  let roleId: number | undefined;
  if (roleRaw != null && roleRaw !== '') {
    const n = Number(roleRaw);
    if (!Number.isNaN(n)) roleId = n;
  }
  const roleNameStr =
    o.roleName != null ? String(o.roleName) : o.role_name != null ? String(o.role_name) : '';
  // 历史缓存里可能只有 roleName、没有 roleId（旧版未识别后端 roleID 字段时写入的）
  if (roleId === undefined && roleNameStr === '管理员') {
    roleId = 2;
  }
  const id = o.id != null ? String(o.id) : '';
  const username = o.username != null ? String(o.username) : '';
  if (!id || !username) return null;
  return {
    id,
    username,
    email: o.email != null ? String(o.email) : undefined,
    roleId,
    roleName: roleNameStr || undefined,
    avatarUrl:
      (o.avatarUrl as string | null | undefined) ??
      (o.avatar_url as string | null | undefined) ??
      null,
  };
}

// 从 localStorage 恢复 userInfo（并做一次规范化，兼容历史缓存）
function loadUserInfo(): UserInfo | null {
  try {
    const raw = localStorage.getItem('userInfo');
    if (!raw) return null;
    return normalizeUserInfo(JSON.parse(raw) as unknown);
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
    /** 管理员：roleId 数值为 2（兼容登录接口把 roleId 打成字符串的情况） */
    isAdmin: (state) => Number(state.userInfo?.roleId) === 2,
  },
  actions: {
    setToken(token: string) {
      this.token = token;
      localStorage.setItem('token', token);
    },
    setUserInfo(info: UserInfo | Record<string, unknown> | null) {
      if (info == null) {
        this.userInfo = null;
        localStorage.removeItem('userInfo');
        return;
      }
      const normalized = normalizeUserInfo(info);
      this.userInfo = normalized;
      if (normalized) {
        localStorage.setItem('userInfo', JSON.stringify(normalized));
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
