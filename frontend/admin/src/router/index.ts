import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { useUserStore } from '@/store/user';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', noLayout: true },
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/users',
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UserManage.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import('@/views/PositionManage.vue'),
        meta: { title: '岗位管理' },
      },
      {
        path: 'question-bank',
        name: 'QuestionBank',
        component: () => import('@/views/QuestionBankManage.vue'),
        meta: { title: '题库管理' },
      },
      {
        path: 'learning-resource',
        name: 'LearningResource',
        component: () => import('@/views/LearningResourceManage.vue'),
        meta: { title: '学习资源' },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export function setupRouterGuard(pinia: Pinia) {
  router.beforeEach((to, _from, next) => {
    const userStore = useUserStore(pinia);
    if (to.meta.requiresAuth && !userStore.isLoggedIn) {
      next({ name: 'Login', query: { redirect: to.fullPath } });
    } else if (to.name === 'Login' && userStore.isLoggedIn) {
      next({ path: '/' });
    } else {
      next();
    }
  });
}

export default router;
