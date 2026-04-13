import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { ElMessage } from 'element-plus';
import { useUserStore } from '../store/user';
import { resolveDocumentTitle } from '@/utils/documentTitle';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../pages/Landing/LandingPage.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    meta: { title: '登录' },
    component: () => import('../pages/Login/LoginPage.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    meta: { title: '注册' },
    component: () => import('../pages/Register/RegisterPage.vue'),
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    meta: { title: '找回密码' },
    component: () => import('../pages/ForgotPassword/ForgotPasswordPage.vue'),
  },
  {
    path: '/home',
    component: () => import('../layouts/HomeLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        component: () => import('../pages/Home/HomePage.vue'),
        children: [
          {
            path: '',
            name: 'Home',
            meta: { title: '首页' },
            component: () => import('../pages/Home/HomeDashboardPage.vue'),
          },
          {
            path: 'question',
            name: 'HomeQuestion',
            meta: { title: '面试押题' },
            component: () => import('../pages/QuestionBank/QuestionBankPage.vue'),
          },
          {
            path: 'question/predict',
            name: 'HomePredictQuestions',
            meta: { title: '面试押题' },
            component: () => import('../pages/QuestionBank/PredictQuestionsPage.vue'),
          },
          {
            path: 'resume',
            name: 'HomeResume',
            meta: { title: '简历管理' },
            component: () => import('../pages/Resume/ResumeManagePage.vue'),
          },
          {
            path: 'resume/optimize',
            name: 'HomeResumeOptimize',
            meta: { title: '简历优化' },
            component: () => import('../pages/Resume/ResumeOptimizePreviewPage.vue'),
          },
          {
            path: 'resume/optimize/run',
            name: 'HomeResumeOptimizeRun',
            meta: { title: '简历优化' },
            component: () => import('../pages/Resume/ResumeOptimizeRunPage.vue'),
          },
          {
            path: 'job',
            name: 'HomeJob',
            meta: { title: '岗位检索' },
            component: () => import('../pages/JobSearch/JobSearchPage.vue'),
          },
          {
            path: 'interview',
            name: 'HomeInterview',
            redirect: { name: 'HomeInterviewType' },
          },
          {
            path: 'interview/type',
            name: 'HomeInterviewType',
            meta: { title: '面试设置' },
            component: () => import('../pages/Interview/InterviewTypeSelectPage.vue'),
          },
          {
            path: 'interview/position',
            name: 'HomeInterviewPosition',
            meta: { title: '面试设置' },
            component: () => import('../pages/Interview/InterviewPositionSelectPage.vue'),
          },
          {
            path: 'interview/config',
            name: 'HomeInterviewConfig',
            meta: { title: '面试设置' },
            component: () => import('../pages/Interview/InterviewConfigPage.vue'),
          },
          {
            path: 'doc',
            name: 'HomeDoc',
            meta: { title: '帮助文档' },
            component: () => import('../pages/Common/PlaceholderPage.vue'),
            props: { title: '文档', desc: '文档模块正在建设中，后续会提供使用说明与常见问题。' },
          },
          {
            path: 'profile',
            name: 'Profile',
            meta: { title: '个人中心' },
            component: () => import('../pages/Profile/ProfilePage.vue'),
          },
          {
            path: 'profile/edit',
            name: 'ProfileEdit',
            meta: { title: '编辑资料' },
            component: () => import('../pages/Profile/ProfileEditPage.vue'),
          },
        ],
      },
      {
        path: 'job-search',
        name: 'JobSearch',
        meta: { title: '岗位检索' },
        component: () => import('../pages/JobSearch/JobSearchPage.vue'),
      },
      {
        path: 'interview/settings/:id(\\d+)',
        name: 'InterviewSettings',
        meta: { title: '面试设置' },
        component: () => import('../pages/Interview/InterviewSettingsPage.vue'),
      },
      {
        path: 'interview/session/:id',
        name: 'InterviewSession',
        meta: { title: '面试' },
        redirect: (to) => {
          const mode = String(to.query.interviewMode || '').trim().toLowerCase();
          return {
            name: mode === 'avatar' ? 'InterviewSessionAvatar' : 'InterviewSessionText',
            params: to.params,
            query: to.query,
          };
        },
      },
      {
        path: 'interview/session/:id/text',
        name: 'InterviewSessionText',
        meta: { title: '面试' },
        component: () => import('../pages/Interview/InterviewSessionTextPage.vue'),
      },
      {
        path: 'interview/session/:id/avatar',
        name: 'InterviewSessionAvatar',
        meta: { title: '面试' },
        component: () => import('../pages/Interview/InterviewSessionAvatarPage.vue'),
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
        meta: { title: '面试押题' },
        component: () => import('../pages/QuestionBank/QuestionBankPage.vue'),
      },
      {
        path: 'records',
        name: 'InterviewRecordList',
        meta: { title: '面试记录' },
        component: () => import('../pages/InterviewRecordList/InterviewRecordListPage.vue'),
      },
      {
        path: 'report/:id',
        name: 'ReportDetail',
        meta: { title: '面试报告' },
        component: () => import('../pages/ReportDetail/ReportDetailPage.vue'),
      },
      {
        path: 'job/:id(\\d+)',
        name: 'JobDetail',
        meta: { title: '岗位详情' },
        component: () => import('../pages/JobDetail/JobDetailPage.vue'),
      },
      {
        path: 'demo',
        name: 'HomeDemo',
        meta: { title: '首页Demo' },
        component: () => import('../pages/Demo/HomeDemoPage.vue'),
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
        path: 'resumes',
        name: 'AdminResumes',
        meta: { title: '简历管理', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/ResumeManagePage.vue'),
      },
      {
        path: 'sessions',
        name: 'AdminSessions',
        meta: { title: '会话管理', requiresAuth: true, requiresAdmin: true },
        component: () => import('../pages/Admin/SessionManagePage.vue'),
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
  router.beforeEach((to) => {
    const userStore = useUserStore(pinia);
    const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
    const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin);

    // 已登录仍访问登录/注册页时，直接进入主站首页（避免「有 token 却停在登录页」）
    if (userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
      return { name: 'Home' };
    }

    // 需要登录但当前未登录，跳转到登录页并带上重定向地址
    if (requiresAuth && !userStore.isLoggedIn) {
      return { name: 'Login' };
    }

    // 仅管理员可访问：用 isAdmin（内部 Number(roleId)===2），避免后端返回字符串 "2" 时误判
    if (requiresAdmin && userStore.isLoggedIn && !userStore.isAdmin) {
      ElMessage.error('仅管理员可访问后台管理系统');
      return { name: 'Home' };
    }
    return true;
  });

  router.afterEach((to) => {
    document.title = resolveDocumentTitle(to);
  });
}

export default router;