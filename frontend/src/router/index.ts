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
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../pages/ForgotPassword/ForgotPasswordPage.vue'),
  },
  {
    path: '/home',
    component: () => import('../layouts/HomeLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../pages/Home/HomePage.vue'),
      },
      {
        path: 'job-search',
        name: 'JobSearch',
        component: () => import('../pages/JobSearch/JobSearchPage.vue'),
      },
      {
        path: 'interview/settings/:id',
        name: 'InterviewSettings',
        component: () => import('../pages/Interview/InterviewSettingsPage.vue'),
      },
      {
        path: 'interview/session/:id',
        name: 'InterviewSession',
        component: () => import('../pages/Interview/InterviewSessionPage.vue'),
      },
      {
        path: 'question-bank',
        name: 'QuestionBank',
        component: () => import('../pages/QuestionBank/QuestionBankPage.vue'),
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../pages/Profile/ProfilePage.vue'),
      },
      {
        path: 'profile/edit',
        name: 'ProfileEdit',
        component: () => import('../pages/Profile/ProfileEditPage.vue'),
      },
      {
        path: 'records',
        name: 'InterviewRecordList',
        component: () => import('../pages/InterviewRecordList/InterviewRecordListPage.vue'),
      },
      {
        path: 'report/:id',
        name: 'ReportDetail',
        component: () => import('../pages/ReportDetail/ReportDetailPage.vue'),
      },
      {
        path: 'job/:id',
        name: 'JobDetail',
        component: () => import('../pages/JobDetail/JobDetailPage.vue'),
      },
    ],
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