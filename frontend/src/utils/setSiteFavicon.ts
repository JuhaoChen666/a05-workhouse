import faviconUrl from '@/assets/logo2-title.webp';

/** 将浏览器标签页图标设为站点资源（与 index.html 中 link[rel=icon] 对应） */
export function applySiteFavicon() {
  let el = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!el) {
    el = document.createElement('link');
    el.rel = 'icon';
    document.head.appendChild(el);
  }
  el.type = 'image/webp';
  el.href = faviconUrl;
}
