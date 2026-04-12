import { getUserAvatarByIdApi } from '@/api/auth';
import { useUserStore } from '@/store/user';

let inflight: Promise<boolean> | null = null;

/**
 * 调用 GET /admin/users/{id}/avatar，将返回的 avatarUrl 写回 Pinia（相对路径由布局用 apiOrigin 拼接）。
 * 用于登录后、刷新后进入主站、个人中心等；短时间并发合并为单次请求。
 */
export function syncUserAvatarFromAdminApi(): Promise<boolean> {
  if (inflight) return inflight;
  inflight = (async () => {
    try {
      const userStore = useUserStore();
      const id = userStore.userInfo?.id;
      if (!id || !userStore.isLoggedIn) return false;
      const { avatarUrl } = await getUserAvatarByIdApi(id);
      if (avatarUrl && userStore.userInfo) {
        userStore.setUserInfo({ ...userStore.userInfo, avatarUrl });
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}
