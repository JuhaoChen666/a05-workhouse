/**
 * 初始化数据库：创建 ai_interview 库和 users 表
 * 使用 config.js 中的数据库配置
 * 运行：node init-db.js
 */
const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');
const config = require('./config');

async function init() {
  // 连接时先不指定 database，以便执行 CREATE DATABASE
  const { database, ...connConfig } = config;
  const conn = await mysql.createConnection(connConfig);

  const sqlPath = path.join(__dirname, 'init.sql');
  const sql = fs.readFileSync(sqlPath, 'utf8');

  // 按分号分割并执行每条 SQL（跳过空行和纯注释行）
  const statements = sql
    .split(';')
    .map((s) =>
      s
        .split('\n')
        .filter((line) => !line.trim().startsWith('--'))
        .join('\n')
        .trim()
    )
    .filter((s) => s);

  for (const stmt of statements) {
    await conn.query(stmt);
    console.log('执行成功:', stmt.substring(0, 60).replace(/\s+/g, ' ') + '...');
  }

  await conn.end();
  console.log('数据库初始化完成！');
}

init().catch((err) => {
  console.error('初始化失败:', err.message);
  process.exit(1);
});
