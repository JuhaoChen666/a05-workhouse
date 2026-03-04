# AI 面试平台 - API 文档

> 基于当前后端实现整理，供前后端对接使用。

---

## 一、基础信息

| 项目 | 说明 |
|------|------|
| Base URL | `http://localhost:3000/api` |
| 请求格式 | `application/json` |
| 认证方式 | Bearer Token（JWT，有效期 2h） |

---

## 二、统一响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

- `code`: 0 表示成功
- `message`: 提示信息
- `data`: 业务数据，可为 `null`

### 失败响应

```json
{
  "code": 1001,
  "message": "用户名或密码不能为空",
  "data": null
}
```

### 业务错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 1001 | 用户名或密码不能为空 |
| 1002 | 两次密码不一致 |
| 1003 | 用户名已存在 |
| 1004 | 用户名或密码错误 |
| 1005 | 用户不存在 |
| 1006 | 原密码错误 |
| 400 | 请求参数错误（如无效 ID） |
| 401 | 未提供 token / token 无效或已过期 |
| 403 | 无权限（如非管理员） |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 三、认证说明

需要登录的接口，请求头需携带：

```
Authorization: Bearer <token>
```

JWT payload 含：`id`、`username`、`roleId`。管理员为 `roleId === 2`。

---

## 四、数据库设计简要

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| role | 角色 | id, name（普通用户、管理员） |
| user | 用户信息 | id, username, password, email, avatar_url, role_id |
| position | 岗位 | id, name, sort_order |
| question_bank | 题库 | id, position_id, question, answer, knowledge_tags |
| knowledge_base | 知识库文档 | id, content, vector_id |
| interview_record | 面试记录 | id, user_id, position_id, started_at, ended_at, total_score |
| interview_detail | 对话详情 | id, interview_record_id, round_index, role, content, emotion_data, score |
| report | 报告 | id, interview_record_id, content（JSON） |
| learning_resource | 学习资源(暂时不搞) | id, title, link, tags |

---

## 五、接口列表

### 认证（Auth）

#### 1. 用户注册

**POST** `/auth/register`

无需认证。注册后默认 `role_id = 1`（普通用户）。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| confirmPassword | string | 是 | 确认密码，需与 password 一致 |

成功：`data: null`。错误：1002（两次密码不一致）、1003（用户名已存在）。

---

#### 2. 用户登录

**POST** `/auth/login`

无需认证。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

成功返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "eyJ...",
    "user": {
      "id": "1",
      "username": "zhangsan",
      "roleId": 1,
      "roleName": "普通用户",
      "avatarUrl": "http://localhost:3000/api/avatar-file/default-avatar.png"
    }
  }
}
```

错误：1001、1004。

---

#### 3. 获取当前用户信息

**GET** `/auth/profile`

需要认证。

成功返回：`data: { id, username, email?, roleId, roleName, avatarUrl }`。错误：401、1005。  
其中 `avatarUrl` 为**完整可访问链接**，若用户尚未上传头像，则指向默认头像：`http://localhost:3000/api/avatar-file/default-avatar.png`。

---

#### 3.1 上传/修改头像

**POST** `/auth/avatar`

需要认证。更新当前登录用户的头像，完成后会覆盖原有头像地址。

- 支持两种请求方式：
  - `multipart/form-data`：字段名 **`file`**，上传图片文件（最大约 2MB）；
  - `application/json`：传入 base64 字符串，字段名 **`avatar`**，可为裸 base64 或 `data:image/png;base64,...` 形式。

成功返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "avatarUrl": "http://localhost:3000/api/avatar-file/avatar_1_1700000000000.png"
  }
}
```

- `avatarUrl`：后端生成的**完整头像访问链接**。前端收到后应更新本地用户信息（例如 Pinia / localStorage），之后都以该链接展示头像。

---

#### 4. 修改密码

**PUT** `/auth/password`

需要认证。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| oldPassword | string | 是 | 原密码 |
| newPassword | string | 是 | 新密码 |
| confirmPassword | string | 是 | 确认新密码，需与 newPassword 一致 |

成功：`data: null`。错误：1002（两次新密码不一致）、1006（原密码错误）。

---

### 角色

#### 5. 角色列表

**GET** `/roles`

需要认证。返回所有角色，用于下拉等。

响应：`data: [{ id, name }]`

---

### 岗位（Position）

#### 6. 岗位列表

**GET** `/positions`

需要认证。按 `sort_order`、`id` 排序。

响应：`data: [{ id, name, sortOrder }]`

---

#### 7. 岗位详情

**GET** `/positions/:id`

需要认证。404 表示岗位不存在。

---

#### 8. 新增岗位（管理员）

**POST** `/positions`

需要认证 + 管理员。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 岗位名称 |
| sortOrder | number | 否 | 排序，默认 0 |

响应：`data: { id, name, sortOrder }`

---

#### 9. 更新岗位（管理员）

**PUT** `/positions/:id`

需要认证 + 管理员。请求体：`name?`, `sortOrder?`。

---

#### 10. 删除岗位（管理员）

**DELETE** `/positions/:id`

需要认证 + 管理员。

---

### 题库（Question Bank）

#### 11. 题库列表（分页、按岗位筛选）

**GET** `/question-bank?page=1&pageSize=10&positionId=1`

需要认证。`positionId` 可选。`page` 默认 1，`pageSize` 默认 10，最大 50。

响应：`data: { list: [{ id, positionId, positionName, question, answer, knowledgeTags }], total }`

---

#### 12. 题库详情

**GET** `/question-bank/:id`

需要认证。404 表示题目不存在。

---

#### 13. 新增题目（管理员）

**POST** `/question-bank`

需要认证 + 管理员。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| positionId | number | 是 | 岗位 ID |
| question | string | 是 | 题目内容 |
| answer | string | 否 | 参考答案 |
| knowledgeTags | string | 否 | 知识点标签 |

响应：`data: { id, positionId, question, answer, knowledgeTags }`

---

#### 14. 更新题目（管理员）

**PUT** `/question-bank/:id`

需要认证 + 管理员。请求体：`positionId?`, `question?`, `answer?`, `knowledgeTags?`。

---

#### 15. 删除题目（管理员）

**DELETE** `/question-bank/:id`

需要认证 + 管理员。

---

### 面试记录（Interview Record）

#### 16. 创建面试记录（开始面试）

**POST** `/interview-record`

需要认证。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| positionId | number | 是 | 岗位 ID |

响应：`data: { id, userId, positionId, startedAt }`。400 表示岗位必选。

---

#### 17. 当前用户面试记录列表

**GET** `/interview-record?page=1&pageSize=10`

需要认证。仅返回当前用户记录。`pageSize` 最大 50。

响应：`data: { list: [{ id, positionId, positionName, startedAt, endedAt, totalScore }], total }`

---

#### 17.1 当前用户面试数据统计

**GET** `/interview-record/stats`

需要认证。用于个人中心统计面板。

响应：`data: { totalCount, finishedCount, avgScore, lastAt }`。其中 `totalCount` 为总次数，`finishedCount` 为已结束次数，`avgScore` 为已结束记录的平均得分（无则为 `null`），`lastAt` 为最近一次开始时间（ISO 字符串，无则为 `null`）。

---

#### 17.2 最近几次面试分数（折线图）

**GET** `/interview-record/recent-scores?limit=10`

需要认证。按开始时间倒序取当前用户最近若干次**已结束**面试的分数，用于个人中心折线图。`limit` 默认 10，最大 20。

响应：`data: [{ interviewRecordId, positionName, startedAt, totalScore }]`（按 startedAt 倒序，即最近一次在前）。

---

#### 18. 面试记录详情

**GET** `/interview-record/:id`

需要认证。本人或管理员可查看；否则 403。含 `details` 数组（对话详情）。

响应：`data: { id, userId, positionId, positionName, startedAt, endedAt, totalScore, details: [...] }`

---

#### 19. 结束面试

**PATCH** `/interview-record/:id/end`

需要认证。仅记录本人可操作。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| endedAt | string | 否 | 结束时间，不传则当前时间 |
| totalScore | number | 否 | 综合评分 |

---

### 面试对话详情（Interview Detail）

#### 20. 追加对话详情（每轮问答）

**POST** `/interview-detail`

需要认证。须为对应面试记录的本人。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| interviewRecordId | number | 是 | 面试记录 ID |
| roundIndex | number | 是 | 轮次序号 |
| role | string | 是 | `user` \| `assistant` |
| content | string | 是 | 本轮内容 |
| emotionData | object | 否 | 情感数据 JSON |
| score | number | 否 | 单题评分 |

响应：`data: { id, interviewRecordId, roundIndex, role, content, emotionData, score }`。400 表示必填项缺失；404 面试记录不存在；403 无权限。

---

### 报告（Report）

#### 21. 获取某次面试的报告

**GET** `/report?interviewRecordId=1`

需要认证。本人或管理员可查看。`content` 为 JSON。

响应：`data: { id, interviewRecordId, content }`。404 表示报告或记录不存在。

---

#### 22. 保存/更新报告

**POST** `/report`

需要认证。

| 请求体 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| interviewRecordId | number | 是 | 面试记录 ID |
| content | object/string | 是 | 报告内容（会 JSON 序列化存储） |

同一 `interviewRecordId` 再次提交会更新原报告。

---

#### 22.1 报告内容结构约定（示例）

报告 `content` 为 JSON，可含：`totalScore`、`dimensions`（各维度得分/评语）、`summary`、`suggestions` 等，供前端展示。详见各端实现。

---

### 用户能力分析

#### 23. 获取当前用户能力分析（柱状图 + 雷达图）

**GET** `/user/ability-analysis`

需要认证。用于个人中心柱状图与六边形（雷达）图。

响应：`data: { bar: [{ name, value }], radar: [{ name, value, max? }] }`。`bar` 为各能力项与分数（如技术深度、表达清晰度、逻辑性等）；`radar` 为雷达图维度，`value` 为当前值，`max` 为满分（默认 100）。

---

### 热门岗位（招聘信息）

以下为首页「热门岗位」卡片及岗位详情页所用接口，与面试用岗位（`/positions`）可独立。

#### 24. 热门岗位列表

**GET** `/jobs/hot?limit=10`

需要认证。返回热门招聘岗位列表，用于首页左侧卡片。`limit` 默认 10。

响应：

```json
[
  {
    "id": 1,
    "name": "Java 后端开发工程师",
    "companyName": "示例公司",
    "companyLogo": "",
    "salaryMin": 25000,
    "salaryMax": 45000,
    "jobContent": "工作内容描述",
    "type": "backend"
  }
]
```

- `salaryMin` / `salaryMax`: 数字，单位为元/月
- `jobContent`: 工作内容描述文本
- `type`: 岗位类型编码，当前值包括：
  - `backend`: 后端开发
  - `frontend`: 前端开发
  - `algo`: 算法工程师
  - `fullstack`: 全栈开发
  - `other`: 其它

---

#### 25. 岗位详情（招聘）

**GET** `/jobs/:id`

需要认证。返回单条招聘岗位详情，用于岗位详情页。

响应：`data: { id, name, companyName, companyLogo, salaryMin, salaryMax, jobContent, type }`。404 表示不存在。

---

#### 25.1 招聘岗位搜索

**GET** `/jobs/search?keyword=前端&type=frontend&page=1&pageSize=8`

需要认证。用于首页 Banner 搜索和岗位搜索结果页，支持关键词与岗位类型组合筛选。

| 查询参数 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| keyword | string | 否 | 关键词，模糊匹配岗位名称、公司名称、工作内容 |
| type | string | 否 | 岗位类型，取值同 `/jobs/hot` 返回的 `type` 字段 |
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页条数，默认 8，最大 50 |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": 3,
        "name": "Web 前端开发工程师",
        "companyName": "腾讯",
        "companyLogo": "",
        "salaryMin": 20000,
        "salaryMax": 40000,
        "jobContent": "负责前端需求分析、架构设计和代码开发……",
        "type": "frontend"
      }
    ],
    "total": 1
  }
}
```

---

### 用户管理（管理员）

#### 27. 用户列表（管理员）

**GET** `/users?page=1&pageSize=10`

需要认证 + 管理员。`pageSize` 最大 50。

响应：`data: { list: [{ id, username, email?, roleId, roleName }], total }`

---

### 后台管理（Admin，仅管理员）

以下接口均需认证且 `roleId === 2`。

#### 28. 全部面试记录列表（管理员）

**GET** `/admin/interview-record?page=1&pageSize=10&userId=1&positionId=2`

- `userId`、`positionId` 可选，用于筛选。`pageSize` 最大 50。

响应：`data: { list: [{ id, userId, userName, positionId, positionName, startedAt, endedAt, totalScore }], total }`

---

#### 29. 导出面试记录（管理员）

**GET** `/admin/export/interview-record?userId=1&positionId=2&limit=500`

- `userId`、`positionId` 可选；`limit` 默认 500，最大 1000。
- 请求头 `Accept: application/json` 时：返回统一格式 `{ code, message, data }`，`data` 为记录数组。
- 否则：直接返回 JSON 文件流，`Content-Disposition: attachment; filename=interview-records.json`。

---

## 六、前端请求封装说明

- `baseURL`: `http://localhost:3000/api`
- 请求拦截器：自动注入 `Authorization: Bearer <token>`
- 响应拦截器：`code !== 0` 时抛出 `Error(data.message)`，成功时返回 `data.data`

---

*文档根据当前后端 server.js 整理，日期：2026-03-04*
