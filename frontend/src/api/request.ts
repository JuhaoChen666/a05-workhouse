import axios from 'axios';
import { useUserStore } from '@/store/user';

// 创建 axios 实例
const instance = axios.create({
  baseURL: 'http://localhost:3000/api', // 本地开发可通过 Vite 代理到后端
  timeout: 10000,
});

// 请求拦截器：注入 token
instance.interceptors.request.use((config) => {
  const userStore = useUserStore();
  if (userStore.token && config.headers) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});

// 响应拦截器：统一处理 code / message
instance.interceptors.response.use(
  (response) => {
    const data = response.data;
    // 这里假设后端统一返回 { code, message, data }
    if (data.code !== 0) {
      // 可以在这里做全局错误提示
      return Promise.reject(new Error(data.message || '请求错误'));
    }
    return data.data;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default instance;