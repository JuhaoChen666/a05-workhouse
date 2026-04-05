# 用户管理 API 接口文档

## 基础信息

- **Base URL**: `http://localhost:8080`
- **认证方式**: JWT Bearer Token（管理员权限）
- **请求格式**: JSON (`Content-Type: application/json`)

---

## 接口列表

### 1. 获取用户列表（分页）

**接口**: `GET /users?page=1&pageSize=10`

**请求头**:
```
Authorization: Bearer {admin_token}
```

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 10 | 每页数量 |

**响应示例**:
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
        "avatar": "D:/...",
        "roleId": 2,
        "roleName": "管理员"
      },
      {
        "id": 2,
        "username": "user1",
        "email": "user1@example.com",
        "avatar": "D:/...",
        "roleId": 1,
        "roleName": "普通用户"
      }
    ],
    "total": 100
  }
}
```

---

### 2. 获取用户详情

**接口**: `GET /users/{id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 用户 ID |

**请求头**:
```
Authorization: Bearer {admin_token}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "roleId": 2,
    "avatar": "D:/..."
  }
}
```

---

### 3. 创建用户

**接口**: `POST /users`

**请求头**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "username": "newuser",
  "password": "123456",
  "email": "newuser@example.com",
  "roleId": 1
}
```

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| username | string | 是 | - | 用户名 |
| password | string | 是 | - | 密码 |
| email | string | 否 | null | 邮箱 |
| roleId | int | 否 | 1 | 角色 ID（1:普通用户，2:管理员） |

**响应示例**:
```json
{
  "code": 0,
  "message": "创建用户成功",
  "data": null
}
```

**错误响应**:
```json
{
  "code": 1003,
  "message": "用户名已存在",
  "data": null
}
```

---

### 4. 更新用户信息

**接口**: `PUT /users/{id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 用户 ID |

**请求头**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "username": "updated_username",
  "email": "updated@email.com",
  "roleId": 2
}
```

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 否 | 新用户名（**可以修改，但不能与其他用户重复**） |
| email | string | 否 | 新邮箱 |
| roleId | int | 否 | 新角色 ID |
| password | string | 否 | 新密码（如需修改则提供） |

**注意**:
- ✅ **可以修改 username** - 但会检查是否与现有用户重复
- ❌ **不允许修改 avatar** - 头像字段会被忽略
- ✅ **可以修改 email、roleId、password**
- ✅ **密码不传则保持原密码**

**响应示例**:
```json
{
  "code": 0,
  "message": "更新用户成功",
  "data": null
}
```

**错误响应**:
```json
{
  "code": 1005,
  "message": "用户不存在",
  "data": null
}
```

---

### 5. 删除用户

**接口**: `DELETE /users/{id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 用户 ID |

**请求头**:
```
Authorization: Bearer {admin_token}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "删除用户成功",
  "data": null
}
```

**错误响应**:
```json
{
  "code": 1005,
  "message": "用户不存在",
  "data": null
}
```

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 用户名或密码不能为空 |
| 1002 | 两次密码不一致 |
| 1003 | 用户名已存在 |
| 1004 | 用户名或密码错误 |
| 1005 | 用户不存在 |
| 401 | 未授权/Token 无效 |
| 403 | 无权限（非管理员） |
| 500 | 服务器错误 |

---

## 使用示例（curl）

### 1. 登录获取管理员 Token

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2. 获取用户列表

```bash
curl -X GET "http://localhost:8080/users?page=1&pageSize=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 3. 创建用户

```bash
curl -X POST http://localhost:8080/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "123456",
    "email": "test@example.com",
    "roleId": 1
  }'
```

### 4. 更新用户

```bash
curl -X PUT http://localhost:8080/users/123 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newname",
    "roleId": 2
  }'
```

### 5. 删除用户

```bash
curl -X DELETE http://localhost:8080/users/123 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## 注意事项

1. **所有用户管理接口都需要管理员权限**（roleId = 2）
2. **密码加密**: 后端会自动使用 BCrypt 加密密码
3. **字段命名**: 后端返回的数据已转换为驼峰命名（roleId, roleName）
4. **分页逻辑**: 页码从 1 开始，默认每页 10 条
5. **删除保护**: 建议添加逻辑防止删除当前登录的管理员自己
