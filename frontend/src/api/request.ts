import axios from 'axios';
import { useUserStore } from '@/store/user';

const API_BASE = 'http://localhost:3000';
export const apiOrigin = API_BASE;

// 创建 axios 实例
const instance = axios.create({
  baseURL: `${API_BASE}/api`,
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

// 响应拦截器：统一处理 code / message，返回 data 字段（已解包）
instance.interceptors.response.use(
  (response) => {
    const data = response.data;
    if (data.code !== 0) {
      return Promise.reject(new Error(data.message || '请求错误'));
    }
    return data.data;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 封装为返回解包后的 data 类型，避免各处拿到 AxiosResponse
export default {
  get: <T = unknown>(url: string, config?: Parameters<typeof instance.get>[1]) =>
    instance.get(url, config) as Promise<T>,
  post: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof instance.post>[2]) =>
    instance.post(url, data, config) as Promise<T>,
  put: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof instance.put>[2]) =>
    instance.put(url, data, config) as Promise<T>,
  patch: <T = unknown>(url: string, data?: unknown, config?: Parameters<typeof instance.patch>[2]) =>
    instance.patch(url, data, config) as Promise<T>,
  delete: <T = unknown>(url: string, config?: Parameters<typeof instance.delete>[1]) =>
    instance.delete(url, config) as Promise<T>,
};