/// <reference types="vite/client" />

// 让 TypeScript 识别 .vue 文件模块
declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

