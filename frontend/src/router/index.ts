import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { ElMessage } from 'element-plus';
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
        path: 'interview/evaluation/:sessionId',
        name: 'InterviewEvaluation',
        meta: { title: '面试评估报告' },
        component: () => import('../pages/Interview/InterviewEvaluationPage.vue'),
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
  {
    path: '/admin',
    component: () => import('../pages/Admin/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        redirect: '/admin/users',
      },
      {
        path: 'users',
        name: 'AdminUsers',
        meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/UserManagePage.vue'),
      },
      {
        path: 'positions',
        name: 'AdminPositions',
        meta: { title: '岗位管理', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/PositionManagePage.vue'),
      },
      {
        path: 'positions/:id',
        name: 'AdminPositionDetail',
        meta: { title: '岗位详情', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/PositionDetailPage.vue'),
      },
      {
        path: 'question-bank',
        name: 'AdminQuestionBank',
        meta: { title: '题库管理', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/QuestionBankManagePage.vue'),
      },
      {
        path: 'learning-resource',
        name: 'AdminLearningResource',
        meta: { title: '学习资源', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/LearningResourceManagePage.vue'),
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
    const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
    const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin);

    // 已登录仍访问登录/注册页时，直接进入主站首页（避免「有 token 却停在登录页」）
    if (userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
      next({ name: 'Home' });
      return;
    }

    // 需要登录但当前未登录，跳转到登录页并带上重定向地址
    if (requiresAuth && !userStore.isLoggedIn) {
      next({ name: 'Login' });
      return;
    }

    // 仅管理员可访问：用 isAdmin（内部 Number(roleId)===2），避免后端返回字符串 "2" 时误判
    if (requiresAdmin && userStore.isLoggedIn && !userStore.isAdmin) {
      ElMessage.error('仅管理员可访问后台管理系统');
      next({ name: 'Home' });
      return;
    }

    next();
  });
}

export default router;