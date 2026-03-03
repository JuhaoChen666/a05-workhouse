import axios from 'axios';
import { useUserStore } from '@/store/user';

const instance = axios.create({
  baseURL: 'http://localhost:3000/api',
  timeout: 10000,
});

instance.interceptors.request.use((config) => {
  const userStore = useUserStore();
  if (userStore.token && config.headers) {
    config.headers.Authorization = `Bearer ${userStore.token}`;
  }
  return config;
});

instance.interceptors.response.use(
  (response) => {
    const data = response.data;
    if (data.code !== 0) {
      return Promise.reject(new Error(data.message || '请求错误'));
    }
    return data.data;
  },
  (error) => Promise.reject(error)
);

export default instance;
