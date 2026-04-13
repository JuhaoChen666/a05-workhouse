import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import router, { setupRouterGuard } from './router';
import faviconUrl from '../../src/assets/logo2-title.webp';

{
  let el = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!el) {
    el = document.createElement('link');
    el.rel = 'icon';
    document.head.appendChild(el);
  }
  el.type = 'image/webp';
  el.href = faviconUrl;
}

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
setupRouterGuard(pinia);
app.use(router);
app.use(ElementPlus);
app.mount('#app');
