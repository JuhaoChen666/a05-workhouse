/**
 * 数据库配置
 * 生产环境建议使用环境变量：process.env.DB_HOST 等
 */
module.exports = {
  host: 'localhost',
  port: 3306,
  user: 'root',
  password: 'lzwlzw', // 请改为你的 MySQL 密码
  database: 'ai_interview',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
};
