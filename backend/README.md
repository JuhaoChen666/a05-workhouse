# 后端说明（与 api.md 对齐）

前端请求基地址：`http://localhost:3000/api`。运行方式：`npm install && npm start`（或 `npm run dev` 带监听）。

## 已实现接口（server.js）

- **认证**：`POST /auth/register`、`POST /auth/login`、`GET /auth/profile`、`PUT /auth/password`、`POST /auth/avatar`（上传头像）
- **角色/岗位**：`GET /roles`、`GET /positions`
- **面试记录**：`POST /api/interview-record`、`GET /api/interview-record`、`GET /api/interview-record/stats`、`GET /api/interview-record/recent-scores`、`GET /api/interview-record/:id`、`PATCH /api/interview-record/:id/end`
- **报告**：`GET /report?interviewRecordId=`、`POST /report`
- **用户能力分析**：`GET /user/ability-analysis`（柱状图 + 雷达图数据）
- **热门岗位（招聘）**：`GET /jobs/hot`、`GET /jobs/:id`

数据为内存存储，热门岗位已预置 8 条计算机相关招聘（Java/前端/Python/Go/C++/全栈等）。头像上传目录为 `uploads/`。
