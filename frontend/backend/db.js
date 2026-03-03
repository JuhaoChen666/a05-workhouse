/**
 * MySQL 连接池
 * 使用 mysql2 的 Promise 接口
 */
const mysql = require('mysql2/promise');
const config = require('./config');

const pool = mysql.createPool(config);

// 测试连接
pool.getConnection()
  .then((conn) => {
    conn.release();
    console.log('MySQL 连接成功');
  })
  .catch((err) => {
    console.error('MySQL 连接失败:', err.message);
  });

module.exports = pool;
