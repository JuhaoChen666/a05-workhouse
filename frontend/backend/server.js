const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const pool = require('./db');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

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
  const { username, password, confirmPassword } = req.body || {};
  if (!username || !password || !confirmPassword) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  if (password !== confirmPassword) {
    return res.json(fail(1002, '两次密码不一致'));
  }
  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE username = ?', [username]);
    if (rows.length > 0) {
      return res.json(fail(1003, '用户名已存在'));
    }
    await pool.query('INSERT INTO `user` (username, password, role_id) VALUES (?, ?, 1)', [username, password]);
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
      'SELECT u.id, u.username, u.role_id, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.username = ? AND u.password = ?',
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
    return res.json(
      ok({
        token,
        user: {
          id: String(row.id),
          username: row.username,
          roleId: row.role_id,
          roleName: row.role_name,
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
      'SELECT u.id, u.username, u.email, u.role_id, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.id = ?',
      [id]
    );
    if (rows.length === 0) {
      return res.json(fail(1005, '用户不存在'));
    }
    const u = rows[0];
    return res.json(
      ok({
        id: String(u.id),
        username: u.username,
        email: u.email || undefined,
        roleId: u.role_id,
        roleName: u.role_name,
      })
    );
  } catch (err) {
    console.error('获取用户信息失败:', err);
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
