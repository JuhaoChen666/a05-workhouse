


```markdown
# 后台管理系统API文档

本文档记录了后台管理系统中所有需要管理员权限的接口（/admin路径下的接口，不包含文件管理接口）。

## 通用说明

### 认证方式
- 所有接口需要在请求头中携带管理员JWT Token
- 请求头格式：`Authorization: Bearer <token>`

### 通用响应格式
```json
{
  "code": "0",
  "msg": "ok",
  "data": {}
}
```

| 字段 | 类型   | 描述                              |
| ---- | ------ | --------------------------------- |
| code | string | 响应码，"0"表示成功，其他表示错误 |
| msg  | string | 响应消息                          |
| data | object | 响应数据                          |

### 通用错误码
| 错误码 | 描述                      |
| ------ | ------------------------- |
| 0      | 成功                      |
| -1     | 一般错误                  |
| 401    | 未认证（Token无效或过期） |
| 403    | 无权限（非管理员用户）    |
| 404    | 资源不存在                |
| 1001   | 用户名或密码不能为空      |
| 1002   | 两次密码不一致            |
| 1003   | 用户名已存在              |
| 1004   | 用户名或密码错误          |
| 1005   | 用户不存在                |

---

## 1. 用户管理接口

### 1.1 获取用户列表（分页）

**接口地址**：`GET /admin/users`

**请求头**：
```
Authorization: Bearer <admin_token>
```

**请求参数**：
| 参数名   | 类型 | 必填 | 默认值 | 说明     |
| -------- | ---- | ---- | ------ | -------- |
| page     | int  | 否   | 1      | 页码     |
| pageSize | int  | 否   | 10     | 每页数量 |

**请求示例**：
```
GET /admin/users?page=1&pageSize=10
Authorization: Bearer <admin_token>
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "list": [
      {
        "id": "1",
        "username": "admin",
        "email": "admin@example.com",
        "roleId": 2,
        "roleName": "管理员"
      }
    ],
    "total": 1
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员

---

### 1.2 获取用户详情

**接口地址**：`GET /admin/users/{id}`

**请求头**：
```
Authorization: Bearer <admin_token>
```

**路径参数**：
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| id     | int  | 是   | 用户ID |

**请求示例**：
```
GET /admin/users/1
Authorization: Bearer <admin_token>
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "roleId": 2,
    "avatar": "path/to/avatar.png"
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `404` 资源不存在：用户不存在

---

### 1.3 创建用户

**接口地址**：`POST /admin/users`

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**请求体**：
| 参数名   | 类型   | 必填 | 说明                             |
| -------- | ------ | ---- | -------------------------------- |
| username | string | 是   | 用户名                           |
| password | string | 是   | 密码                             |
| email    | string | 否   | 邮箱                             |
| role_id  | int    | 否   | 角色ID（1为普通用户，2为管理员） |

**请求示例**：
```json
{
  "username": "newuser",
  "password": "password123",
  "email": "newuser@example.com",
  "role_id": 1
}
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "创建用户成功",
  "data": null
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `1001` 用户名或密码不能为空
- `1003` 用户名已存在

---

### 1.4 更新用户信息

**接口地址**：`PUT /admin/users/{id}`

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**路径参数**：
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| id     | int  | 是   | 用户ID |

**请求体**：
| 参数名   | 类型   | 必填 | 说明   |
| -------- | ------ | ---- | ------ |
| username | string | 否   | 用户名 |
| email    | string | 否   | 邮箱   |
| role_id  | int    | 否   | 角色ID |

**请求示例**：
```json
{
  "username": "updateduser",
  "email": "updated@example.com",
  "role_id": 2
}
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "更新用户成功",
  "data": null
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `404` 用户不存在：用户不存在
- `1003` 用户名已存在：新用户名已被占用

---

### 1.5 删除用户

**接口地址**：`DELETE /admin/users/{id}`

**请求头**：
```
Authorization: Bearer <admin_token>
```

**路径参数**：
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| id     | int  | 是   | 用户ID |

**请求示例**：
```
DELETE /admin/users/1
Authorization: Bearer <admin_token>
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "删除用户成功",
  "data": null
}
```

**错误响应**：
- `403` 无权限：用户不是管理员或尝试删除自己
- `404` 用户不存在：用户不存在

---

## 2. 岗位管理接口

### 2.1 分页查询岗位

**接口地址**：`GET /admin/positions/page`

**请求头**：
```
Authorization: Bearer <admin_token>
```

**请求参数**：
| 参数名   | 类型   | 必填 | 说明                 |
| -------- | ------ | ---- | -------------------- |
| name     | string | 是   | 岗位名称（模糊查询） |
| page     | int    | 是   | 页码                 |
| pageSize | int    | 是   | 每页数量             |

**请求示例**：
```
GET /admin/positions/page?name=Java&page=1&pageSize=10
Authorization: Bearer <admin_token>
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "list": [
      {
        "id": 1,
        "name": "Java开发工程师",
        "sort_order": 0
      }
    ],
    "total": 1
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员

---

### 2.2 添加岗位

**接口地址**：`POST /admin/positions`

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**请求体**：
| 参数名     | 类型   | 必填 | 说明     |
| ---------- | ------ | ---- | -------- |
| name       | string | 是   | 岗位名称 |
| sort_order | int    | 否   | 排序值   |

**请求示例**：
```json
{
  "name": "前端开发工程师",
  "sort_order": 1
}
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "id": 2,
    "name": "前端开发工程师",
    "sort_order": 1
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员

---

### 2.3 添加岗位信息

**接口地址**：`POST /admin/positions/info`

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**请求体**：
| 参数名             | 类型   | 必填 | 说明                              |
| ------------------ | ------ | ---- | --------------------------------- |
| id                 | int    | 是   | 岗位ID（必须在positions表中存在） |
| name               | string | 是   | 岗位名称                          |
| responsibilities   | string | 是   | 职责描述                          |
| salary_junior      | string | 是   | 初级薪资                          |
| salary_mid         | string | 是   | 中级薪资                          |
| salary_senior      | string | 是   | 高级薪资                          |
| salary_expert      | string | 是   | 专家级薪资                        |
| skill_requirements | string | 是   | 技能要求                          |

**请求示例**：
```json
{
  "id": 2,
  "name": "前端开发工程师",
  "responsibilities": "负责前端页面开发",
  "salary_junior": "15k-20k",
  "salary_mid": "20k-30k",
  "salary_senior": "30k-40k",
  "salary_expert": "40k+",
  "skill_requirements": "熟练掌握React、Vue等前端框架"
}
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "positionInfo": {
      "id": 2,
      "name": "前端开发工程师",
      "responsibilities": "负责前端页面开发",
      "salary_junior": "15k-20k",
      "salary_mid": "20k-30k",
      "salary_senior": "30k-40k",
      "salary_expert": "40k+",
      "skill_requirements": "熟练掌握React、Vue等前端框架",
      "create_time": "2026-04-04T00:00:00.000+00:00",
      "update_time": "2026-04-04T00:00:00.000+00:00"
    },
    "url": "http://localhost:8080/positions/2"
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `1013` 岗位ID不能为空：岗位ID为0
- `1011` 添加岗位信息失败：数据库操作失败

---

### 2.4 更新岗位信息

**接口地址**：`PUT /admin/positions/info`

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**请求体**：
| 参数名             | 类型   | 必填 | 说明       |
| ------------------ | ------ | ---- | ---------- |
| id                 | int    | 是   | 岗位ID     |
| name               | string | 否   | 岗位名称   |
| responsibilities   | string | 否   | 职责描述   |
| salary_junior      | string | 否   | 初级薪资   |
| salary_mid         | string | 否   | 中级薪资   |
| salary_senior      | string | 否   | 高级薪资   |
| salary_expert      | string | 否   | 专家级薪资 |
| skill_requirements | string | 否   | 技能要求   |

**请求示例**：
```json
{
  "id": 2,
  "name": "高级前端开发工程师",
  "responsibilities": "负责前端架构设计",
  "salary_junior": "18k-25k",
  "salary_mid": "25k-35k",
  "salary_senior": "35k-45k",
  "salary_expert": "45k+",
  "skill_requirements": "熟练掌握React、Vue等前端框架及架构设计"
}
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": {
    "id": 2,
    "name": "高级前端开发工程师",
    "responsibilities": "负责前端架构设计",
    "salary_junior": "18k-25k",
    "salary_mid": "25k-35k",
    "salary_senior": "35k-45k",
    "salary_expert": "45k+",
    "skill_requirements": "熟练掌握React、Vue等前端框架及架构设计",
    "create_time": "2026-04-04T00:00:00.000+00:00",
    "update_time": "2026-04-04T00:00:00.000+00:00"
  }
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `1012` 更新岗位信息失败：数据库操作失败

---

### 2.5 删除岗位

**接口地址**：`DELETE /admin/positions/{id}`

**请求头**：
```
Authorization: Bearer <admin_token>
```

**路径参数**：
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| id     | int  | 是   | 岗位ID |

**请求示例**：
```
DELETE /admin/positions/2
Authorization: Bearer <admin_token>
```

**成功响应**：
```json
{
  "code": "0",
  "msg": "ok",
  "data": null
}
```

**错误响应**：
- `403` 无权限：用户不是管理员
- `404` 资源不存在：岗位不存在

---

## 3. 认证说明

需要登录的接口，请求头需携带：

```
Authorization: Bearer <token>
```

JWT payload 含：`id`、`username`、`roleId`。管理员为 `roleId === 2`。
```
        
