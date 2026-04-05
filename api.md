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
| 1008 | 验证码不能为空 |
| 1009 | 验证码错误或已过期 |
| 1010 | 密码不能为空 |
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

#### 3.2 发送验证码（注册绑定邮箱 / 找回密码）

**POST** `/auth/send-code`

无需认证。用于：

- 注册时绑定邮箱（场景 `register`）；
- 找回密码（场景 `reset`）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene | string | 否 | 场景：`register`（注册）\|`reset`（找回密码）；默认 `reset` |
| username | string | 否 | 找回密码场景下的用户名（`scene=reset` 时必填） |
| email | string | 否 | 注册绑定邮箱时必填；找回密码时若用户未绑定邮箱，可在此传入新邮箱以便绑定 |

- 当 `scene = register` 时：
  - 仅使用 `email` 生成验证码，缓存在服务端（控制台会打印模拟“发送”记录）；
  - 前端在注册接口中携带 `email` 和 `emailCode` 完成绑定。
- 当 `scene = reset` 时：
  - 必须提供 `username`；
  - 若该用户已绑定邮箱，将向用户邮箱发送验证码；
  - 若尚未绑定邮箱且没有传入 `email`，返回错误 `400: 邮箱未绑定，请先绑定邮箱`；
  - 若尚未绑定邮箱但传入了 `email`，后端会先保存此邮箱到用户信息，再发送验证码。

成功：`data: null`，提示信息为“验证码已发送”。验证码有效期约 10 分钟。

---

#### 3.3 找回密码（验证码验证 + 重置密码）

**POST** `/auth/verify-code`

无需认证。校验找回密码验证码并重置指定用户的登录密码。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| code | string | 是 | 验证码（与 `/auth/send-code` 找回密码场景下发送的一致） |
| newPassword | string | 是 | 新密码 |
| confirmPassword | string | 是 | 确认新密码，需与 `newPassword` 一致 |

成功：`data: null`，密码重置成功，用户可用新密码登录。

失败示例：

- `1005`：用户不存在；
- `1002`：两次密码不一致；
- `1009`：验证码错误或已过期。

---

#### 4. 修改密码

**POST** `/auth/password`

需要认证。用于已登录用户在「账号与安全设置」页修改登录密码，需同时验证原密码与邮箱验证码。

| 字段 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| oldPassword | string | 是 | 原密码 |
| newPassword | string | 是 | 新密码 |
| confirmPassword | string | 是 | 确认新密码，需与 newPassword 一致 |
| code | string | 是 | 邮箱验证码，需与 `/auth/send-code` 找回密码场景下发送的一致 |

使用流程：

1. 前端调用 `/auth/send-code`，`scene = 'reset'`，传入当前用户名（以及必要时的邮箱），发送验证码；
2. 用户在修改密码表单中填写原密码、新密码和邮箱验证码；
3. 前端调用 `/auth/password` 完成修改。

成功：`data: null`。  
失败：可能返回：

- `1002`：两次新密码不一致；
- `1006`：原密码错误；
- `1009`：验证码错误或已过期。

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

> 说明：为了方便后台管理系统在本地联调，本项目的模拟后端在原有基础结构上，
> 额外返回了一份更详细的岗位信息，并允许用 GET 查询参数临时覆盖这些字段。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "name": "前端开发工程师",
    "sortOrder": 0,
    "city": "北京",
    "workExperience": "3-5 年",
    "education": "本科及以上",
    "salaryMin": 20000,
    "salaryMax": 40000,
    "responsibilities": "1. 负责 Web 前端需求分析与开发；2. 与产品和后端配合，持续优化用户体验；3. 推动前端工程化与性能优化。",
    "requirements": "1. 熟悉 HTML5/CSS3/JavaScript；2. 至少掌握一种前端框架（如 Vue/React）；3. 良好的编码习惯与沟通协作能力。",
    "tags": ["前端", "面试", "高薪"],
    "publishDate": "2026-03-04T12:00:00.000Z"
  }
}
```

在本地开发环境中，可以通过查询参数覆盖其中部分字段，例如：

`GET /positions/1?city=上海&salaryMin=30000&salaryMax=50000`

上述请求会返回相同结构的数据，只是 `city` 与薪资范围会按查询参数进行替换，
方便在不改动数据库的前提下模拟不同岗位详情。

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

需要认证 + 管理员。请求体字段均为可选，用于局部更新：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 岗位名称 |
| sortOrder | number | 否 | 排序值 |
| city | string | 否 | 工作城市，如“北京” |
| workExperience | string | 否 | 工作经验要求，如“3-5 年” |
| education | string | 否 | 学历要求，如“本科及以上” |
| salaryMin | number | 否 | 薪资下限（元/月） |
| salaryMax | number | 否 | 薪资上限（元/月） |
| responsibilities | string | 否 | 职责描述，建议按 1.2.3. 形式分条 |
| requirements | string | 否 | 任职要求，建议按 1.2.3. 形式分条 |
| tags | string / string[] | 否 | 标签集合，可以是字符串数组，也可以是逗号分隔的字符串 |
| publishDate | string | 否 | 发布时间，ISO 格式字符串 |

> 注意：当前模拟后端中，扩展字段（除 `name` / `sortOrder` 外）仅存储在内存中，
> 主要用于后台管理系统展示和调试，不会写入真实数据库。

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

### 模拟面试 AI（豆包 / 本地回退）

用于 `/home/interview/settings/:id` → 开始面试后的文本流式对话。服务端在内存中保存会话与消息历史；进程重启后清空。

**环境变量（可选，配置后走火山方舟豆包流式接口）**

| 变量 | 说明 |
|------|------|
| `ARK_API_KEY` | 方舟 API Key（推荐；兼容旧名 `DOUBAO_API_KEY`） |
| `ARK_ENDPOINT_ID` | 推理接入点 ID，对应请求体 `model`（如 `ep-xxxx`；兼容旧名 `DOUBAO_ENDPOINT_ID`） |
| `ARK_CHAT_URL` | 可选，默认 `POST https://ark.cn-beijing.volces.com/api/v3/chat/completions` |

未配置 `ARK_API_KEY` 或 `ARK_ENDPOINT_ID` 时，接口仍可用，后端使用**模拟流式输出**（逐字推送），便于本地联调。

#### 20.1 开始面试

**POST** `/interview/start`

需要认证。请求体：

```json
{
  "resume": "候选人张三，3年Android开发经验...",
  "position": "移动端开发工程师(Android)",
  "collection_name": "android_engineer",
  "interview_mode": "text"
}
```

`interview_mode` 可选：`text`（默认，文本+语音一体）/ `avatar`。

成功响应：

`data: { session_id, status, total_rounds, current_topic, current_question, interview_mode, history }`

---

#### 20.2 回答问题（流式）

**POST** `/interview/answer`

需要认证。请求体：

```json
{
  "session_id": "bd500e58-f57d-4828-a12f-fd0b04928045",
  "answer": "Activity、Service、BroadcastReceiver、ContentProvider"
}
```

响应为 **NDJSON 流**（逐行 JSON，不是统一 `{ code, message, data }` 包装），典型事件：

- `{"type":"analyzing","data":{"message":"正在分析回答深度..."}, ...}`
- `{"type":"analysis_result","data":{"depth_score":1,"is_vague":true,"need_followup":true}, ...}`
- `{"type":"followup","data":{"message":"回答不够深入，准备追问..."}, ...}`
- `{"type":"question","data":{"question":"...","is_followup":true,"topic":"...","round":2}, ...}`

---

#### 20.3 获取会话详情（用于中途加入/恢复）

**GET** `/interview/session/:session_id`

需要认证。成功响应：

`data: { session_id, interview_mode, status, total_rounds, current_topic, current_question, history }`

---

#### 20.4 结束并删除会话

**DELETE** `/interview/session/:session_id`

需要认证。成功响应：

`data: { session_id, status: "ended" }`

---

#### 20.5 虚拟人会话初始化（方案A）

**POST** `/interview/avatar/session/start`

需要认证。用于虚拟人面试模式下获取前端直连流媒体所需的短时凭证。

请求体：

```json
{
  "session_id": "bd500e58-f57d-4828-a12f-fd0b04928045",
  "avatar_id": "110592024"
}
```

可选形象 ID（当前受后端白名单限制）：

- `110592024`
- `110117005`
- `110017006`

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "session_id": "bd500e58-f57d-4828-a12f-fd0b04928045",
    "avatar_session_id": "d67f...a42",
    "vendor": "mock-xnrpt",
    "avatar_id": "110592024",
    "sdk_config": {
      "app_id": "your_app_id",
      "server_url": "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact",
      "signed_url": "wss://.../v1/interact?authorization=...&date=...&host=...",
      "scene_id": "your_scene_id",
      "vcn": "your_vcn",
      "protocol": "xrtc",
      "alpha": 1,
      "token": "short_lived_token",
      "expire_at": 1760000000
    }
  }
}
```

---

#### 20.6 虚拟人会话续签

**POST** `/interview/avatar/session/refresh`

需要认证。用于 SDK token 即将过期时续签。

请求体：`{ session_id, avatar_session_id }`  
响应：`data: { session_id, avatar_session_id, sdk_config: { token, expire_at } }`

---

#### 20.7 驱动虚拟人口播

**POST** `/interview/avatar/speak`

需要认证。将文本推送给虚拟人服务端（由后端持有厂商密钥）。

请求体：

```json
{
  "session_id": "bd500e58-f57d-4828-a12f-fd0b04928045",
  "text": "下一题：请介绍一个你做过的性能优化案例",
  "interrupt": true
}
```

响应：`data: { accepted: true, task_id }`

---

#### 20.8 结束虚拟人会话

**DELETE** `/interview/avatar/session/:session_id`

需要认证。成功响应：`data: { session_id, status: "ended" }`

---

#### 20.9 语音回答（流式）

**POST** `/interview/answer-voice`

需要认证。`multipart/form-data`，字段：

- `session_id`: string
- `file`: 二进制音频文件

响应为 NDJSON 流，典型事件：

- `voice_processing`（可带 `transcript`）
- `analyzing`
- `analysis_result`（包含 `feedback`）
- `followup`
- `question`
- `error`

---

#### 20.10 后端开发要求（虚拟人方案A）

1. **密钥只在后端**：`apiKey/apiSecret` 不得下发前端，仅用于后端换取短时凭证。  
2. **前端直连流媒体**：后端返回 `sdk_config`（含 `server_url/signed_url/token/expire_at`），前端 `start({ wrapper })` 后由 SDK 自动拉流播放。  
3. **会话绑定**：`avatar_session` 必须绑定 `session_id + userId`；所有 speak/refresh/stop 都要校验归属。  
4. **续签机制**：建议 token 到期前 30s 续签；接口失败时前端提示并降级文本/语音模式。  
5. **可观测性**：记录 `avatar_session_id`、`task_id`、关键耗时与错误码，便于排查厂商侧问题。  
6. **降级策略**：虚拟人初始化失败不阻断面试主链路，允许继续文本/语音问答。

**建议环境变量**

| 变量 | 说明 |
|------|------|
| `AVATAR_APP_ID` | 虚拟人平台 appId（用于前端 SDK 初始化） |
| `AVATAR_API_KEY` | 虚拟人平台 APIKey（仅后端使用，不下发前端） |
| `AVATAR_API_SECRET` | 虚拟人平台 APISecret（仅后端使用，不下发前端） |
| `AVATAR_VENDOR` | 厂商标识，仅用于日志与返回展示 |
| `AVATAR_SERVER_URL` | 交互接口地址，默认 `wss://avatar.cn-huadong-1.xf-yun.com/v1/interact` |
| `AVATAR_TOKEN_TTL_SEC` | 短时 token 过期秒数，默认 300 |

**前端环境变量**

| 变量 | 说明 |
|------|------|
| `VITE_AVATAR_SDK_SCRIPT_URL` | 虚拟人 Web SDK 脚本地址（会话页动态加载） |

**前端 SDK 初始化顺序（与官方文档一致）**

1. 创建 SDK 实例（`new AvatarPlatform({ useInlinePlayer: true })`）  
2. 设置监听（如 `playNotAllowed`）  
3. `setApiInfo`（`appId/sceneId/serverUrl/signedUrl`）  
4. `setGlobalParams`（`stream.protocol/alpha`、`avatar.avatar_id`、`tts.vcn`）  
5. `start({ wrapper })` 启动显示  
6. `writeText(text, { nlp: true, interrupt: true|false })` 驱动播报  
7. 结束时 `stop/destroy`

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

以下接口均需 **认证** 且 **`roleId === 2`（管理员）**。

管理后台「用户管理」页（`/admin/users`）联调说明：

- 角色下拉：复用 **「角色列表」** `GET /roles`（见上文 #### 5）。
- 用户 CRUD：使用本节 `GET/POST/PUT/DELETE /users...`。

> **路径前缀**：本文档统一以 `Base URL = http://localhost:3000/api` 为准，即完整地址形如 `http://localhost:3000/api/users`。若生产环境网关去掉 `/api` 前缀（例如根路径直接挂到 `8080`），则等价路径为 `http://localhost:8080/users`，请求体与响应结构不变。

#### 27. 用户列表（分页）

**GET** `/users?page=1&pageSize=10`

| 查询参数 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页条数，默认 10，最大 50 |

成功响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "avatar": "/avatar-file/avatar_1_1700000000000.png",
        "roleId": 2,
        "roleName": "管理员"
      }
    ],
    "total": 100
  }
}
```

- `list[].id`：数字类型用户 ID。
- `avatar`：可选；为库中存储的相对路径（或可访问路径），具体以后端为准。列表展示头像时可与站点域名拼接为完整 URL（与 `/auth/profile` 的 `avatarUrl` 处理类似，由后端或前端统一约定）。

---

#### 28. 用户详情

**GET** `/users/:id`

| 路径参数 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| id | number | 是 | 用户 ID |

成功：`data: { id, username, email?, roleId, avatar? }`。

错误：`1005` 用户不存在。

---

#### 29. 创建用户

**POST** `/users`

`Content-Type: application/json`

| 请求体 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| username | string | 是 | - | 用户名 |
| password | string | 是 | - | 密码（生产环境建议后端 BCrypt 等加密存储） |
| email | string | 否 | null | 邮箱 |
| roleId | number | 否 | 1 | `1` 普通用户，`2` 管理员 |

成功示例：

```json
{
  "code": 0,
  "message": "创建用户成功",
  "data": null
}
```

错误：`1001` 用户名或密码不能为空；`1003` 用户名已存在。

---

#### 30. 更新用户

**PUT** `/users/:id`

`Content-Type: application/json`

请求体字段均为可选（按需局部更新）：

| 请求体 | 类型 | 说明 |
|--------|------|------|
| username | string | 新用户名；**不得与其他用户重复** |
| email | string | 新邮箱 |
| roleId | number | 新角色（1 / 2） |
| password | string | 新密码；**不传或空字符串则保持原密码** |

**注意**：

- 允许修改 `username`，但会校验唯一性。
- **不允许通过本接口修改头像**：即使传入 `avatar` 也应被后端忽略（与业务文档一致）。
- 仅提交需要变更的字段即可。

成功示例：

```json
{
  "code": 0,
  "message": "更新用户成功",
  "data": null
}
```

错误：`1005` 用户不存在；`1003` 用户名已存在；`1001` 等参数不合法。

---

#### 31. 删除用户

**DELETE** `/users/:id`

成功示例：

```json
{
  "code": 0,
  "message": "删除用户成功",
  "data": null
}
```

错误：`1005` 用户不存在。

**删除保护**：建议禁止删除当前登录的管理员本人。当前模拟后端行为：`400`，`message: 不允许删除当前登录管理员`。

---

#### 31.1 调用示例（curl）

管理员先登录拿到 `token` 后：

```bash
# 用户列表
curl -X GET "http://localhost:3000/api/users?page=1&pageSize=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 用户详情
curl -X GET "http://localhost:3000/api/users/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 创建用户
curl -X POST "http://localhost:3000/api/users" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456","email":"test@example.com","roleId":1}'

# 更新用户
curl -X PUT "http://localhost:3000/api/users/2" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"newname","roleId":2}'

# 删除用户
curl -X DELETE "http://localhost:3000/api/users/2" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 后台管理（Admin，仅管理员）

以下接口均需认证且 `roleId === 2`。

#### 32. 全部面试记录列表（管理员）

**GET** `/admin/interview-record?page=1&pageSize=10&userId=1&positionId=2`

- `userId`、`positionId` 可选，用于筛选。`pageSize` 最大 50。

响应：`data: { list: [{ id, userId, userName, positionId, positionName, startedAt, endedAt, totalScore }], total }`

---

#### 33. 导出面试记录（管理员）

**GET** `/admin/export/interview-record?userId=1&positionId=2&limit=500`

- `userId`、`positionId` 可选；`limit` 默认 500，最大 1000。
- 请求头 `Accept: application/json` 时：返回统一格式 `{ code, message, data }`，`data` 为记录数组。
- 否则：直接返回 JSON 文件流，`Content-Disposition: attachment; filename=interview-records.json`。

---

## 六、前端请求封装说明

- `baseURL`: `http://localhost:3000/api`（可通过环境变量 `VITE_API_ORIGIN` 等调整，见前端 `request.ts`）
- 请求拦截器：自动注入 `Authorization: Bearer <token>`
- 响应拦截器：`code !== 0` 时抛出 `Error(data.message)`，成功时返回 `data.data`
- 管理后台用户管理：`src/pages/Admin/UserManagePage.vue` 使用 `src/api/admin.ts` 中的 `getUserListApi`、`getUserDetailApi`、`createUserApi`、`updateUserApi`、`deleteUserApi` 及 `getRolesApi`

---

*文档根据当前后端 server.js 与后台管理页整理，日期：2026-04-05*
