const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const pool = require('./db');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';

const app = express();
const PORT = process.env.PORT || 3000;

// 头像上传目录
const AVATAR_DIR = path.join(__dirname, 'uploads', 'avatar');
if (!fs.existsSync(AVATAR_DIR)) {
  fs.mkdirSync(AVATAR_DIR, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, AVATAR_DIR),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname || '') || '.png';
    const userId = (req.user && req.user.id) || 'guest';
    cb(null, `avatar_${userId}_${Date.now()}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 2 * 1024 * 1024 },
});

// 简单的验证码存储（仅用于演示环境，进程重启后会丢失）
// key 形如：register:email 或 reset:username
const verifyCodes = new Map();
const CODE_EXPIRE_MS = 10 * 60 * 1000; // 10 分钟

function genCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function setCode(key) {
  const code = genCode();
  verifyCodes.set(key, { code, expiresAt: Date.now() + CODE_EXPIRE_MS });
  return code;
}

function checkCode(key, code) {
  const item = verifyCodes.get(key);
  if (!item) return false;
  if (Date.now() > item.expiresAt) {
    verifyCodes.delete(key);
    return false;
  }
  const okMatch = String(code).trim() === String(item.code);
  if (okMatch) {
    verifyCodes.delete(key);
  }
  return okMatch;
}

// 根据相对路径生成完整可访问的头像链接；如无则返回默认头像链接
function buildAvatarUrl(req, avatarPath) {
  const base = `${req.protocol}://${req.get('host')}`;
  const pathOrDefault = avatarPath || '/api/avatar-file/default-avatar.png';
  if (pathOrDefault.startsWith('http')) return pathOrDefault;
  return base + pathOrDefault;
}

app.use(cors());
app.use(express.json({ limit: '5mb' }));
// 对外暴露头像静态文件
app.use('/api/avatar-file', express.static(AVATAR_DIR));

function ok(data = null, message = 'ok') {
  return { code: 0, message, data };
}
function fail(code, message) {
  return { code, message, data: null };
}

// 验证 token，写入 req.user（含 id, username, roleId）
function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '');
  if (!token) {
    return res.status(401).json(fail(401, '未提供 token'));
  }
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    next();
  } catch (e) {
    return res.status(401).json(fail(401, 'token 无效或已过期'));
  }
}

// 需要管理员角色（假定 roleId 2 为管理员）
function adminMiddleware(req, res, next) {
  if (req.user.roleId !== 2) {
    return res.status(403).json(fail(403, '无权限'));
  }
  next();
}

// ----- 认证 -----

// 用户注册
app.post('/api/auth/register', async (req, res) => {
  const { username, password, confirmPassword, email, emailCode } = req.body || {};
  if (!username || !password || !confirmPassword) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  if (password !== confirmPassword) {
    return res.json(fail(1002, '两次密码不一致'));
  }
  // 如果填写了邮箱，则需要验证码校验
  if (email) {
    if (!emailCode) {
      return res.json(fail(400, '请先完成邮箱验证码验证'));
    }
    const okMatch = checkCode(`register:${email}`, emailCode);
    if (!okMatch) {
      return res.json(fail(1009, '验证码错误或已过期'));
    }
  }
  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE username = ?', [username]);
    if (rows.length > 0) {
      return res.json(fail(1003, '用户名已存在'));
    }
    await pool.query('INSERT INTO `user` (username, password, email, role_id) VALUES (?, ?, ?, 1)', [
      username,
      password,
      email || null,
    ]);
    return res.json(ok(null, '注册成功'));
  } catch (err) {
    console.error('注册失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 用户登录
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  try {
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.role_id, u.avatar_url, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.username = ? AND u.password = ?',
      [username, password]
    );
    if (rows.length === 0) {
      return res.json(fail(1004, '用户名或密码错误'));
    }
    const row = rows[0];
    const token = jwt.sign(
      { id: String(row.id), username: row.username, roleId: row.role_id },
      JWT_SECRET,
      { expiresIn: '2h' }
    );
    const avatarUrl = buildAvatarUrl(req, row.avatar_url);
    return res.json(
      ok({
        token,
        user: {
          id: String(row.id),
          username: row.username,
          roleId: row.role_id,
          roleName: row.role_name,
          avatarUrl,
        },
      })
    );
  } catch (err) {
    console.error('登录失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 获取当前用户信息
app.get('/api/auth/profile', authMiddleware, async (req, res) => {
  const { id } = req.user;
  try {
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.email, u.avatar_url, u.role_id, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.id = ?',
      [id]
    );
    if (rows.length === 0) {
      return res.json(fail(1005, '用户不存在'));
    }
    const u = rows[0];
    const avatarUrl = buildAvatarUrl(req, u.avatar_url);
    return res.json(
      ok({
        id: String(u.id),
        username: u.username,
        email: u.email || undefined,
        roleId: u.role_id,
        roleName: u.role_name,
        avatarUrl,
      })
    );
  } catch (err) {
    console.error('获取用户信息失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 发送验证码（注册绑定邮箱 / 找回密码）
app.post('/api/auth/send-code', async (req, res) => {
  const { scene, username, email } = req.body || {};

  if (scene === 'register') {
    if (!email) return res.json(fail(400, '邮箱不能为空'));
    const key = `register:${email}`;
    const code = setCode(key);
    console.log(`[验证码][注册] email=${email}, code=${code}`);
    return res.json(ok(null, '验证码已发送'));
  }

  // 默认视为找回密码
  if (!username) return res.json(fail(400, '用户名不能为空'));
  try {
    const [rows] = await pool.query('SELECT id, email FROM `user` WHERE username = ?', [username]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    let userEmail = rows[0].email;

    if (!userEmail) {
      if (!email) {
        return res.json(fail(400, '邮箱未绑定，请先绑定邮箱'));
      }
      // 简单处理：在找回密码流程中顺便绑定邮箱
      await pool.query('UPDATE `user` SET email = ? WHERE id = ?', [email, rows[0].id]);
      userEmail = email;
    }

    const key = `reset:${username}`;
    const code = setCode(key);
    console.log(`[验证码][找回密码] username=${username}, email=${userEmail}, code=${code}`);
    return res.json(ok(null, '验证码已发送'));
  } catch (err) {
    console.error('发送验证码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 找回密码：验证验证码并重置密码
app.post('/api/auth/verify-code', async (req, res) => {
  const { username, code, newPassword, confirmPassword } = req.body || {};
  if (!username) return res.json(fail(400, '用户名不能为空'));
  if (!code) return res.json(fail(1008, '验证码不能为空'));
  if (!newPassword || !confirmPassword) return res.json(fail(1010, '密码不能为空'));
  if (newPassword !== confirmPassword) return res.json(fail(1002, '两次密码不一致'));

  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE username = ?', [username]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));

    const key = `reset:${username}`;
    const okMatch = checkCode(key, code);
    if (!okMatch) return res.json(fail(1009, '验证码错误或已过期'));

    await pool.query('UPDATE `user` SET password = ? WHERE id = ?', [newPassword, rows[0].id]);
    return res.json(ok(null, '密码重置成功'));
  } catch (err) {
    console.error('重置密码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 修改密码（需登录 + 邮箱验证码）
app.post('/api/auth/password', authMiddleware, async (req, res) => {
  const { oldPassword, newPassword, confirmPassword, code } = req.body || {};
  if (!oldPassword || !newPassword || !confirmPassword) {
    return res.json(fail(1010, '密码不能为空'));
  }
  if (newPassword !== confirmPassword) {
    return res.json(fail(1002, '两次新密码不一致'));
  }
  if (!code) {
    return res.json(fail(1008, '验证码不能为空'));
  }

  const userId = req.user.id;
  const username = req.user.username;

  try {
    const [rows] = await pool.query('SELECT password FROM `user` WHERE id = ?', [userId]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    if (rows[0].password !== oldPassword) {
      return res.json(fail(1006, '原密码错误'));
    }

    const okMatch = checkCode(`reset:${username}`, code);
    if (!okMatch) {
      return res.json(fail(1009, '验证码错误或已过期'));
    }

    await pool.query('UPDATE `user` SET password = ? WHERE id = ?', [newPassword, userId]);
    return res.json(ok(null, '密码修改成功'));
  } catch (err) {
    console.error('修改密码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 上传 / 修改头像（支持 multipart/form-data 和 base64 JSON）
app.post('/api/auth/avatar', authMiddleware, upload.single('file'), async (req, res) => {
  const { id } = req.user;
  try {
    let avatarUrl = null;

    if (req.file) {
      // 表单上传文件
      avatarUrl = `/api/avatar-file/${req.file.filename}`;
    } else if (req.body && req.body.avatar) {
      // base64 字符串
      const base64 = req.body.avatar;
      const match = base64.match(/^data:image\/\w+;base64,(.+)$/);
      const data = match ? match[1] : base64;
      const buf = Buffer.from(data, 'base64');
      const filename = `avatar_${id}_${Date.now()}.png`;
      const filepath = path.join(AVATAR_DIR, filename);
      fs.writeFileSync(filepath, buf);
      avatarUrl = `/api/avatar-file/${filename}`;
    } else {
      return res.json(fail(400, '请上传文件或提供 avatar 字段'));
    }

    await pool.query('UPDATE `user` SET avatar_url = ? WHERE id = ?', [avatarUrl, id]);

    const fullUrl = buildAvatarUrl(req, avatarUrl);

    return res.json(ok({ avatarUrl: fullUrl }));
  } catch (err) {
    console.error('上传头像失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 角色 -----
app.get('/api/roles', authMiddleware, async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT id, name FROM role ORDER BY id');
    return res.json(ok(rows.map((r) => ({ id: r.id, name: r.name }))));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 岗位 -----
app.get('/api/positions', authMiddleware, async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT id, name, sort_order AS sortOrder FROM `position` ORDER BY sort_order, id');
    return res.json(ok(rows));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/positions/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query('SELECT id, name, sort_order AS sortOrder FROM `position` WHERE id = ?', [id]);
    if (rows.length === 0) return res.status(404).json(fail(404, '岗位不存在'));
    return res.json(ok(rows[0]));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/positions', authMiddleware, adminMiddleware, async (req, res) => {
  const { name, sortOrder } = req.body || {};
  if (!name) return res.json(fail(400, '岗位名称不能为空'));
  try {
    const [r] = await pool.query('INSERT INTO `position` (name, sort_order) VALUES (?, ?)', [name, sortOrder ?? 0]);
    return res.json(ok({ id: r.insertId, name, sortOrder: sortOrder ?? 0 }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/positions/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { name, sortOrder } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (name !== undefined) {
      updates.push('name = ?');
      values.push(name);
    }
    if (sortOrder !== undefined) {
      updates.push('sort_order = ?');
      values.push(sortOrder);
    }
    if (updates.length === 0) return res.json(ok(null));
    values.push(id);
    await pool.query(`UPDATE \`position\` SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/positions/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM `position` WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 题库 -----
app.get('/api/question-bank', authMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '';
    const params = [];
    if (positionId && !isNaN(positionId)) {
      where = 'WHERE q.position_id = ?';
      params.push(positionId);
    }
    const countSql = `SELECT COUNT(*) AS total FROM question_bank q ${where}`;
    const [countRows] = await pool.query(countSql, params);
    const total = countRows[0].total;

    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT q.id, q.position_id AS positionId, p.name AS positionName, q.question, q.answer, q.knowledge_tags AS knowledgeTags
       FROM question_bank q LEFT JOIN \`position\` p ON q.position_id = p.id ${where} ORDER BY q.id DESC LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/question-bank/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      'SELECT q.id, q.position_id AS positionId, p.name AS positionName, q.question, q.answer, q.knowledge_tags AS knowledgeTags FROM question_bank q LEFT JOIN `position` p ON q.position_id = p.id WHERE q.id = ?',
      [id]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '题目不存在'));
    return res.json(ok(rows[0]));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/question-bank', authMiddleware, adminMiddleware, async (req, res) => {
  const { positionId, question, answer, knowledgeTags } = req.body || {};
  if (!positionId || !question) return res.json(fail(400, '岗位和题目必填'));
  try {
    const [r] = await pool.query(
      'INSERT INTO question_bank (position_id, question, answer, knowledge_tags) VALUES (?, ?, ?, ?)',
      [positionId, question, answer || null, knowledgeTags || null]
    );
    return res.json(ok({ id: r.insertId, positionId, question, answer: answer || null, knowledgeTags: knowledgeTags || null }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/question-bank/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { positionId, question, answer, knowledgeTags } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (positionId !== undefined) {
      updates.push('position_id = ?');
      values.push(positionId);
    }
    if (question !== undefined) {
      updates.push('question = ?');
      values.push(question);
    }
    if (answer !== undefined) {
      updates.push('answer = ?');
      values.push(answer);
    }
    if (knowledgeTags !== undefined) {
      updates.push('knowledge_tags = ?');
      values.push(knowledgeTags);
    }
    if (updates.length === 0) return res.json(ok(null));
    values.push(id);
    await pool.query(`UPDATE question_bank SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/question-bank/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM question_bank WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 面试记录 -----
app.post('/api/interview-record', authMiddleware, async (req, res) => {
  const { positionId } = req.body || {};
  const userId = req.user.id;
  if (!positionId) return res.json(fail(400, '岗位必选'));
  const startedAt = new Date().toISOString().slice(0, 19).replace('T', ' ');
  try {
    const [r] = await pool.query(
      'INSERT INTO interview_record (user_id, position_id, started_at) VALUES (?, ?, ?)',
      [userId, positionId, startedAt]
    );
    return res.json(
      ok({
        id: r.insertId,
        userId: Number(userId),
        positionId: Number(positionId),
        startedAt,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/interview-record', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const offset = (page - 1) * pageSize;
  try {
    const [countRows] = await pool.query('SELECT COUNT(*) AS total FROM interview_record WHERE user_id = ?', [userId]);
    const total = countRows[0].total;
    const [rows] = await pool.query(
      `SELECT r.id, r.position_id AS positionId, p.name AS positionName, r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r LEFT JOIN \`position\` p ON r.position_id = p.id WHERE r.user_id = ? ORDER BY r.started_at DESC LIMIT ? OFFSET ?`,
      [userId, pageSize, offset]
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/interview-record/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const userId = req.user.id;
  const isAdmin = req.user.roleId === 2;
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, r.position_id AS positionId, p.name AS positionName, r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r LEFT JOIN \`position\` p ON r.position_id = p.id WHERE r.id = ?`,
      [id]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    const row = rows[0];
    if (Number(row.userId) !== Number(userId) && !isAdmin) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const [details] = await pool.query(
      'SELECT id, interview_record_id AS interviewRecordId, round_index AS roundIndex, role, content, emotion_data AS emotionData, score FROM interview_detail WHERE interview_record_id = ? ORDER BY round_index',
      [id]
    );
    return res.json(ok({ ...row, details }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.patch('/api/interview-record/:id/end', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const userId = req.user.id;
  const { endedAt, totalScore } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [id]);
    if (rows.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    if (Number(rows[0].user_id) !== Number(userId)) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const endTime = endedAt || new Date().toISOString().slice(0, 19).replace('T', ' ');
    const updates = ['ended_at = ?'];
    const values = [endTime];
    if (totalScore !== undefined && totalScore !== null) {
      updates.push('total_score = ?');
      values.push(totalScore);
    }
    values.push(id);
    await pool.query(`UPDATE interview_record SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 面试对话详情 -----
app.post('/api/interview-detail', authMiddleware, async (req, res) => {
  const { interviewRecordId, roundIndex, role, content, emotionData, score } = req.body || {};
  const userId = req.user.id;
  if (!interviewRecordId || roundIndex === undefined || !role || !content) {
    return res.json(fail(400, 'interviewRecordId、roundIndex、role、content 必填'));
  }
  try {
    const [rows] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [interviewRecordId]);
    if (rows.length === 0) return res.status(404).json(fail(404, '面试记录不存在'));
    if (Number(rows[0].user_id) !== Number(userId)) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const emotionJson = emotionData ? JSON.stringify(emotionData) : null;
    const [r] = await pool.query(
      'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
      [interviewRecordId, roundIndex, role, content, emotionJson, score ?? null]
    );
    return res.json(
      ok({
        id: r.insertId,
        interviewRecordId,
        roundIndex,
        role,
        content,
        emotionData: emotionData || null,
        score: score ?? null,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 报告 -----
app.get('/api/report', authMiddleware, async (req, res) => {
  const interviewRecordId = parseInt(req.query.interviewRecordId, 10);
  const userId = req.user.id;
  const isAdmin = req.user.roleId === 2;
  if (!interviewRecordId || isNaN(interviewRecordId)) {
    return res.json(fail(400, 'interviewRecordId 必填'));
  }
  try {
    const [rows] = await pool.query(
      'SELECT rep.id, rep.interview_record_id AS interviewRecordId, rep.content FROM report rep JOIN interview_record r ON rep.interview_record_id = r.id WHERE rep.interview_record_id = ?',
      [interviewRecordId]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '报告不存在'));
    const row = rows[0];
    const [rec] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [interviewRecordId]);
    if (rec.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    if (Number(rec[0].user_id) !== Number(userId) && !isAdmin) {
      return res.status(403).json(fail(403, '无权限'));
    }
    return res.json(ok(row));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/report', authMiddleware, async (req, res) => {
  const { interviewRecordId, content } = req.body || {};
  if (!interviewRecordId || content === undefined) return res.json(fail(400, 'interviewRecordId 和 content 必填'));
  try {
    const contentStr = typeof content === 'string' ? content : JSON.stringify(content);
    await pool.query(
      'INSERT INTO report (interview_record_id, content) VALUES (?, ?) ON DUPLICATE KEY UPDATE content = VALUES(content), updated_at = CURRENT_TIMESTAMP',
      [interviewRecordId, contentStr]
    );
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 热门岗位（招聘信息，首页展示 & 搜索，使用 job 表） ----- 
app.get('/api/jobs/hot', authMiddleware, async (req, res) => {
  const limit = Math.min(20, Math.max(1, parseInt(req.query.limit, 10) || 10));
  try {
    const [rows] = await pool.query(
      'SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type FROM job ORDER BY id DESC LIMIT ?',
      [limit]
    );
    return res.json(ok(rows));
  } catch (err) {
    console.error('获取热门岗位失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 招聘岗位搜索（关键词 + 岗位类型筛选）
// 注意：必须放在 /api/jobs/:id 之前注册，否则会被当作 :id 路径处理
app.get('/api/jobs/search', authMiddleware, async (req, res) => {
  const keywordRaw = (req.query.keyword || '').toString().trim();
  const type = (req.query.type || '').toString().trim();
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 8));
  const offset = (page - 1) * pageSize;

  const keyword = keywordRaw.toLowerCase();

  try {
    let where = '1=1';
    const params = [];

    if (keyword) {
      where += ' AND (LOWER(name) LIKE ? OR LOWER(company_name) LIKE ? OR LOWER(job_content) LIKE ?)';
      const kw = `%${keyword}%`;
      params.push(kw, kw, kw);
    }
    if (type) {
      where += ' AND type = ?';
      params.push(type);
    }

    const [countRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM job WHERE ${where}`,
      params
    );
    const total = countRows[0].total || 0;

    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type
       FROM job
       WHERE ${where}
       ORDER BY id DESC
       LIMIT ? OFFSET ?`,
      listParams
    );

    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error('搜索岗位失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/jobs/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      'SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type FROM job WHERE id = ?',
      [id]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '岗位不存在'));
    return res.json(ok(rows[0]));
  } catch (err) {
    console.error('获取岗位详情失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 学习资源 -----
app.get('/api/learning-resource', authMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const tags = req.query.tags ? String(req.query.tags).trim() : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '';
    const params = [];
    if (tags) {
      const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);
      if (tagList.length) {
        where = 'WHERE ' + tagList.map(() => 'tags LIKE ?').join(' OR ');
        tagList.forEach((t) => params.push('%' + t + '%'));
      }
    }
    const countSql = `SELECT COUNT(*) AS total FROM learning_resource ${where}`;
    const [countRows] = await pool.query(countSql, params);
    const total = countRows[0].total;
    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT id, title, link, tags FROM learning_resource ${where} ORDER BY id DESC LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/learning-resource', authMiddleware, adminMiddleware, async (req, res) => {
  const { title, link, tags } = req.body || {};
  if (!title || !link) return res.json(fail(400, '标题和链接必填'));
  try {
    const [r] = await pool.query('INSERT INTO learning_resource (title, link, tags) VALUES (?, ?, ?)', [
      title,
      link,
      tags || null,
    ]);
    return res.json(ok({ id: r.insertId, title, link, tags: tags || null }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/learning-resource/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { title, link, tags } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    if (link !== undefined) {
      updates.push('link = ?');
      values.push(link);
    }
    if (tags !== undefined) {
      updates.push('tags = ?');
      values.push(tags);
    }
    if (updates.length === 0) return res.json(ok(null));
    values.push(id);
    await pool.query(`UPDATE learning_resource SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/learning-resource/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM learning_resource WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 用户列表（管理员） -----
app.get('/api/users', authMiddleware, adminMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const offset = (page - 1) * pageSize;
  try {
    const [countRows] = await pool.query('SELECT COUNT(*) AS total FROM `user`');
    const total = countRows[0].total;
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.email, u.role_id AS roleId, r.name AS roleName FROM `user` u JOIN role r ON u.role_id = r.id ORDER BY u.id LIMIT ? OFFSET ?',
      [pageSize, offset]
    );
    const list = rows.map((u) => ({
      id: String(u.id),
      username: u.username,
      email: u.email || undefined,
      roleId: u.roleId,
      roleName: u.roleName,
    }));
    return res.json(ok({ list, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 后台管理：全部面试记录（仅管理员） -----
app.get('/api/admin/interview-record', authMiddleware, adminMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const userId = req.query.userId ? parseInt(req.query.userId, 10) : null;
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '1=1';
    const params = [];
    if (userId && !isNaN(userId)) {
      where += ' AND r.user_id = ?';
      params.push(userId);
    }
    if (positionId && !isNaN(positionId)) {
      where += ' AND r.position_id = ?';
      params.push(positionId);
    }
    const [countRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM interview_record r WHERE ${where}`,
      params
    );
    const total = countRows[0].total;
    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, u.username AS userName, r.position_id AS positionId, p.name AS positionName,
       r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r
       LEFT JOIN \`user\` u ON r.user_id = u.id
       LEFT JOIN \`position\` p ON r.position_id = p.id
       WHERE ${where}
       ORDER BY r.started_at DESC
       LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 后台管理：导出面试记录（仅管理员，返回 JSON） -----
app.get('/api/admin/export/interview-record', authMiddleware, adminMiddleware, async (req, res) => {
  const userId = req.query.userId ? parseInt(req.query.userId, 10) : null;
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const limit = Math.min(1000, Math.max(1, parseInt(req.query.limit, 10) || 500));
  try {
    let where = '1=1';
    const params = [];
    if (userId && !isNaN(userId)) {
      where += ' AND r.user_id = ?';
      params.push(userId);
    }
    if (positionId && !isNaN(positionId)) {
      where += ' AND r.position_id = ?';
      params.push(positionId);
    }
    params.push(limit);
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, u.username AS userName, r.position_id AS positionId, p.name AS positionName,
       r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r
       LEFT JOIN \`user\` u ON r.user_id = u.id
       LEFT JOIN \`position\` p ON r.position_id = p.id
       WHERE ${where}
       ORDER BY r.started_at DESC
       LIMIT ?`,
      params
    );
    const accept = req.headers.accept || '';
    if (accept.includes('application/json')) {
      return res.json(ok(rows));
    }
    res.setHeader('Content-Disposition', 'attachment; filename=interview-records.json');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.send(JSON.stringify(rows, null, 2));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.listen(PORT, () => {
  console.log(`Backend server is running at http://localhost:${PORT}`);
});
