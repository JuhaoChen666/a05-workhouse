# 前端项目结构与实现说明

本文档用于快速理解 `frontend` 项目的目录结构、技术选型和功能实现方式，便于后续开发与维护。

## 1. 技术栈

- 框架：Vue 3（Composition API）+ TypeScript
- 构建工具：Vite
- 路由：Vue Router
- 状态管理：Pinia
- UI 组件库：Element Plus
- HTTP：Axios（封装在 `src/api/request.ts`）

常用命令（在 `frontend` 目录执行）：

- 启动开发：`npm run dev`
- 构建生产：`npm run build`
- 本地预览：`npm run preview`

---

## 2. 目录结构（核心）

```text
frontend/
  src/
    api/                    # 所有前端接口封装
      request.ts            # axios 实例、统一请求配置
      auth.ts               # 登录/注册等认证接口
      jobs.ts               # 岗位相关接口
      interviewAi.ts        # AI 面试会话、首问、流式聊天
      ...
    pages/                  # 页面级组件（按业务模块划分）
      Landing/
      Home/
      JobSearch/
      JobDetail/
      Interview/
      Admin/
      ...
    layouts/                # 布局组件（如 HomeLayout）
    router/
      index.ts              # 路由表、路由守卫
    store/
      user.ts               # 用户登录态与用户信息
    utils/                  # 通用工具函数
    main.ts                 # 应用入口
    App.vue                 # 根组件
  public/                   # 静态资源（图标、图片等）
  backend/                  # 本地 Node 后端（接口服务）
  admin/                    # 历史后台前端（当前主线已迁移到 src/pages/Admin）
```

---

## 3. 前端分层设计

### 3.1 `pages`（页面层）

- 负责页面展示、交互处理、生命周期逻辑。
- 通过调用 `api` 层获取/提交数据。
- 页面状态以 `ref/computed` 为主，跨页共享状态放到 `store`。

### 3.2 `api`（接口层）

- 每个业务域单独文件，保持“按功能聚合”。
- 所有接口走 `request.ts`，统一处理鉴权、错误与返回结构。
- 页面不直接写 `axios`，只调用 `api` 暴露的方法。

### 3.3 `store`（状态层）

- 当前以用户态为核心（token、用户信息、登录状态）。
- 与权限控制、菜单控制、请求鉴权联动。

### 3.4 `router`（路由与权限）

- 维护路由映射与页面入口。
- 通过 `meta`（如 `requiresAuth`、`requiresAdmin`）配合守卫做访问控制。

---

## 4. 典型业务实现：AI 面试流程

以 `Interview` 模块为例，当前流程为：

1. 在 `InterviewSettingsPage.vue` 填写岗位、模式、简历等信息。
2. 调用 `createInterviewAiSessionApi` 创建会话（仅创建上下文，不生成首问）。
3. 跳转到 `InterviewSessionPage.vue`。
4. 页面 `onMounted` 调用 `requestInterviewOpeningApi(sessionId)` 生成/获取 AI 首问。
5. 用户发送回答时调用 `streamInterviewChat`，通过 SSE 流式显示 AI 回复。

这样做的好处是：不会在点击“开始面试”时阻塞等待大模型，而是进入会话页后再触发生成。

---

## 5. 新增一个页面功能的推荐步骤

1. 在 `src/pages/<模块>/` 新建页面组件。
2. 在 `src/api/` 新建或扩展对应业务接口文件。
3. 在 `src/router/index.ts` 注册路由，按需配置 `meta` 权限。
4. 若有全局状态需求，在 `src/store/` 增加 store。
5. 页面中仅调用 `api` 方法，不直接处理底层请求细节。
6. 完成功能后自测：路由跳转、鉴权拦截、异常提示、边界场景。

---

## 6. 代码规范建议（项目内实践）

- 文件命名：页面组件使用 `PascalCasePage.vue` 风格。
- API 命名：`xxxApi` / `getXxxApi` / `createXxxApi` 统一后缀。
- 类型优先：接口入参、返回值在 `api` 层声明 TS 类型。
- 组件职责单一：页面负责编排，复杂逻辑可下沉到 `utils` 或独立 composable。
- 错误处理统一：优先通过统一请求封装与 `ElMessage` 提示用户。

---

## 7. 开发与联调说明

- 前端在 `frontend`，后端在 `frontend/backend`。
- 联调前确认后端服务已启动（例如 `node server.js`）。
- 若后端接口有改动，优先同步更新：
  - `src/api/*.ts` 的类型与方法
  - 使用该接口的页面逻辑
  - `api.md` 文档说明

---

## 8. 快速定位入口

- 应用入口：`src/main.ts`
- 路由入口：`src/router/index.ts`
- 认证状态：`src/store/user.ts`
- 面试主流程：`src/pages/Interview/InterviewSettingsPage.vue`、`src/pages/Interview/InterviewSessionPage.vue`
- 接口封装：`src/api/`

如需扩展新模块，建议直接参考 `Interview` 或 `Admin` 模块的组织方式进行复制与裁剪。
