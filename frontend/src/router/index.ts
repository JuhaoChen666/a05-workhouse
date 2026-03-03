import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { useUserStore } from '../store/user';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../pages/Landing/LandingPage.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login/LoginPage.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../pages/Register/RegisterPage.vue'),
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../pages/Home/HomePage.vue'),
    meta: { requiresAuth: true }, // 需要登录
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 在 app 挂载前守卫里用 store 时，必须传入 pinia，否则 getActivePinia() 未就绪
export function setupRouterGuard(pinia: Pinia) {
  router.beforeEach((to, _from, next) => {
    const userStore = useUserStore(pinia);
    if (to.meta.requiresAuth && !userStore.isLoggedIn) {
      next({ name: 'Login' });
    } else {
      next();
    }
  });
}

export default router;