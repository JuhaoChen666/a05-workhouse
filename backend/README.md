# 后端说明

## MySQL 配置

1. 确保已安装 MySQL（5.7+ 或 8.x）
2. 修改 `config.js` 中的数据库连接信息：
   - `host`: 数据库地址（默认 localhost）
   - `port`: 端口（默认 3306）
   - `user`: 用户名（默认 root）
   - `password`: 你的 MySQL 密码
   - `database`: 数据库名（默认 ai_interview）

3. 初始化数据库和表，在 MySQL 中执行 `init.sql`：

```bash
mysql -u root -p < init.sql
```

或在 MySQL 客户端中手动执行 `init.sql` 中的 SQL。

4. 安装依赖并启动：

```bash
npm install
npm run dev
```

## 文件说明

- `config.js` - 数据库配置
- `db.js` - MySQL 连接池
- `init.sql` - 建库建表脚本
- `server.js` - Express 服务入口
